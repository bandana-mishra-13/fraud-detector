"""Unit tests for the SQLite AuditStore (Task 1.4)."""

import os
import tempfile
import pytest
from datetime import datetime, timezone

from app.models.schemas import (
    ExecutionPlan,
    ExecutionTrace,
    Flag,
    PlanStep,
    RiskTier,
    SkippedTool,
    StepStatus,
    TraceStatus,
)
from app.storage.audit_store import AuditStore, get_audit_store


@pytest.fixture
def memory_audit_store() -> AuditStore:
    """Fixture providing an initialized in-memory AuditStore."""
    store = AuditStore(db_path=":memory:")
    store.init_db()
    return store


@pytest.fixture
def temp_audit_store() -> tuple[AuditStore, str]:
    """Fixture providing a file-backed AuditStore in a temp directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_audit.db")
        store = AuditStore(db_path=db_path)
        store.init_db()
        yield store, db_path


def test_init_db_tables_and_indexes(memory_audit_store: AuditStore):
    """Verify that all required tables and indexes are created upon init_db()."""
    with memory_audit_store.get_connection() as conn:
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        assert "audit_queries" in tables
        assert "audit_flags" in tables
        assert "audit_feedback" in tables

        indexes = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        assert "idx_queries_query_id" in indexes
        assert "idx_flags_flag_id" in indexes
        assert "idx_flags_query_id" in indexes
        assert "idx_flags_entity_id" in indexes
        assert "idx_flags_severity" in indexes
        assert "idx_feedback_flag_id" in indexes


def test_temp_file_based_audit_store(temp_audit_store: tuple[AuditStore, str]):
    """Verify that file-based AuditStore creates the sqlite file and functions properly."""
    store, db_path = temp_audit_store
    assert os.path.isfile(db_path)

    query_id = store.log_query(
        query_text="Investigate high volume structuring",
        detected_intent="TYPOLOGY_SEARCH",
        execution_time_ms=124.5,
    )
    assert query_id is not None

    record = store.get_query(query_id)
    assert record is not None
    assert record["query_text"] == "Investigate high volume structuring"
    assert record["detected_intent"] == "TYPOLOGY_SEARCH"
    assert record["execution_time_ms"] == 124.5


def test_log_query_and_get_query(memory_audit_store: AuditStore):
    """Test full query logging with filters, targets, and tool details."""
    query_id = memory_audit_store.log_query(
        query_id="query-12345",
        query_text="Find structuring patterns for account ACCT_9988",
        detected_intent="INVESTIGATE_ACCOUNT",
        active_filters={"min_amount": 9000, "time_window_days": 30},
        target_entities=["ACCT_9988"],
        invoked_tools=["structuring_detector", "profiler"],
        skipped_tools=[{"tool_name": "ml_anomaly", "reason": "Deterministic rule query"}],
        execution_time_ms=250.0,
        status="SUCCESS",
        metadata={"user_role": "compliance_analyst"},
    )

    assert query_id == "query-12345"

    query_record = memory_audit_store.get_query("query-12345")
    assert query_record is not None
    assert query_record["query_id"] == "query-12345"
    assert query_record["query_text"] == "Find structuring patterns for account ACCT_9988"
    assert query_record["detected_intent"] == "INVESTIGATE_ACCOUNT"
    assert query_record["active_filters"] == {"min_amount": 9000, "time_window_days": 30}
    assert query_record["target_entities"] == ["ACCT_9988"]
    assert query_record["invoked_tools"] == ["structuring_detector", "profiler"]
    assert len(query_record["skipped_tools"]) == 1
    assert query_record["skipped_tools"][0]["tool_name"] == "ml_anomaly"
    assert query_record["execution_time_ms"] == 250.0
    assert query_record["status"] == "SUCCESS"
    assert query_record["metadata"]["user_role"] == "compliance_analyst"


def test_get_queries_pagination_and_filter(memory_audit_store: AuditStore):
    """Test retrieving query logs with pagination and filters."""
    for i in range(5):
        memory_audit_store.log_query(
            query_id=f"q-{i}",
            query_text=f"Query {i}",
            detected_intent="TYPOLOGY_SEARCH" if i % 2 == 0 else "ENTITY_LOOKUP",
            status="SUCCESS" if i < 4 else "FAILED",
        )

    all_queries = memory_audit_store.get_queries(limit=10)
    assert len(all_queries) == 5

    typology_queries = memory_audit_store.get_queries(intent="TYPOLOGY_SEARCH")
    assert len(typology_queries) == 3

    failed_queries = memory_audit_store.get_queries(status="FAILED")
    assert len(failed_queries) == 1
    assert failed_queries[0]["query_id"] == "q-4"

    paginated = memory_audit_store.get_queries(limit=2, offset=0)
    assert len(paginated) == 2


def test_log_execution_plan_helper(memory_audit_store: AuditStore):
    """Test log_execution_plan convenience method with Pydantic model."""
    plan = ExecutionPlan(
        plan_id="plan-777",
        query="Analyze smurfing network",
        detected_intent="TYPOLOGY_SEARCH",
        active_filters={"currency": "USD"},
        target_entities=["ACCT_001", "ACCT_002"],
        steps=[
            PlanStep(
                step_number=1,
                tool_name="features",
                description="Extract rolling velocity",
                status=StepStatus.COMPLETED,
            )
        ],
        invoked_tools=["features", "smurfing_detector"],
        skipped_tools=[
            SkippedTool(tool_name="eda", reason="Targeted typology query")
        ],
        reasoning="Smurfing detected via rapid aggregation",
    )

    logged_id = memory_audit_store.log_execution_plan(plan, execution_time_ms=88.5)
    assert logged_id == "plan-777"

    record = memory_audit_store.get_query("plan-777")
    assert record is not None
    assert record["detected_intent"] == "TYPOLOGY_SEARCH"
    assert record["invoked_tools"] == ["features", "smurfing_detector"]
    assert record["skipped_tools"][0]["tool_name"] == "eda"
    assert record["metadata"]["reasoning"] == "Smurfing detected via rapid aggregation"


def test_log_execution_trace_helper(memory_audit_store: AuditStore):
    """Test log_execution_trace convenience method with Pydantic model."""
    trace = ExecutionTrace(
        trace_id="trace-999",
        query_id="query-origin-1",
        detected_intent="INVESTIGATE_ACCOUNT",
        active_filters={"account": "ACCT_123"},
        invoked_tools=["detectors_rules", "explain"],
        skipped_tools=[SkippedTool(tool_name="eda", reason="Account targeted")],
        execution_timings_ms={"detectors_rules": 45.2, "explain": 20.1},
        total_execution_time_ms=65.3,
        status=TraceStatus.SUCCESS,
    )

    logged_id = memory_audit_store.log_execution_trace(trace, query_text="Check account ACCT_123")
    assert logged_id == "query-origin-1"

    record = memory_audit_store.get_query("query-origin-1")
    assert record is not None
    assert record["query_text"] == "Check account ACCT_123"
    assert record["execution_time_ms"] == 65.3
    assert record["metadata"]["execution_timings_ms"]["detectors_rules"] == 45.2


def test_log_flags_and_query_by_filters(memory_audit_store: AuditStore):
    """Test logging Pydantic Flags and querying by entity, severity, and rule_id."""
    flags = [
        Flag(
            flag_id="flag-001",
            rule_id="STRUCTURING_01",
            rule_name="Multiple sub-$10k deposits",
            severity=RiskTier.HIGH,
            entity_id="ACCT_1001",
            transaction_ids=["TX_1", "TX_2", "TX_3"],
            typology="Structuring",
            reason="4 transactions of $9,500 within 24 hours",
            evidence={"tx_count": 4, "total_amount": 38000.0, "threshold": 10000.0},
        ),
        Flag(
            flag_id="flag-002",
            rule_id="RAPID_MOVEMENT_01",
            rule_name="Rapid layering pass-through",
            severity=RiskTier.CRITICAL,
            entity_id="ACCT_1002",
            transaction_ids=["TX_4", "TX_5"],
            typology="Pass-through",
            reason="Funds moved out within 3 minutes of deposit",
            evidence={"time_delta_sec": 180, "in_amount": 50000.0, "out_amount": 49800.0},
        ),
        Flag(
            flag_id="flag-003",
            rule_id="ML_ANOMALY_01",
            rule_name="Isolation Forest Anomaly",
            severity=RiskTier.MEDIUM,
            entity_id="ACCT_1001",
            transaction_ids=["TX_6"],
            typology="Statistical Anomaly",
            reason="High deviation in counterparty fan-out",
            evidence={"anomaly_score": 0.78},
        ),
    ]

    logged_ids = memory_audit_store.log_flags(flags, query_id="query-demo-1", rule_version="v1.0")
    assert logged_ids == ["flag-001", "flag-002", "flag-003"]

    # Filter by query_id
    query_flags = memory_audit_store.get_flags(query_id="query-demo-1")
    assert len(query_flags) == 3

    # Filter by entity_id
    acct1001_flags = memory_audit_store.get_flags(entity_id="ACCT_1001")
    assert len(acct1001_flags) == 2

    # Filter by severity
    critical_flags = memory_audit_store.get_flags(severity=RiskTier.CRITICAL)
    assert len(critical_flags) == 1
    assert critical_flags[0]["flag_id"] == "flag-002"
    assert critical_flags[0]["transaction_ids"] == ["TX_4", "TX_5"]
    assert critical_flags[0]["evidence"]["time_delta_sec"] == 180

    # Filter by rule_id
    structuring_flags = memory_audit_store.get_flags(rule_id="STRUCTURING_01")
    assert len(structuring_flags) == 1
    assert structuring_flags[0]["rule_name"] == "Multiple sub-$10k deposits"


def test_log_flags_from_dict(memory_audit_store: AuditStore):
    """Test logging flags passed as dictionaries."""
    dict_flags = [
        {
            "flag_id": "flag-dict-1",
            "rule_id": "FAN_OUT_01",
            "rule_name": "High Fan-out Ratio",
            "severity": "HIGH",
            "entity_id": "ACCT_3001",
            "transaction_ids": ["TX_10", "TX_11"],
            "typology": "Fan-Out",
            "reason": "1 account distributed funds to 12 accounts in 1 hour",
            "evidence": {"fan_out_degree": 12},
        }
    ]

    logged_ids = memory_audit_store.log_flags(dict_flags, query_id="query-dict-1")
    assert logged_ids == ["flag-dict-1"]

    retrieved = memory_audit_store.get_flag("flag-dict-1")
    assert retrieved is not None
    assert retrieved["entity_id"] == "ACCT_3001"
    assert retrieved["severity"] == "HIGH"
    assert retrieved["evidence"]["fan_out_degree"] == 12
    assert retrieved["feedback_status"] == "PENDING"


def test_log_feedback_and_audit_trail(memory_audit_store: AuditStore):
    """Test recording analyst feedback, updating flag status, and tracking feedback audit history."""
    flags = [
        Flag(
            flag_id="flag-fb-1",
            rule_id="STRUCTURING_01",
            rule_name="Structuring Rule",
            severity=RiskTier.HIGH,
            entity_id="ACCT_5001",
            reason="Structuring detected",
        )
    ]
    memory_audit_store.log_flags(flags, query_id="q-fb-1")

    # Initial state
    flag_record = memory_audit_store.get_flag("flag-fb-1")
    assert flag_record["feedback_status"] == "PENDING"
    assert flag_record["analyst_notes"] is None
    assert flag_record["feedback_history"] == []

    # First feedback event (Analyst 1 marks under review)
    fb1 = memory_audit_store.log_feedback(
        flag_id="flag-fb-1",
        feedback_status="UNDER_REVIEW",
        analyst_id="analyst_alice",
        notes="Opening SAR review case",
    )
    assert fb1["feedback_status"] == "UNDER_REVIEW"

    updated = memory_audit_store.get_flag("flag-fb-1")
    assert updated["feedback_status"] == "UNDER_REVIEW"
    assert updated["analyst_notes"] == "Opening SAR review case"
    assert len(updated["feedback_history"]) == 1

    # Second feedback event (Analyst 2 confirms suspicious)
    fb2 = memory_audit_store.log_feedback(
        flag_id="flag-fb-1",
        feedback_status="CONFIRMED_SUSPICIOUS",
        analyst_id="analyst_bob",
        notes="Confirmed deliberate structuring below reporting threshold",
    )
    assert fb2["feedback_status"] == "CONFIRMED_SUSPICIOUS"

    updated2 = memory_audit_store.get_flag("flag-fb-1")
    assert updated2["feedback_status"] == "CONFIRMED_SUSPICIOUS"
    assert updated2["analyst_notes"] == "Confirmed deliberate structuring below reporting threshold"
    assert len(updated2["feedback_history"]) == 2
    assert updated2["feedback_history"][0]["analyst_id"] == "analyst_alice"
    assert updated2["feedback_history"][1]["analyst_id"] == "analyst_bob"

    # Test history helper method
    history = memory_audit_store.get_flag_feedback_history("flag-fb-1")
    assert len(history) == 2


def test_log_feedback_invalid_flag_raises(memory_audit_store: AuditStore):
    """Test that logging feedback for a nonexistent flag raises ValueError."""
    with pytest.raises(ValueError, match="Flag ID not found in audit store"):
        memory_audit_store.log_feedback(
            flag_id="nonexistent-flag-id",
            feedback_status="FALSE_POSITIVE",
            analyst_id="analyst_1",
        )


def test_get_audit_summary_metrics(memory_audit_store: AuditStore):
    """Test aggregate summary statistics calculation across queries, flags, and feedback."""
    # Log 2 queries
    memory_audit_store.log_query(query_id="q1", query_text="Check structuring")
    memory_audit_store.log_query(query_id="q2", query_text="Check fan out")

    # Log 3 flags
    flags = [
        Flag(
            flag_id="f1",
            rule_id="STRUCTURING_01",
            rule_name="Structuring",
            severity=RiskTier.HIGH,
            reason="Sub-$10k",
        ),
        Flag(
            flag_id="f2",
            rule_id="STRUCTURING_01",
            rule_name="Structuring",
            severity=RiskTier.CRITICAL,
            reason="Sub-$10k multiple",
        ),
        Flag(
            flag_id="f3",
            rule_id="ML_01",
            rule_name="ML Anomaly",
            severity=RiskTier.MEDIUM,
            reason="Outlier",
        ),
    ]
    memory_audit_store.log_flags(flags, query_id="q1")

    # Add feedback
    memory_audit_store.log_feedback(flag_id="f1", feedback_status="CONFIRMED_SUSPICIOUS", analyst_id="analyst_1")
    memory_audit_store.log_feedback(flag_id="f3", feedback_status="FALSE_POSITIVE", analyst_id="analyst_2")

    summary = memory_audit_store.get_audit_summary()
    assert summary["total_queries"] == 2
    assert summary["total_flags"] == 3
    assert summary["total_feedback_events"] == 2
    assert summary["flags_by_severity"]["HIGH"] == 1
    assert summary["flags_by_severity"]["CRITICAL"] == 1
    assert summary["flags_by_severity"]["MEDIUM"] == 1
    assert summary["flags_by_feedback_status"]["CONFIRMED_SUSPICIOUS"] == 1
    assert summary["flags_by_feedback_status"]["FALSE_POSITIVE"] == 1
    assert summary["flags_by_feedback_status"]["PENDING"] == 1
    assert summary["top_triggered_rules"][0]["rule_id"] == "STRUCTURING_01"
    assert summary["top_triggered_rules"][0]["count"] == 2


def test_get_audit_store_factory():
    """Test get_audit_store helper returns singleton and custom instance."""
    store1 = get_audit_store()
    store2 = get_audit_store()
    assert store1 is store2

    custom_store = get_audit_store(db_path=":memory:")
    assert custom_store is not store1
