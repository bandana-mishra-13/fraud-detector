"""Agent tests. The planner tests encode the problem statement's own
behaviour table — each example query must produce the documented tool path.
No LLM is called here: specs are constructed directly (the LLM's only job is
producing these specs from text)."""

import json
from unittest.mock import patch

import pandas as pd

from app.agent.executor import execute
from app.agent.intent import IntentSpec, parse_intent
from app.agent.planner import TOOL_ORDER, build_plan
from app.models.schemas import AMLPattern, QueryFilters


def _decisions(planned) -> dict[str, bool]:
    return {s.tool: s.invoke for s in planned}


def test_planner_full_analysis_runs_everything_relevant():
    plan = build_plan(IntentSpec(intent="full_analysis"))
    d = _decisions(plan)
    assert d["eda"] and d["feature_engineering"] and d["rule_detection"]
    assert d["ml_anomaly"] and d["risk_classification"]
    assert not d["aggregation"] and not d["entity_lookup"]


def test_ps_row1_structuring_last_30_days_skips_eda():
    """'Find structuring patterns in the last 30 days' → time filter first;
    structuring-focused detection; skip full EDA."""
    spec = IntentSpec(
        intent="pattern_search",
        pattern=AMLPattern.STRUCTURING,
        filters=QueryFilters(last_n_days=30),
    )
    plan = build_plan(spec)
    d = _decisions(plan)
    assert not d["eda"], "EDA must be skipped for a targeted pattern query"
    assert d["apply_filters"] and d["feature_engineering"] and d["rule_detection"]
    rule = next(s for s in plan if s.tool == "rule_detection")
    assert rule.params["patterns"] == ["structuring"]


def test_ps_row2_aggregation_needs_no_ml():
    """'Which customers made 10+ transactions under $10,000?' → aggregation
    and threshold directly; ML anomaly detection is not required."""
    spec = IntentSpec(
        intent="aggregation",
        filters=QueryFilters(min_txn_count=10, max_amount=10_000),
    )
    d = _decisions(build_plan(spec))
    assert d["aggregation"]
    assert not d["ml_anomaly"], "ML must be skipped for aggregation queries"
    assert not d["rule_detection"] and not d["feature_engineering"] and not d["eda"]


def test_ps_row3_entity_lookup_is_scoped():
    """'Is customer ID 4521 suspicious?' → single-entity lookup; on-demand
    risk for that customer only."""
    spec = IntentSpec(
        intent="entity_lookup", filters=QueryFilters(customer="4521")
    )
    d = _decisions(build_plan(spec))
    assert d["entity_lookup"] and d["risk_classification"]
    assert not d["eda"] and not d["ml_anomaly"]


def test_every_plan_covers_the_full_tool_universe():
    """Skipped tools must appear in the plan WITH reasons — the decision is
    visible, not silent."""
    for intent in ("full_analysis", "pattern_search", "aggregation", "entity_lookup", "eda_only"):
        plan = build_plan(IntentSpec(intent=intent))
        assert [s.tool for s in plan] == TOOL_ORDER
        assert all(s.reason for s in plan)


# ── executor on synthetic data (no LLM involved) ─────────────────────────

def _frame() -> pd.DataFrame:
    rows = []
    for i in range(6):  # structuring plant
        rows.append(
            dict(
                timestamp=pd.Timestamp(f"2022-09-0{(i % 3) + 1} 1{i}:00"),
                from_bank="010", from_account="STRUCT1",
                to_bank="020", to_account=f"D{i}",
                amount_received=9_500.0, receiving_currency="US Dollar",
                amount_paid=9_500.0, payment_currency="US Dollar",
                payment_format="ACH", is_laundering=1,
            )
        )
    for i in range(12):  # aggregation fodder: SPENDER makes 12 txns under 10k
        rows.append(
            dict(
                timestamp=pd.Timestamp(f"2022-09-1{i % 8} 09:00"),
                from_bank="030", from_account="SPENDER",
                to_bank="040", to_account=f"SHOP{i % 4}",
                amount_received=200.0 + i, receiving_currency="US Dollar",
                amount_paid=200.0 + i, payment_currency="US Dollar",
                payment_format="Credit Card", is_laundering=0,
            )
        )
    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def _accounts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bank_name": ["B1", "B2"],
            "bank_id": ["010", "030"],
            "account": ["STRUCT1", "SPENDER"],
            "entity_id": ["E00A1", "E00B2"],
            "entity_name": ["Corporation #4521", "Sole Proprietorship #77"],
        }
    )


def test_executor_pattern_search_end_to_end(tmp_path):
    spec = IntentSpec(intent="pattern_search", pattern=AMLPattern.STRUCTURING)
    result = execute("find structuring", spec, build_plan(spec), df=_frame(), accounts=_accounts())
    assert result.run_id
    assert any(f.entity_id == "STRUCT1" for f in result.flags)
    actions = {s.tool: s.action for s in result.plan.steps}
    assert actions["eda"] == "skipped"
    invoked = [s for s in result.plan.steps if s.action == "invoked"]
    assert all(s.duration_ms is not None for s in invoked)


def test_executor_aggregation_end_to_end():
    spec = IntentSpec(
        intent="aggregation",
        filters=QueryFilters(min_txn_count=10, max_amount=10_000),
    )
    result = execute("who made 10+ under 10k", spec, build_plan(spec), df=_frame(), accounts=_accounts())
    table = result.charts["aggregation_table"]
    assert any(r["account"] == "SPENDER" and r["txn_count"] == 12 for r in table)
    assert result.kpis["aggregation_matches"] >= 1
    assert not result.flags  # aggregation answers a question; it doesn't flag


def test_executor_entity_lookup_scopes_to_customer():
    spec = IntentSpec(intent="entity_lookup", filters=QueryFilters(customer="4521"))
    result = execute("is customer 4521 suspicious?", spec, build_plan(spec), df=_frame(), accounts=_accounts())
    assert result.charts["entity_accounts"] == ["STRUCT1"]
    assert result.kpis["transactions_scanned"] == 6  # only the entity's txns
    assert any(f.entity_id == "STRUCT1" for f in result.flags)


def test_executor_determinism():
    spec = IntentSpec(intent="pattern_search", pattern=AMLPattern.STRUCTURING)
    r1 = execute("q", spec, build_plan(spec), df=_frame(), accounts=_accounts())
    r2 = execute("q", spec, build_plan(spec), df=_frame(), accounts=_accounts())
    assert [(f.entity_id, f.score) for f in r1.flags] == [
        (f.entity_id, f.score) for f in r2.flags
    ]


# ── intent parsing with a mocked LLM ─────────────────────────────────────

def test_parse_intent_validates_llm_json():
    fake = json.dumps(
        {
            "intent": "pattern_search",
            "pattern": "structuring",
            "filters": {"last_n_days": 30},
            "top_n": 50,
        }
    )
    with patch("app.agent.intent.chat", return_value=fake):
        spec = parse_intent("Find structuring patterns in the last 30 days")
    assert spec.intent == "pattern_search"
    assert spec.pattern is AMLPattern.STRUCTURING
    assert spec.filters.last_n_days == 30


def test_parse_intent_retries_once_on_bad_json():
    good = json.dumps({"intent": "eda_only", "pattern": None, "filters": {}})
    with patch("app.agent.intent.chat", side_effect=["not json{", good]) as mocked:
        spec = parse_intent("profile the data")
    assert mocked.call_count == 2
    assert spec.intent == "eda_only"


# ── manual tool overrides ────────────────────────────────────────────────

def test_override_forces_tool_on_and_pulls_dependencies():
    from app.agent.overrides import apply_overrides

    spec = IntentSpec(
        intent="aggregation",
        filters=QueryFilters(min_txn_count=10, max_amount=10_000),
    )
    plan = apply_overrides(build_plan(spec), {"eda": "on", "ml_anomaly": "on"})
    d = {s.tool: s.invoke for s in plan}
    assert d["eda"] and d["ml_anomaly"]
    assert d["feature_engineering"], "ml_anomaly must pull feature_engineering"
    forced = next(s for s in plan if s.tool == "eda")
    assert "reviewer" in forced.reason


def test_override_forces_tool_off_and_cascades():
    from app.agent.overrides import apply_overrides

    spec = IntentSpec(intent="pattern_search", pattern=AMLPattern.STRUCTURING)
    plan = apply_overrides(build_plan(spec), {"feature_engineering": "off"})
    d = {s.tool: s.invoke for s in plan}
    assert not d["feature_engineering"]
    assert not d["rule_detection"] and not d["ml_anomaly"]
    assert not d["risk_classification"], "off must cascade downstream"


def test_override_cannot_disable_locked_tools():
    from app.agent.overrides import apply_overrides

    spec = IntentSpec(intent="full_analysis")
    plan = apply_overrides(build_plan(spec), {"load_data": "off", "apply_filters": "off"})
    d = {s.tool: s.invoke for s in plan}
    assert d["load_data"] and d["apply_filters"]


def test_no_overrides_is_identity():
    from app.agent.overrides import apply_overrides

    spec = IntentSpec(intent="full_analysis")
    base = build_plan(spec)
    assert apply_overrides(base, None) == base
    assert apply_overrides(base, {}) == base


def test_ml_score_consistent_across_different_slices():
    """The bug this guards: slice-fit ML gave the same account different
    anomaly scores depending on which query selected it (population-relative
    normalization), flipping risk levels between runs. Population-fit scores
    must be identical whatever the filter."""
    df, accounts = _frame(), _accounts()
    spec_all = IntentSpec(intent="pattern_search", pattern=AMLPattern.STRUCTURING)
    spec_narrow = IntentSpec(
        intent="pattern_search",
        pattern=AMLPattern.STRUCTURING,
        filters=QueryFilters(min_amount=1_000),  # different slice population
    )
    r1 = execute("q1", spec_all, build_plan(spec_all), df=df, accounts=accounts)
    r2 = execute("q2", spec_narrow, build_plan(spec_narrow), df=df, accounts=accounts)
    f1 = next(f for f in r1.flags if f.entity_id == "STRUCT1")
    f2 = next(f for f in r2.flags if f.entity_id == "STRUCT1")
    assert f1.evidence["ml_anomaly_score"] == f2.evidence["ml_anomaly_score"]
    assert f1.risk_level == f2.risk_level
    assert f1.score == f2.score
