"""Sequential execution of planner-generated AML investigation plans."""

from copy import deepcopy
import time
from typing import Any, Final

import numpy as np
import pandas as pd

from app.models.schemas import (
    ExecutionPlan,
    ExecutionTrace,
    PlanStep,
    StepStatus,
    TraceStatus,
)
from app.tools.detectors import run_rule_detectors
from app.tools.eda import run_eda
from app.tools.explain import explain_flags
from app.tools.features import FEATURE_COLUMNS, engineer_features
from app.tools.isolation_forest import detect_anomalies
from app.tools.risk import fuse_entity_risk, fuse_overall_risk


RAW_TRANSACTIONS: Final = "raw_transactions"
CURRENT_TRANSACTIONS: Final = "current_transactions"


def execute_plan(
    plan: ExecutionPlan,
    transactions: pd.DataFrame,
) -> dict[str, Any]:
    """Execute a copy of ``plan`` sequentially and return it with its context.

    Execution stops after the first failed step. The returned context records
    failure details, while the caller's plan and DataFrame remain unchanged.
    """
    workflow_start = time.perf_counter()
    execution_plan = plan.model_copy(deep=True)
    execution_plan.steps = sorted(
        execution_plan.steps,
        key=lambda step: step.step_number,
    )
    raw_transactions = transactions.copy(deep=True)
    context: dict[str, Any] = {
        RAW_TRANSACTIONS: raw_transactions,
        CURRENT_TRANSACTIONS: raw_transactions,
    }
    invoked_tools: list[str] = []
    execution_timings_ms: dict[str, float] = {}
    completed_steps = 0
    failed_tool: str | None = None

    for step in execution_plan.steps:
        step.status = StepStatus.IN_PROGRESS
        invoked_tools.append(step.tool_name)
        step_start = time.perf_counter()
        try:
            result, summary = _dispatch_step(step, execution_plan, context)
        except Exception as error:
            step.status = StepStatus.FAILED
            step.result_summary = f"{type(error).__name__}: {error}"
            context["error"] = {
                "step_number": step.step_number,
                "tool_name": step.tool_name,
                "message": step.result_summary,
            }
            failed_tool = step.tool_name
            break
        finally:
            timing_key = _next_timing_key(step.tool_name, execution_timings_ms)
            execution_timings_ms[timing_key] = max(
                0.0,
                (time.perf_counter() - step_start) * 1000,
            )

        step.result_summary = summary
        step.status = StepStatus.COMPLETED
        context[f"{step.tool_name}_result"] = result
        completed_steps += 1

    execution_plan.invoked_tools = invoked_tools
    trace = _build_execution_trace(
        execution_plan=execution_plan,
        invoked_tools=invoked_tools,
        execution_timings_ms=execution_timings_ms,
        total_execution_time_ms=max(0.0, (time.perf_counter() - workflow_start) * 1000),
        completed_steps=completed_steps,
        failed_tool=failed_tool,
        error=context.get("error"),
    )

    return {"plan": execution_plan, "context": context, "trace": trace}


def _build_execution_trace(
    execution_plan: ExecutionPlan,
    invoked_tools: list[str],
    execution_timings_ms: dict[str, float],
    total_execution_time_ms: float,
    completed_steps: int,
    failed_tool: str | None,
    error: dict[str, Any] | None,
) -> ExecutionTrace:
    """Build telemetry from actual runtime execution without mutating plan inputs."""
    if failed_tool is None:
        status = TraceStatus.SUCCESS
        error_message = None
    else:
        status = TraceStatus.PARTIAL_SUCCESS if completed_steps else TraceStatus.FAILED
        failure_message = error.get("message", "Execution failed") if error else "Execution failed"
        error_message = f"{failed_tool}: {failure_message}"

    return ExecutionTrace(
        query_id=execution_plan.plan_id,
        detected_intent=execution_plan.detected_intent,
        active_filters=deepcopy(execution_plan.active_filters),
        invoked_tools=invoked_tools.copy(),
        skipped_tools=[tool.model_copy(deep=True) for tool in execution_plan.skipped_tools],
        execution_timings_ms=execution_timings_ms.copy(),
        total_execution_time_ms=total_execution_time_ms,
        status=status,
        error_message=error_message,
    )


def _next_timing_key(tool_name: str, timings: dict[str, float]) -> str:
    """Return a stable, non-conflicting timing key for a tool invocation."""
    if tool_name not in timings:
        return tool_name

    occurrence = 2
    while f"{tool_name}#{occurrence}" in timings:
        occurrence += 1
    return f"{tool_name}#{occurrence}"


def _dispatch_step(
    step: PlanStep,
    plan: ExecutionPlan,
    context: dict[str, Any],
) -> tuple[Any, str]:
    if step.tool_name == "eda":
        result = run_eda(
            context[CURRENT_TRANSACTIONS],
            **_compatible_parameters(step.parameters, {"top_n"}),
        )
        context["eda_result"] = result
        return result, f"EDA completed with {len(result)} report sections"

    if step.tool_name == "features":
        result = engineer_features(
            context[CURRENT_TRANSACTIONS],
            **_compatible_parameters(step.parameters, {"window", "sub_threshold"}),
        )
        context["featured_transactions"] = result
        context[CURRENT_TRANSACTIONS] = result
        return result, f"Engineered {len(FEATURE_COLUMNS)} features for {len(result)} transactions"

    if step.tool_name == "detectors_ml":
        featured_transactions = context.get("featured_transactions")
        if featured_transactions is None:
            featured_transactions = engineer_features(
                context[RAW_TRANSACTIONS],
                **_compatible_parameters(step.parameters, {"window", "sub_threshold"}),
            )
            context["featured_transactions"] = featured_transactions

        result = detect_anomalies(
            featured_transactions,
            **_compatible_parameters(step.parameters, {"contamination", "random_state"}),
        )
        context["ml_scored_transactions"] = result
        context[CURRENT_TRANSACTIONS] = result
        anomaly_count = int(result["is_anomaly"].sum()) if "is_anomaly" in result else 0
        return result, f"ML scored {len(result)} transactions and found {anomaly_count} anomalies"

    if step.tool_name == "detectors_rules":
        result = run_rule_detectors(
            context[RAW_TRANSACTIONS],
            **_compatible_parameters(step.parameters, {"entity_id", "rules"}),
        )
        context["rule_flags"] = result
        return result, f"Rule detectors produced {len(result)} flags"

    if step.tool_name == "risk":
        rule_flags = context.get("rule_flags", [])
        entity_id = _resolve_entity_id(step, plan)
        ml_score = _normalized_ml_risk_score(
            context.get("ml_scored_transactions"),
            entity_id,
        )

        if entity_id:
            result = fuse_entity_risk(
                entity_id=entity_id,
                flags=rule_flags,
                ml_score=ml_score,
            )
        else:
            result = fuse_overall_risk(
                flags=rule_flags,
                ml_score=ml_score,
                total_transactions=len(context[RAW_TRANSACTIONS]),
            )

        context["risk_result"] = result
        return result, f"Risk fusion completed: {result.risk_tier.value} ({result.risk_score:.4f})"

    if step.tool_name == "explain":
        result = explain_flags(context.get("rule_flags", []))
        context["explanations"] = result
        return result, f"Generated {len(result)} flag explanations"

    raise ValueError(f"Unsupported plan tool: {step.tool_name}")


def _compatible_parameters(
    parameters: dict[str, Any],
    supported_names: set[str],
) -> dict[str, Any]:
    return {
        name: value
        for name, value in parameters.items()
        if name in supported_names
    }


def _resolve_entity_id(step: PlanStep, plan: ExecutionPlan) -> str | None:
    parameter_entity = step.parameters.get("entity_id")
    if isinstance(parameter_entity, str) and parameter_entity:
        return parameter_entity
    return plan.target_entities[0] if plan.target_entities else None


def _normalized_ml_risk_score(
    scored_transactions: pd.DataFrame | None,
    entity_id: str | None,
) -> float | None:
    """Return a finite, batch-normalized ML score for risk fusion.

    Isolation Forest anomaly scores are unbounded, so they are min-max
    normalized across the scored batch before selecting an overall or
    entity-specific maximum. Higher values remain more anomalous.
    """
    if scored_transactions is None or "anomaly_score" not in scored_transactions.columns:
        return None

    numeric_scores = pd.to_numeric(
        scored_transactions["anomaly_score"],
        errors="coerce",
    )
    finite_mask = np.isfinite(numeric_scores.to_numpy(dtype=float, na_value=np.nan))
    finite_scores = numeric_scores.loc[finite_mask]
    if finite_scores.empty:
        return None

    minimum = float(finite_scores.min())
    maximum = float(finite_scores.max())
    if minimum == maximum:
        normalized_scores = pd.Series(0.0, index=finite_scores.index)
    else:
        normalized_scores = (finite_scores - minimum) / (maximum - minimum)

    if entity_id is None:
        return float(normalized_scores.max())

    required_entity_columns = {"From Account", "To Account"}
    if not required_entity_columns.issubset(scored_transactions.columns):
        return None

    entity_mask = (
        (scored_transactions["From Account"] == entity_id)
        | (scored_transactions["To Account"] == entity_id)
    )
    matching_finite_rows = entity_mask.to_numpy(dtype=bool, na_value=False)[finite_mask]
    entity_scores = normalized_scores.iloc[np.flatnonzero(matching_finite_rows)]
    return float(entity_scores.max()) if not entity_scores.empty else None
