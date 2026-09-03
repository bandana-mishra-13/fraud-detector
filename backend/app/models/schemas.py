import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskTier(str, Enum):
    """Risk severity categorization level."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StepStatus(str, Enum):
    """Execution status of an individual plan step."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class TraceStatus(str, Enum):
    """Overall outcome status of an execution trace."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"


def generate_uuid() -> str:
    """Utility to generate a string UUID4."""
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    """Utility to get timezone-aware UTC current datetime."""
    return datetime.now(timezone.utc)


class Transaction(BaseModel):
    """
    Structured representation of an AML transaction.
    Compatible with IBM AML dataset schema (HI-Small_Trans.csv) and application tools.
    """
    model_config = ConfigDict(populate_by_name=True)

    transaction_id: str = Field(
        default_factory=generate_uuid,
        description="Unique transaction ID. Auto-generated if not provided."
    )
    timestamp: str = Field(
        ...,
        alias="Timestamp",
        description="Date/time of transaction (e.g., '2022/09/01 00:20' or ISO format)"
    )
    from_bank: str = Field(
        default="",
        alias="From Bank",
        description="Identifier of the sending bank"
    )
    from_account: str = Field(
        ...,
        alias="From Account",
        description="Identifier of the sending account"
    )
    to_bank: str = Field(
        default="",
        alias="To Bank",
        description="Identifier of the receiving bank"
    )
    to_account: str = Field(
        ...,
        alias="To Account",
        description="Identifier of the receiving account"
    )
    amount_received: float = Field(
        ...,
        ge=0.0,
        alias="Amount Received",
        description="Amount received in destination account"
    )
    receiving_currency: str = Field(
        default="US Dollar",
        alias="Receiving Currency",
        description="Currency received"
    )
    amount_paid: float = Field(
        ...,
        ge=0.0,
        alias="Amount Paid",
        description="Amount sent from origin account"
    )
    payment_currency: str = Field(
        default="US Dollar",
        alias="Payment Currency",
        description="Currency paid"
    )
    payment_format: str = Field(
        default="Wire",
        alias="Payment Format",
        description="Payment format/instrument (e.g., Cash, Wire, ACH, Cheque)"
    )
    is_laundering: int = Field(
        default=0,
        alias="Is Laundering",
        description="Ground truth laundering label (0 = Legitimate, 1 = Suspicious/Laundering)"
    )

    @field_validator("is_laundering")
    @classmethod
    def validate_is_laundering(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("is_laundering must be either 0 or 1")
        return v


class Flag(BaseModel):
    """
    Structured AML rule finding / detection flag model.
    Represents suspicious activity identified by rule detectors or ML anomaly algorithms.
    """
    model_config = ConfigDict(populate_by_name=True)

    flag_id: str = Field(
        default_factory=generate_uuid,
        description="Unique flag identifier"
    )
    rule_id: str = Field(
        ...,
        description="Identifier of the rule or detector that triggered the flag (e.g., 'STRUCTURING_01')"
    )
    rule_name: str = Field(
        ...,
        description="Human-readable rule name"
    )
    severity: RiskTier = Field(
        ...,
        description="Severity level of the flag (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    entity_id: Optional[str] = Field(
        default=None,
        description="Primary entity/account involved in the finding"
    )
    transaction_ids: List[str] = Field(
        default_factory=list,
        description="List of related transaction IDs associated with this flag"
    )
    typology: Optional[str] = Field(
        default=None,
        description="AML typology pattern (e.g., 'Structuring', 'Fan-out', 'Pass-through', 'Smurfing')"
    )
    reason: str = Field(
        ...,
        description="Detailed explanation of why the flag was triggered"
    )
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting metric evidence (e.g., transaction count, total amount, thresholds)"
    )
    timestamp: datetime = Field(
        default_factory=get_utc_now,
        description="Timestamp when the flag was generated"
    )


class PlanStep(BaseModel):
    """Individual analytical step in an ExecutionPlan."""
    step_number: int = Field(..., ge=1, description="1-based ordered index of the plan step")
    tool_name: str = Field(..., description="Name of the analytical tool to invoke")
    description: str = Field(..., description="Description of the step objective")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the tool")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Execution status of the step")
    result_summary: Optional[str] = Field(default=None, description="Summary of step execution output")


class SkippedTool(BaseModel):
    """Tool skipped during plan execution with rationale."""
    tool_name: str = Field(..., description="Name of the tool skipped")
    reason: str = Field(..., description="Rationale for skipping the tool")


class ExecutionPlan(BaseModel):
    """
    Schema representing a dynamic execution plan generated by the LLM planner / agent.
    Describes ordered steps, target entities, active filters, and skipped tools.
    """
    model_config = ConfigDict(populate_by_name=True)

    plan_id: str = Field(
        default_factory=generate_uuid,
        description="Unique execution plan ID"
    )
    query: str = Field(
        ...,
        description="Original user investigation query"
    )
    detected_intent: str = Field(
        ...,
        description="Inferred intent (e.g., 'INVESTIGATE_ACCOUNT', 'TYPOLOGY_SEARCH')"
    )
    active_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Active context filters (e.g., time window, min amount, currency)"
    )
    target_entities: List[str] = Field(
        default_factory=list,
        description="Entities/accounts targeted in the plan"
    )
    steps: List[PlanStep] = Field(
        default_factory=list,
        description="Ordered analytical tool steps to execute"
    )
    invoked_tools: List[str] = Field(
        default_factory=list,
        description="List of tool names invoked during execution"
    )
    skipped_tools: List[SkippedTool] = Field(
        default_factory=list,
        description="List of tools skipped with explanation"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="LLM planner rationale for the generated plan"
    )
    created_at: datetime = Field(
        default_factory=get_utc_now,
        description="Plan creation timestamp"
    )


class RiskResult(BaseModel):
    """
    Schema representing the overall risk assessment for an entity or transaction.
    Combines rule-based flags, ML anomaly scores, and risk tier categorization.
    """
    model_config = ConfigDict(populate_by_name=True)

    result_id: str = Field(
        default_factory=generate_uuid,
        description="Unique risk result ID"
    )
    entity_id: Optional[str] = Field(
        default=None,
        description="Account or bank ID assessed"
    )
    transaction_id: Optional[str] = Field(
        default=None,
        description="Transaction ID assessed if transaction-specific"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized aggregate risk score between 0.0 and 1.0"
    )
    risk_tier: RiskTier = Field(
        ...,
        description="Risk tier categorization (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    flags: List[Flag] = Field(
        default_factory=list,
        description="AML flags contributing to the risk score"
    )
    rule_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Component score from deterministic rule engine"
    )
    ml_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Component score from ML anomaly detector"
    )
    summary: str = Field(
        ...,
        description="Natural language summary of the risk assessment"
    )
    evidence_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated metrics and supporting evidence"
    )
    created_at: datetime = Field(
        default_factory=get_utc_now,
        description="Assessment generation timestamp"
    )


class ExecutionTrace(BaseModel):
    """
    Schema representing execution telemetry and trace audit logging for agentic workflows.
    Records timings, active filters, invoked/skipped tools, and step outcomes.
    """
    model_config = ConfigDict(populate_by_name=True)

    trace_id: str = Field(
        default_factory=generate_uuid,
        description="Unique execution trace ID"
    )
    query_id: Optional[str] = Field(
        default=None,
        description="Identifier of the associated request/query"
    )
    detected_intent: str = Field(
        ...,
        description="Detected user query intent"
    )
    active_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Active context filters applied during execution"
    )
    invoked_tools: List[str] = Field(
        default_factory=list,
        description="Names of tools executed during the workflow"
    )
    skipped_tools: List[SkippedTool] = Field(
        default_factory=list,
        description="Tools skipped during execution with rationale"
    )
    execution_timings_ms: Dict[str, float] = Field(
        default_factory=dict,
        description="Execution duration per tool step in milliseconds"
    )
    total_execution_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Total workflow execution duration in milliseconds"
    )
    status: TraceStatus = Field(
        default=TraceStatus.SUCCESS,
        description="Workflow outcome status (SUCCESS, FAILED, PARTIAL_SUCCESS)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if workflow failed or encountered warnings"
    )
    created_at: datetime = Field(
        default_factory=get_utc_now,
        description="Trace record creation timestamp"
    )
