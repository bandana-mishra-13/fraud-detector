from datetime import datetime
import pytest
from pydantic import ValidationError

from app.models.schemas import (
    ExecutionPlan,
    ExecutionTrace,
    Flag,
    PlanStep,
    RiskResult,
    RiskTier,
    SkippedTool,
    StepStatus,
    TraceStatus,
    Transaction,
)


# ============================================================================
# 1. Transaction Schema Tests
# ============================================================================

def test_transaction_creation_valid_dict_alias():
    """Test creating a Transaction model from a dictionary with CSV column aliases."""
    raw_data = {
        "Timestamp": "2022/09/01 14:10",
        "From Bank": "150",
        "From Account": "ACC015",
        "To Bank": "160",
        "To Account": "ACC016",
        "Amount Received": 9990.00,
        "Receiving Currency": "US Dollar",
        "Amount Paid": 9990.00,
        "Payment Currency": "US Dollar",
        "Payment Format": "Wire",
        "Is Laundering": 1,
    }
    tx = Transaction(**raw_data)
    assert tx.from_account == "ACC015"
    assert tx.to_account == "ACC016"
    assert tx.amount_received == 9990.00
    assert tx.amount_paid == 9990.00
    assert tx.payment_format == "Wire"
    assert tx.is_laundering == 1
    assert tx.transaction_id is not None


def test_transaction_creation_valid_field_names():
    """Test creating a Transaction model using Python attribute names."""
    tx = Transaction(
        timestamp="2022/09/01 00:20",
        from_account="ACC001",
        to_account="ACC002",
        amount_received=2500.0,
        amount_paid=2500.0,
    )
    assert tx.from_account == "ACC001"
    assert tx.to_account == "ACC002"
    assert tx.amount_received == 2500.0
    assert tx.receiving_currency == "US Dollar"
    assert tx.is_laundering == 0


def test_transaction_validation_negative_amount():
    """Test that negative transaction amounts raise a ValidationError."""
    with pytest.raises(ValidationError):
        Transaction(
            timestamp="2022/09/01 00:20",
            from_account="ACC001",
            to_account="ACC002",
            amount_received=-500.0,
            amount_paid=500.0,
        )


def test_transaction_validation_invalid_laundering_flag():
    """Test that invalid is_laundering flag values raise a ValidationError."""
    with pytest.raises(ValidationError):
        Transaction(
            timestamp="2022/09/01 00:20",
            from_account="ACC001",
            to_account="ACC002",
            amount_received=100.0,
            amount_paid=100.0,
            is_laundering=5,  # Must be 0 or 1
        )


# ============================================================================
# 2. Flag Schema Tests
# ============================================================================

def test_flag_creation_valid():
    """Test creating a valid Flag instance."""
    flag = Flag(
        rule_id="STRUCTURING_01",
        rule_name="Rapid Transactions Below Threshold",
        severity=RiskTier.HIGH,
        entity_id="ACC015",
        transaction_ids=["TX101", "TX102"],
        typology="Structuring",
        reason="3 transactions executed within 30 minutes totaling $29,840",
        evidence={"count": 3, "total_amount": 29840.0, "time_window_mins": 30},
    )
    assert flag.rule_id == "STRUCTURING_01"
    assert flag.severity == RiskTier.HIGH
    assert flag.entity_id == "ACC015"
    assert len(flag.transaction_ids) == 2
    assert flag.evidence["count"] == 3
    assert isinstance(flag.timestamp, datetime)


def test_flag_validation_invalid_severity():
    """Test that invalid severity values raise a ValidationError."""
    with pytest.raises(ValidationError):
        Flag(
            rule_id="RULE_01",
            rule_name="Test Rule",
            severity="EXTREME",  # Invalid enum value
            reason="Test reason",
        )


# ============================================================================
# 3. ExecutionPlan Schema Tests
# ============================================================================

def test_execution_plan_creation_valid():
    """Test creating a valid ExecutionPlan with ordered steps and skipped tools."""
    step1 = PlanStep(
        step_number=1,
        tool_name="rule_detector",
        description="Run deterministic structuring and fan-out rule detectors",
        parameters={"entity_id": "ACC015"},
        status=StepStatus.COMPLETED,
    )
    step2 = PlanStep(
        step_number=2,
        tool_name="ml_anomaly_detector",
        description="Compute isolation forest anomaly score",
        parameters={"entity_id": "ACC015"},
        status=StepStatus.PENDING,
    )
    skipped = SkippedTool(
        tool_name="graph_network_analyzer",
        reason="Graph analysis tool disabled for single-node entity queries",
    )
    plan = ExecutionPlan(
        query="Investigate suspicious activity for account ACC015",
        detected_intent="INVESTIGATE_ACCOUNT",
        active_filters={"entity_id": "ACC015", "time_window": "30d"},
        target_entities=["ACC015"],
        steps=[step1, step2],
        invoked_tools=["rule_detector"],
        skipped_tools=[skipped],
        reasoning="Prioritize rapid rule check followed by ML anomaly detection.",
    )
    assert plan.detected_intent == "INVESTIGATE_ACCOUNT"
    assert len(plan.steps) == 2
    assert plan.steps[0].step_number == 1
    assert plan.steps[0].status == StepStatus.COMPLETED
    assert plan.skipped_tools[0].tool_name == "graph_network_analyzer"


def test_plan_step_validation_invalid_step_number():
    """Test that non-positive step numbers raise a ValidationError."""
    with pytest.raises(ValidationError):
        PlanStep(
            step_number=0,  # Invalid ge=1
            tool_name="rule_detector",
            description="Run rule detector",
        )


# ============================================================================
# 4. RiskResult Schema Tests
# ============================================================================

def test_risk_result_creation_valid():
    """Test creating a valid RiskResult instance."""
    flag = Flag(
        rule_id="FAN_OUT_01",
        rule_name="Rapid Fan-Out",
        severity=RiskTier.MEDIUM,
        entity_id="ACC015",
        reason="Entity transferred funds to multiple downstream accounts",
    )
    res = RiskResult(
        entity_id="ACC015",
        risk_score=0.85,
        risk_tier=RiskTier.HIGH,
        flags=[flag],
        rule_score=0.90,
        ml_score=0.80,
        summary="High risk account due to rapid fan-out structuring pattern.",
        evidence_summary={"flag_count": 1, "max_severity": "MEDIUM"},
    )
    assert res.entity_id == "ACC015"
    assert res.risk_score == 0.85
    assert res.risk_tier == RiskTier.HIGH
    assert len(res.flags) == 1
    assert res.rule_score == 0.90
    assert res.ml_score == 0.80


def test_risk_result_validation_out_of_bounds_score():
    """Test that risk scores outside [0.0, 1.0] raise a ValidationError."""
    with pytest.raises(ValidationError):
        RiskResult(
            risk_score=1.5,  # Out of bounds (> 1.0)
            risk_tier=RiskTier.CRITICAL,
            summary="Invalid score test",
        )

    with pytest.raises(ValidationError):
        RiskResult(
            risk_score=-0.1,  # Out of bounds (< 0.0)
            risk_tier=RiskTier.LOW,
            summary="Invalid score test",
        )


# ============================================================================
# 5. ExecutionTrace Schema Tests
# ============================================================================

def test_execution_trace_creation_valid():
    """Test creating a valid ExecutionTrace telemetry model."""
    skipped = SkippedTool(
        tool_name="heavy_llm_summarizer",
        reason="Skipped for fast deterministic response mode",
    )
    trace = ExecutionTrace(
        query_id="QRY-9921",
        detected_intent="QUICK_RISK_CHECK",
        active_filters={"entity_id": "ACC002"},
        invoked_tools=["rule_detector", "feature_extractor"],
        skipped_tools=[skipped],
        execution_timings_ms={"rule_detector": 12.5, "feature_extractor": 4.2},
        total_execution_time_ms=16.7,
        status=TraceStatus.SUCCESS,
    )
    assert trace.query_id == "QRY-9921"
    assert trace.detected_intent == "QUICK_RISK_CHECK"
    assert len(trace.invoked_tools) == 2
    assert trace.total_execution_time_ms == 16.7
    assert trace.status == TraceStatus.SUCCESS
    assert trace.error_message is None
