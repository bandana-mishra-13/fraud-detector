"""Core data contracts shared by the tools, the agent, and the API.

These mirror the problem statement's vocabulary: flags carry a risk level,
a plain-English reason, and an escalation action; the execution plan records
what the agent decided — including the tools it chose to SKIP and why.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Escalation(str, Enum):
    MONITOR = "monitor"
    REVIEW = "review"
    REPORT = "report"


class AMLPattern(str, Enum):
    STRUCTURING = "structuring"
    SMURFING = "smurfing"
    LAYERING = "layering"
    RAPID_CASH_OUT = "rapid_cash_out"
    VELOCITY = "velocity"
    ANOMALY = "anomaly"  # ML-detected, no named typology


class Transaction(BaseModel):
    """One normalized row of the IBM AML transactions data."""

    timestamp: datetime
    from_bank: str
    from_account: str
    to_bank: str
    to_account: str
    amount_received: float
    receiving_currency: str
    amount_paid: float
    payment_currency: str
    payment_format: str
    is_laundering: bool = False


class QueryFilters(BaseModel):
    """Filters the agent extracts from a natural-language query.

    Note: the dataset has no country/segment columns, so those filter types
    map to banks, currencies, and payment formats (documented in README).
    """

    date_from: datetime | None = None
    date_to: datetime | None = None
    last_n_days: int | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str | None = None
    payment_format: str | None = None
    bank: str | None = None
    account: str | None = None
    customer: str | None = None  # entity id or "#4521"-style name suffix
    min_txn_count: int | None = None


class PlanStep(BaseModel):
    """One tool decision in the agent's execution plan."""

    tool: str
    action: Literal["invoked", "skipped"]
    reason: str
    params: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = None


class ExecutionPlan(BaseModel):
    """The judge-inspectable record of what the agent decided and why."""

    query: str
    intent: str
    pattern: AMLPattern | None = None
    filters: QueryFilters = Field(default_factory=QueryFilters)
    steps: list[PlanStep] = Field(default_factory=list)


class Flag(BaseModel):
    """One suspicious entity, with the explanation and escalation the
    problem statement requires."""

    entity_type: Literal["transaction", "account", "customer"]
    entity_id: str
    pattern: AMLPattern
    risk_level: RiskLevel
    score: float = Field(ge=0.0, le=1.0)
    reason: str
    escalation: Escalation
    evidence: dict[str, Any] = Field(default_factory=dict)


class RiskResult(BaseModel):
    """Full structured response for one analysis run."""

    run_id: str
    plan: ExecutionPlan
    flags: list[Flag] = Field(default_factory=list)
    kpis: dict[str, Any] = Field(default_factory=dict)
    charts: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
