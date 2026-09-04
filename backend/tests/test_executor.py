import pandas as pd
import pandas.testing as pdt
import pytest

from app.agent import executor
from app.agent.executor import execute_plan
from app.models.schemas import ExecutionPlan, Flag, PlanStep, RiskResult, RiskTier, StepStatus
from app.tools.data_loader import load_transactions


def _plan(steps: list[PlanStep], target_entities: list[str] | None = None) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-test",
        query="Investigate AML activity",
        detected_intent="broad_analysis",
        target_entities=target_entities or [],
        steps=steps,
    )


def _step(number: int, tool_name: str, parameters: dict | None = None) -> PlanStep:
    return PlanStep(
        step_number=number,
        tool_name=tool_name,
        description=f"Run {tool_name}",
        parameters=parameters or {},
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


def _flag() -> Flag:
    return Flag(
        rule_id="RULE_TEST",
        rule_name="Test Rule",
        severity=RiskTier.HIGH,
        entity_id="A",
        reason="Test finding",
    )


def _risk_result() -> RiskResult:
    return RiskResult(
        risk_score=0.4,
        risk_tier=RiskTier.MEDIUM,
        summary="Test risk result",
    )


def test_executes_all_tools_in_step_order_and_passes_context(monkeypatch):
    transactions = _transactions()
    original_transactions = transactions.copy(deep=True)
    plan = _plan(
        [
            _step(6, "explain"),
            _step(2, "features", {"window": "1h", "ignored": True}),
            _step(4, "detectors_rules", {"entity_id": "A", "rules": ["structuring"], "x": 1}),
            _step(1, "eda", {"top_n": 3, "entity_id": "ignored"}),
            _step(5, "risk"),
            _step(3, "detectors_ml", {"contamination": 0.2, "random_state": 9, "entity_id": "ignored"}),
        ]
    )
    original_plan = plan.model_copy(deep=True)
    calls: list[str] = []
    flag = _flag()
    featured = transactions.assign(feature_marker=1)
    ml_scored = featured.assign(anomaly_score=[0.1, 0.7], is_anomaly=[0, 1])

    def fake_eda(data, top_n=10):
        calls.append("eda")
        assert data.equals(transactions)
        assert top_n == 3
        return {"profile": {}}

    def fake_features(data, window="24h", sub_threshold=10_000.0):
        calls.append("features")
        assert data.equals(transactions)
        assert window == "1h"
        return featured

    def fake_ml(data, contamination=0.05, random_state=42):
        calls.append("detectors_ml")
        assert data is featured
        assert (contamination, random_state) == (0.2, 9)
        return ml_scored

    def fake_rules(data, entity_id=None, rules=None):
        calls.append("detectors_rules")
        assert data.equals(transactions)
        assert entity_id == "A"
        assert rules == ["structuring"]
        return [flag]

    def fake_risk(flags, ml_score=None, total_transactions=None, total_entities=None):
        calls.append("risk")
        assert flags == [flag]
        assert ml_score == 1.0
        assert total_transactions == 2
        return _risk_result()

    def fake_explain(flags):
        calls.append("explain")
        assert flags == [flag]
        return [{"rule_id": flag.rule_id}]

    monkeypatch.setattr(executor, "run_eda", fake_eda)
    monkeypatch.setattr(executor, "engineer_features", fake_features)
    monkeypatch.setattr(executor, "detect_anomalies", fake_ml)
    monkeypatch.setattr(executor, "run_rule_detectors", fake_rules)
    monkeypatch.setattr(executor, "fuse_overall_risk", fake_risk)
    monkeypatch.setattr(executor, "explain_flags", fake_explain)

    result = execute_plan(plan, transactions)
    executed_plan = result["plan"]
    context = result["context"]

    assert calls == ["eda", "features", "detectors_ml", "detectors_rules", "risk", "explain"]
    assert [step.step_number for step in executed_plan.steps] == [1, 2, 3, 4, 5, 6]
    assert all(step.status == StepStatus.COMPLETED for step in executed_plan.steps)
    assert all(step.result_summary for step in executed_plan.steps)
    assert context["featured_transactions"] is featured
    assert context["ml_scored_transactions"] is ml_scored
    assert context["rule_flags"] == [flag]
    assert context["risk_result"].risk_score == 0.4
    assert context["explanations"] == [{"rule_id": flag.rule_id}]
    pdt.assert_frame_equal(transactions, original_transactions)
    assert plan.model_dump() == original_plan.model_dump()


def test_ml_step_engineers_features_when_no_feature_step_is_scheduled(monkeypatch):
    transactions = _transactions()
    featured = transactions.assign(feature_marker=1)
    ml_scored = featured.assign(anomaly_score=[0.2, 0.4], is_anomaly=[0, 1])
    calls: list[str] = []

    def fake_features(data, **kwargs):
        calls.append("features")
        assert data.equals(transactions)
        return featured

    def fake_ml(data, **kwargs):
        calls.append("detectors_ml")
        assert data is featured
        return ml_scored

    monkeypatch.setattr(executor, "engineer_features", fake_features)
    monkeypatch.setattr(executor, "detect_anomalies", fake_ml)

    result = execute_plan(_plan([_step(1, "detectors_ml")]), transactions)

    assert calls == ["features", "detectors_ml"]
    assert result["plan"].steps[0].status == StepStatus.COMPLETED
    assert result["context"]["ml_scored_transactions"] is ml_scored


def test_risk_uses_entity_fusion_when_an_entity_is_available(monkeypatch):
    transactions = _transactions()
    flag = _flag()
    calls: list[str] = []

    def fake_entity_risk(entity_id, flags, ml_score=None, metadata=None):
        calls.append("entity_risk")
        assert entity_id == "A"
        assert flags == [flag]
        assert ml_score is None
        return _risk_result()

    monkeypatch.setattr(executor, "run_rule_detectors", lambda data, **kwargs: [flag])
    monkeypatch.setattr(executor, "fuse_entity_risk", fake_entity_risk)

    result = execute_plan(
        _plan([_step(1, "detectors_rules"), _step(2, "risk")], target_entities=["A"]),
        transactions,
    )

    assert calls == ["entity_risk"]
    assert result["context"]["risk_result"].entity_id is None


def test_normalized_ml_risk_score_bounds_extreme_and_negative_values():
    scored_transactions = pd.DataFrame(
        {
            "From Account": ["A", "B", "C"],
            "To Account": ["X", "Y", "Z"],
            "anomaly_score": [-500.0, -25.0, 750.0],
        }
    )

    overall_score = executor._normalized_ml_risk_score(scored_transactions, None)
    entity_score = executor._normalized_ml_risk_score(scored_transactions, "B")

    assert overall_score == 1.0
    assert entity_score == 0.38
    assert 0.0 <= overall_score <= 1.0
    assert 0.0 <= entity_score <= 1.0


def test_entity_ml_risk_uses_only_matching_transactions_after_normalization():
    scored_transactions = pd.DataFrame(
        {
            "From Account": ["A", "A", "B"],
            "To Account": ["X", "Y", "Z"],
            "anomaly_score": [-10.0, 0.0, 10.0],
        }
    )

    entity_score = executor._normalized_ml_risk_score(scored_transactions, "A")

    assert entity_score == 0.5


def test_entity_ml_risk_returns_none_when_no_scored_transaction_matches():
    scored_transactions = pd.DataFrame(
        {
            "From Account": ["A", "B"],
            "To Account": ["X", "Y"],
            "anomaly_score": [-2.0, 3.0],
        }
    )

    assert executor._normalized_ml_risk_score(scored_transactions, "missing") is None


def test_normalized_ml_risk_score_ignores_non_finite_and_handles_equal_scores():
    mixed_scores = pd.DataFrame(
        {
            "From Account": ["A", "B", "C", "D"],
            "To Account": ["W", "X", "Y", "Z"],
            "anomaly_score": [float("nan"), float("-inf"), 2.0, float("inf")],
        }
    )
    equal_scores = pd.DataFrame(
        {
            "From Account": ["A", "B"],
            "To Account": ["X", "Y"],
            "anomaly_score": [4.0, 4.0],
        }
    )

    assert executor._normalized_ml_risk_score(mixed_scores, None) == 0.0
    assert executor._normalized_ml_risk_score(mixed_scores, "A") is None
    assert executor._normalized_ml_risk_score(equal_scores, None) == 0.0
    assert executor._normalized_ml_risk_score(equal_scores, "A") == 0.0


def test_risk_fusion_receives_normalized_ml_score_from_extreme_values(monkeypatch):
    transactions = _transactions()
    ml_scored = transactions.assign(anomaly_score=[-1000.0, 2000.0], is_anomaly=[0, 1])

    monkeypatch.setattr(executor, "engineer_features", lambda data, **kwargs: data.copy())
    monkeypatch.setattr(executor, "detect_anomalies", lambda data, **kwargs: ml_scored)

    result = execute_plan(
        _plan([_step(1, "detectors_ml"), _step(2, "risk")]),
        transactions,
    )

    risk_result = result["context"]["risk_result"]
    assert risk_result.ml_score == 1.0
    assert 0.0 <= risk_result.ml_score <= 1.0


def test_unknown_tool_fails_step_and_stops_later_steps_pending():
    plan = _plan([_step(1, "unknown_tool"), _step(2, "eda")])

    result = execute_plan(plan, _transactions())

    failed_step, pending_step = result["plan"].steps
    assert failed_step.status == StepStatus.FAILED
    assert "Unsupported plan tool: unknown_tool" in failed_step.result_summary
    assert pending_step.status == StepStatus.PENDING
    assert result["context"]["error"]["tool_name"] == "unknown_tool"


def test_tool_failure_is_recorded_and_stops_execution(monkeypatch):
    monkeypatch.setattr(
        executor,
        "run_eda",
        lambda data, **kwargs: (_ for _ in ()).throw(RuntimeError("EDA unavailable")),
    )

    result = execute_plan(_plan([_step(1, "eda"), _step(2, "features")]), _transactions())

    failed_step, pending_step = result["plan"].steps
    assert failed_step.status == StepStatus.FAILED
    assert "RuntimeError: EDA unavailable" in failed_step.result_summary
    assert pending_step.status == StepStatus.PENDING


def test_empty_plan_returns_clean_execution_context():
    transactions = _transactions()

    result = execute_plan(_plan([]), transactions)

    assert result["plan"].steps == []
    assert result["context"].keys() == {"raw_transactions", "current_transactions"}
    assert result["context"]["raw_transactions"].equals(transactions)


def test_integration_with_loader_and_real_tools():
    transactions = load_transactions("synthetic_transactions.csv")
    plan = _plan(
        [
            _step(1, "features"),
            _step(2, "detectors_ml", {"contamination": 0.1}),
            _step(3, "detectors_rules"),
            _step(4, "risk"),
            _step(5, "explain"),
        ]
    )

    result = execute_plan(plan, transactions)

    assert all(step.status == StepStatus.COMPLETED for step in result["plan"].steps)
    assert "ml_scored_transactions" in result["context"]
    assert "rule_flags" in result["context"]
    assert "risk_result" in result["context"]
    assert "explanations" in result["context"]
