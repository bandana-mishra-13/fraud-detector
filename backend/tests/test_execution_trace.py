import pandas as pd
import pandas.testing as pdt

from app.agent import executor
from app.agent.executor import execute_plan
from app.models.schemas import (
    ExecutionPlan,
    ExecutionTrace,
    PlanStep,
    SkippedTool,
    StepStatus,
    TraceStatus,
)
from app.tools.data_loader import load_transactions


def _step(number: int, tool_name: str) -> PlanStep:
    return PlanStep(
        step_number=number,
        tool_name=tool_name,
        description=f"Run {tool_name}",
    )


def _plan(
    steps: list[PlanStep],
    *,
    active_filters: dict | None = None,
    invoked_tools: list[str] | None = None,
    skipped_tools: list[SkippedTool] | None = None,
) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="trace-plan-id",
        query="Investigate AML activity",
        detected_intent="broad_analysis",
        active_filters=active_filters or {},
        invoked_tools=invoked_tools or [],
        skipped_tools=skipped_tools or [],
        steps=steps,
    )


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": pd.to_datetime(["2024-01-01 10:00", "2024-01-01 11:00"]),
            "From Account": ["A", "B"],
            "To Account": ["X", "A"],
            "Amount Paid": [100.0, 200.0],
            "Amount Received": [100.0, 200.0],
        }
    )


def test_success_trace_records_runtime_details_and_preserves_inputs(monkeypatch):
    transactions = _transactions()
    original_transactions = transactions.copy(deep=True)
    skipped_tools = [SkippedTool(tool_name="detectors_ml", reason="Not needed")]
    plan = _plan(
        [_step(1, "eda"), _step(2, "explain")],
        active_filters={"time_window": {"days": 30}},
        invoked_tools=["planner_metadata"],
        skipped_tools=skipped_tools,
    )
    original_plan = plan.model_copy(deep=True)

    monkeypatch.setattr(executor, "run_eda", lambda data, **kwargs: {"profile": {}})
    monkeypatch.setattr(executor, "explain_flags", lambda flags: [])

    result = execute_plan(plan, transactions)
    trace = result["trace"]

    assert isinstance(trace, ExecutionTrace)
    assert trace.status == TraceStatus.SUCCESS
    assert trace.query_id == "trace-plan-id"
    assert trace.detected_intent == "broad_analysis"
    assert trace.active_filters == {"time_window": {"days": 30}}
    assert trace.invoked_tools == ["eda", "explain"]
    assert trace.skipped_tools == skipped_tools
    assert set(trace.execution_timings_ms) == {"eda", "explain"}
    assert all(duration >= 0 for duration in trace.execution_timings_ms.values())
    assert trace.total_execution_time_ms >= 0
    assert trace.error_message is None
    assert result["plan"].invoked_tools == ["eda", "explain"]
    assert all(step.status == StepStatus.COMPLETED for step in result["plan"].steps)
    assert ExecutionTrace.model_validate(trace.model_dump()) == trace

    trace.active_filters["time_window"]["days"] = 7
    trace.skipped_tools[0].reason = "Changed trace copy"
    assert plan.model_dump() == original_plan.model_dump()
    assert plan.active_filters["time_window"]["days"] == 30
    assert plan.skipped_tools[0].reason == "Not needed"
    pdt.assert_frame_equal(transactions, original_transactions)


def test_first_step_failure_trace_records_attempt_and_leaves_later_step_pending(monkeypatch):
    monkeypatch.setattr(
        executor,
        "run_eda",
        lambda data, **kwargs: (_ for _ in ()).throw(RuntimeError("EDA unavailable")),
    )

    result = execute_plan(_plan([_step(1, "eda"), _step(2, "features")]), _transactions())
    trace = result["trace"]
    failed_step, pending_step = result["plan"].steps

    assert failed_step.status == StepStatus.FAILED
    assert pending_step.status == StepStatus.PENDING
    assert trace.status == TraceStatus.FAILED
    assert trace.invoked_tools == ["eda"]
    assert set(trace.execution_timings_ms) == {"eda"}
    assert trace.execution_timings_ms["eda"] >= 0
    assert "eda" in trace.error_message
    assert "RuntimeError: EDA unavailable" in trace.error_message
    assert trace.total_execution_time_ms >= 0


def test_partial_success_trace_records_only_attempted_tools(monkeypatch):
    monkeypatch.setattr(executor, "run_eda", lambda data, **kwargs: {"profile": {}})
    monkeypatch.setattr(
        executor,
        "engineer_features",
        lambda data, **kwargs: (_ for _ in ()).throw(ValueError("Invalid features")),
    )

    result = execute_plan(
        _plan([_step(1, "eda"), _step(2, "features"), _step(3, "explain")]),
        _transactions(),
    )
    trace = result["trace"]
    completed_step, failed_step, pending_step = result["plan"].steps

    assert completed_step.status == StepStatus.COMPLETED
    assert failed_step.status == StepStatus.FAILED
    assert pending_step.status == StepStatus.PENDING
    assert trace.status == TraceStatus.PARTIAL_SUCCESS
    assert trace.invoked_tools == ["eda", "features"]
    assert set(trace.execution_timings_ms) == {"eda", "features"}
    assert all(duration >= 0 for duration in trace.execution_timings_ms.values())
    assert "features" in trace.error_message


def test_empty_plan_creates_success_trace_without_tool_timings():
    result = execute_plan(_plan([]), _transactions())
    trace = result["trace"]

    assert trace.status == TraceStatus.SUCCESS
    assert trace.invoked_tools == []
    assert trace.execution_timings_ms == {}
    assert trace.total_execution_time_ms >= 0
    assert trace.error_message is None


def test_duplicate_tool_names_receive_distinct_timing_keys(monkeypatch):
    monkeypatch.setattr(executor, "run_eda", lambda data, **kwargs: {"profile": {}})

    result = execute_plan(_plan([_step(1, "eda"), _step(2, "eda")]), _transactions())
    trace = result["trace"]

    assert trace.invoked_tools == ["eda", "eda"]
    assert set(trace.execution_timings_ms) == {"eda", "eda#2"}
    assert all(duration >= 0 for duration in trace.execution_timings_ms.values())


def test_trace_integration_with_synthetic_transactions():
    transactions = load_transactions("synthetic_transactions.csv")

    result = execute_plan(_plan([_step(1, "detectors_rules")]), transactions)
    trace = result["trace"]

    assert trace.status == TraceStatus.SUCCESS
    assert trace.invoked_tools == ["detectors_rules"]
    assert set(trace.execution_timings_ms) == {"detectors_rules"}
