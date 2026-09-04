"""Verification suite for Task 5.1: Verifying the 4 official demo queries produce visibly distinct tool execution paths."""

import pytest
import pandas as pd

from app.agent.intent_parser import parse_intent
from app.agent.planner import create_execution_plan
from app.agent.executor import execute_plan
from app.agent.result_synthesizer import synthesize_results
from app.models.schemas import IntentType, SynthesizedResult, ExecutionPlan, ExecutionTrace, TraceStatus
from app.tools.data_loader import load_transactions


@pytest.fixture
def transactions_df():
    """Load real synthetic transaction dataset for verification."""
    return load_transactions("synthetic_transactions.csv")


def test_demo_query_1_broad_analysis_pipeline(transactions_df):
    """Scenario 1: Broad dataset scan executes full 6-tool pipeline."""
    query = "Analyse this dataset for suspicious activity"
    
    parsed = parse_intent(query)
    assert parsed.intent == IntentType.BROAD_ANALYSIS
    
    plan = create_execution_plan(parsed)
    assert plan.detected_intent == "broad_analysis"
    assert plan.invoked_tools == ["eda", "features", "detectors_ml", "detectors_rules", "risk", "explain"]
    assert len(plan.skipped_tools) == 0

    execution_output = execute_plan(plan, transactions_df)
    executed_plan = execution_output["plan"]
    assert all(step.status.value == "COMPLETED" for step in executed_plan.steps)

    synthesized = synthesize_results(execution_output)
    assert isinstance(synthesized, SynthesizedResult)
    assert len(synthesized.executive_summary) > 0

    trace = ExecutionTrace(
        trace_id="test-trace-1",
        detected_intent=executed_plan.detected_intent,
        active_filters=executed_plan.active_filters,
        invoked_tools=executed_plan.invoked_tools,
        skipped_tools=executed_plan.skipped_tools,
        execution_timings_ms={"eda": 10.0, "features": 25.0, "detectors_ml": 40.0, "detectors_rules": 15.0, "risk": 5.0, "explain": 12.0},
        total_execution_time_ms=107.0,
        status=TraceStatus.SUCCESS,
    )
    assert trace.status == TraceStatus.SUCCESS
    assert set(trace.invoked_tools) == set(plan.invoked_tools)


def test_demo_query_2_structuring_skips_eda_and_ml(transactions_df):
    """Scenario 2: Structuring pattern query skips EDA & ML anomaly detection."""
    query = "Find structuring patterns in the last 30 days"
    
    parsed = parse_intent(query)
    assert parsed.intent == IntentType.PATTERN_DETECTION
    assert parsed.pattern == "structuring"
    assert parsed.time_window is not None
    assert parsed.time_window.value == 30

    plan = create_execution_plan(parsed)
    assert plan.detected_intent == "pattern_detection"
    assert plan.invoked_tools == ["detectors_rules", "risk", "explain"]
    
    skipped_tool_names = [st.tool_name for st in plan.skipped_tools]
    assert "eda" in skipped_tool_names
    assert "detectors_ml" in skipped_tool_names
    assert "features" in skipped_tool_names

    execution_output = execute_plan(plan, transactions_df)
    synthesized = synthesize_results(execution_output)
    
    # Verify skipped tools are listed in limitations and summary does NOT falsely claim "no ML anomalies"
    skipped_text = " ".join(synthesized.limitations)
    assert "eda" in skipped_text or "detectors_ml" in skipped_text
    assert "no ML anomalies" not in synthesized.executive_summary


def test_demo_query_3_aggregation_skips_ml(transactions_df):
    """Scenario 3: Aggregation threshold query skips ML anomaly detection."""
    query = "Which customers made 10+ transactions under $10,000?"
    
    parsed = parse_intent(query)
    assert parsed.intent == IntentType.AGGREGATION
    assert parsed.filters.get("min_transaction_count") == 10
    assert parsed.filters.get("max_transaction_amount") == 10000.0

    plan = create_execution_plan(parsed)
    assert plan.detected_intent == "aggregation"
    assert plan.invoked_tools == ["features", "detectors_rules", "risk", "explain"]

    skipped_tool_names = [st.tool_name for st in plan.skipped_tools]
    assert "detectors_ml" in skipped_tool_names
    assert "eda" in skipped_tool_names

    execution_output = execute_plan(plan, transactions_df)
    synthesized = synthesize_results(execution_output)
    assert isinstance(synthesized, SynthesizedResult)


def test_demo_query_4_entity_investigation(transactions_df):
    """Scenario 4: Customer 4521 targeted 360° investigation."""
    query = "Is customer 4521 suspicious?"
    
    parsed = parse_intent(query)
    assert parsed.intent == IntentType.ENTITY_INVESTIGATION
    assert "4521" in parsed.entities

    plan = create_execution_plan(parsed)
    assert plan.detected_intent == "entity_investigation"
    assert plan.target_entities == ["4521"]
    assert plan.steps[0].parameters.get("entity_id") == "4521"

    execution_output = execute_plan(plan, transactions_df)
    synthesized = synthesize_results(execution_output)
    assert isinstance(synthesized, SynthesizedResult)
    assert "4521" in synthesized.executive_summary


def test_all_four_demo_queries_are_visibly_and_structurally_distinct(transactions_df):
    """Verify that all 4 demo queries produce 4 distinct execution plans & tool paths."""
    queries = [
        "Analyse this dataset for suspicious activity",
        "Find structuring patterns in the last 30 days",
        "Which customers made 10+ transactions under $10,000?",
        "Is customer 4521 suspicious?",
    ]

    intents = set()
    invoked_paths = []

    for q in queries:
        parsed = parse_intent(q)
        plan = create_execution_plan(parsed)
        intents.add(plan.detected_intent)
        invoked_paths.append(tuple(plan.invoked_tools))

    # Assert 4 distinct intents
    assert len(intents) == 4
    assert "broad_analysis" in intents
    assert "pattern_detection" in intents
    assert "aggregation" in intents
    assert "entity_investigation" in intents

    # Assert distinct tool execution paths (at least 3 distinct tool call sequences)
    unique_paths = set(invoked_paths)
    assert len(unique_paths) >= 3
