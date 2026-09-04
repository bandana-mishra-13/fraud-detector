"""Unit tests for Dynamic Execution Planner (Task 3.2)."""

import pytest

from app.agent.planner import (
    create_execution_plan,
    create_execution_plan_async,
)
from app.models.schemas import (
    ExecutionPlan,
    IntentType,
    ParsedIntent,
    StepStatus,
    TimeWindowSpec,
)


def test_plan_demo_query_1_broad_analysis():
    """Verify Demo Query 1 schedules full end-to-end investigative pipeline without skipped tools."""
    query = "Analyse this dataset for suspicious activity"
    plan = create_execution_plan(query)

    assert isinstance(plan, ExecutionPlan)
    assert plan.detected_intent == "broad_analysis"
    assert plan.query == query
    assert len(plan.steps) == 6

    expected_tools = ["eda", "features", "detectors_ml", "detectors_rules", "risk", "explain"]
    assert plan.invoked_tools == expected_tools
    assert [step.tool_name for step in plan.steps] == expected_tools
    assert plan.skipped_tools == []
    assert all(step.status == StepStatus.PENDING for step in plan.steps)
    assert "Full end-to-end AML investigative pipeline" in plan.reasoning


def test_plan_demo_query_2_pattern_detection_structuring():
    """Verify Demo Query 2 schedules targeted rule search and explicitly skips EDA and ML."""
    query = "Find structuring patterns in the last 30 days"
    plan = create_execution_plan(query)

    assert isinstance(plan, ExecutionPlan)
    assert plan.detected_intent == "pattern_detection"
    assert plan.invoked_tools == ["detectors_rules", "risk", "explain"]
    assert len(plan.steps) == 3

    # Check skipped tools with explicit reasoning
    skipped_tool_names = [st.tool_name for st in plan.skipped_tools]
    assert "eda" in skipped_tool_names
    assert "detectors_ml" in skipped_tool_names
    assert "features" in skipped_tool_names

    # Check parameters and active filters
    assert plan.active_filters.get("time_window_days") == 30
    assert plan.active_filters.get("pattern") == "structuring"
    rule_step = plan.steps[0]
    assert rule_step.tool_name == "detectors_rules"
    assert "structuring" in rule_step.parameters.get("rules", [])


def test_plan_demo_query_3_aggregation_thresholds():
    """Verify Demo Query 3 schedules aggregation and rule evaluation while skipping ML."""
    query = "Which customers made 10+ transactions under $10,000?"
    plan = create_execution_plan(query)

    assert isinstance(plan, ExecutionPlan)
    assert plan.detected_intent == "aggregation"
    assert plan.invoked_tools == ["features", "detectors_rules", "risk", "explain"]
    assert len(plan.steps) == 4

    skipped_tool_names = [st.tool_name for st in plan.skipped_tools]
    assert "detectors_ml" in skipped_tool_names
    assert "eda" in skipped_tool_names

    assert plan.active_filters.get("min_transaction_count") == 10
    assert plan.active_filters.get("max_transaction_amount") == 10000.0
    assert plan.steps[0].parameters.get("min_transaction_count") == 10


def test_plan_demo_query_4_single_entity_investigation():
    """Verify Demo Query 4 schedules targeted 360° entity drill-down for extracted customer ID."""
    query = "Is customer 4521 suspicious?"
    plan = create_execution_plan(query)

    assert isinstance(plan, ExecutionPlan)
    assert plan.detected_intent == "entity_investigation"
    assert plan.target_entities == ["4521"]
    assert plan.invoked_tools == ["eda", "features", "detectors_rules", "detectors_ml", "risk", "explain"]
    assert len(plan.steps) == 6

    # Verify every step is scoped to the target entity
    for step in plan.steps:
        assert step.parameters.get("entity_id") == "4521"


def test_plan_unsupported_query():
    """Verify unsupported query results in an empty plan with all tools skipped."""
    query = "What is the capital of France?"
    plan = create_execution_plan(query)

    assert isinstance(plan, ExecutionPlan)
    assert plan.detected_intent == "unsupported"
    assert plan.steps == []
    assert plan.invoked_tools == []
    assert len(plan.skipped_tools) == 1
    assert plan.skipped_tools[0].tool_name == "all_tools"
    assert "outside the scope" in plan.reasoning


def test_plan_from_direct_parsed_intent_object():
    """Verify create_execution_plan accepts a pre-parsed ParsedIntent object directly."""
    parsed = ParsedIntent(
        query="Smurfing detection past 7 days",
        intent=IntentType.PATTERN_DETECTION,
        filters={"min_amount": 5000},
        entities=[],
        pattern="smurfing",
        time_window=TimeWindowSpec(type="relative", value=7, unit="days", raw_text="past 7 days"),
    )

    plan = create_execution_plan(parsed)
    assert plan.detected_intent == "pattern_detection"
    assert plan.active_filters.get("pattern") == "smurfing"
    assert plan.active_filters.get("time_window_days") == 7
    assert plan.active_filters.get("min_amount") == 5000
    assert plan.invoked_tools == ["detectors_rules", "risk", "explain"]


@pytest.mark.asyncio
async def test_create_execution_plan_async():
    """Verify asynchronous execution plan generation."""
    query = "Investigate account ACC015"
    plan = await create_execution_plan_async(query)

    assert isinstance(plan, ExecutionPlan)
    assert plan.detected_intent == "entity_investigation"
    assert plan.target_entities == ["ACC015"]
    assert plan.steps[0].parameters.get("entity_id") == "ACC015"


def test_invalid_type_raises_type_error():
    """Verify passing an unsupported type raises TypeError."""
    with pytest.raises(TypeError, match="Expected ParsedIntent or str"):
        create_execution_plan(12345)  # type: ignore


def test_step_numbering_and_ordering():
    """Verify step numbers are strictly 1-indexed, contiguous, and ordered."""
    query = "Analyse this dataset for suspicious activity"
    plan = create_execution_plan(query)

    for i, step in enumerate(plan.steps, start=1):
        assert step.step_number == i
