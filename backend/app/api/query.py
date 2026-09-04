"""FastAPI Query and Investigation Orchestration Endpoint (Task 3.6)."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.agent.executor import execute_plan
from app.agent.intent_parser import parse_intent_async
from app.agent.planner import create_execution_plan_async
from app.agent.result_synthesizer import synthesize_results_async
from app.models.schemas import (
    ExecutionPlan,
    ExecutionTrace,
    Flag,
    ParsedIntent,
    RiskResult,
    SynthesizedResult,
    TraceStatus,
)
from app.storage.audit_store import AuditStore, get_audit_store
from app.tools.data_loader import load_transactions
from app.tools.sampler import sample_transactions

router = APIRouter(tags=["Investigation Query"])


class QueryRequest(BaseModel):
    """Request payload for natural language AML investigation query."""
    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(
        ...,
        min_length=1,
        description="Natural language AML query (e.g., 'Find structuring patterns in the last 30 days')",
        examples=["Find structuring patterns in the last 30 days"],
    )
    dataset_path: Optional[str] = Field(
        default=None,
        description="Optional path or bare filename of CSV dataset (defaults to synthetic_transactions.csv)",
    )
    normal_sample_size: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional sample size for legitimate transactions in stratified sample",
    )
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional manual filter parameter overrides",
    )


class QueryResponse(BaseModel):
    """Complete structured response containing plan, flags, risk results, trace, and executive summary."""
    model_config = ConfigDict(populate_by_name=True)

    query_id: str = Field(..., description="Unique query execution identifier")
    query: str = Field(..., description="Original natural language query")
    parsed_intent: ParsedIntent = Field(..., description="Structured intent parsed by LLM/fallback parser")
    execution_plan: ExecutionPlan = Field(..., description="Dynamic execution plan with invoked and skipped tools")
    flags: List[Flag] = Field(default_factory=list, description="Deterministic AML detection flags")
    risk_result: Optional[RiskResult] = Field(default=None, description="Hybrid risk fusion assessment")
    synthesized_result: Optional[SynthesizedResult] = Field(
        default=None, description="Executive summary and key findings"
    )
    trace: ExecutionTrace = Field(..., description="Execution telemetry and timings trace")
    explanations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Typology-tied natural language flag explanations"
    )
    eda_summary: Optional[Dict[str, Any]] = Field(
        default=None, description="Exploratory data analysis report if EDA was invoked"
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Agentic AML Investigation Query",
    description="Parses natural language query into intent, dynamically plans tool execution, runs deterministic tools, and returns structured findings and executive summary.",
)
async def execute_query(
    request: QueryRequest,
    audit_store: AuditStore = Depends(get_audit_store),
) -> QueryResponse:
    start_time = time.perf_counter()
    clean_query = request.query.strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty.",
        )

    # 1. Parse natural language intent
    try:
        parsed_intent = await parse_intent_async(clean_query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing query intent: {e}",
        )

    if request.filters:
        parsed_intent.filters.update(request.filters)

    # 2. Synthesize dynamic execution plan
    try:
        plan = await create_execution_plan_async(parsed_intent)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating execution plan: {e}",
        )

    # 3. Load dataset
    try:
        dataset_name = request.dataset_path or "synthetic_transactions.csv"
        df = load_transactions(dataset_name)
        if request.normal_sample_size is not None:
            df = sample_transactions(df, normal_sample_size=request.normal_sample_size)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading transaction data: {e}",
        )

    # 4. Execute plan steps sequentially
    try:
        execution_output = execute_plan(plan, df)
        executed_plan: ExecutionPlan = execution_output["plan"]
        context: Dict[str, Any] = execution_output["context"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during plan execution: {e}",
        )

    # 5. Synthesize executive summary & findings
    try:
        synthesized_result = await synthesize_results_async(execution_output, query=clean_query)
    except Exception:
        synthesized_result = None

    # 6. Extract artifacts from context
    flags: List[Flag] = context.get("rule_flags", [])
    risk_result: Optional[RiskResult] = context.get("risk_result")
    explanations: List[Dict[str, Any]] = context.get("explanations", [])
    eda_result: Optional[Dict[str, Any]] = context.get("eda_result")

    # 7. Compile ExecutionTrace
    total_duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
    has_error = bool(context.get("error"))
    trace_status = (
        TraceStatus.FAILED
        if has_error and not flags and not risk_result
        else (TraceStatus.PARTIAL_SUCCESS if has_error else TraceStatus.SUCCESS)
    )

    trace = ExecutionTrace(
        trace_id=str(uuid.uuid4()),
        query_id=plan.plan_id,
        detected_intent=executed_plan.detected_intent,
        active_filters=executed_plan.active_filters,
        invoked_tools=executed_plan.invoked_tools,
        skipped_tools=executed_plan.skipped_tools,
        execution_timings_ms={},
        total_execution_time_ms=total_duration_ms,
        status=trace_status,
        error_message=context.get("error", {}).get("message") if has_error else None,
        created_at=datetime.now(timezone.utc),
    )

    # 8. Persist query trace and flags to SQLite Audit Store
    try:
        audit_store.log_execution_trace(trace, query_text=clean_query)
        if flags:
            audit_store.log_flags(flags, query_id=plan.plan_id)
    except Exception:
        pass

    return QueryResponse(
        query_id=plan.plan_id,
        query=clean_query,
        parsed_intent=parsed_intent,
        execution_plan=executed_plan,
        flags=flags,
        risk_result=risk_result,
        synthesized_result=synthesized_result,
        trace=trace,
        explanations=explanations,
        eda_summary=eda_result,
    )
