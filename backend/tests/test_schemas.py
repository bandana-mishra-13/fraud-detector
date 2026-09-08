import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AMLPattern,
    Escalation,
    ExecutionPlan,
    Flag,
    PlanStep,
    RiskLevel,
    RiskResult,
)


def _flag(**overrides) -> Flag:
    base = dict(
        entity_type="account",
        entity_id="8000EBD30",
        pattern=AMLPattern.STRUCTURING,
        risk_level=RiskLevel.HIGH,
        score=0.9,
        reason="9 sub-threshold deposits within 48h",
        escalation=Escalation.REPORT,
    )
    base.update(overrides)
    return Flag(**base)


def test_flag_score_bounds():
    with pytest.raises(ValidationError):
        _flag(score=1.5)
    with pytest.raises(ValidationError):
        _flag(score=-0.1)


def test_plan_records_skipped_tools():
    plan = ExecutionPlan(
        query="Find structuring patterns in the last 30 days",
        intent="pattern_search",
        pattern=AMLPattern.STRUCTURING,
        steps=[
            PlanStep(tool="time_filter", action="invoked", reason="query names a window"),
            PlanStep(tool="eda", action="skipped", reason="targeted query — no broad exploration needed"),
        ],
    )
    actions = {s.tool: s.action for s in plan.steps}
    assert actions == {"time_filter": "invoked", "eda": "skipped"}


def test_risk_result_serialization_round_trip():
    result = RiskResult(
        run_id="abc123",
        plan=ExecutionPlan(query="q", intent="i"),
        flags=[_flag()],
        kpis={"scanned": 1000, "flags": 1},
    )
    restored = RiskResult.model_validate_json(result.model_dump_json())
    assert restored.flags[0].pattern is AMLPattern.STRUCTURING
    assert restored.kpis["scanned"] == 1000
