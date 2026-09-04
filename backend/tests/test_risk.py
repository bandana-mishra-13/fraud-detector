"""Unit tests for the Hybrid Risk Fusion Engine (Task 2.5)."""

import pytest

from app.models.schemas import Flag, RiskResult, RiskTier
from app.tools.risk import (
    calculate_rule_score,
    determine_risk_tier,
    fuse_entity_risk,
    fuse_overall_risk,
    fuse_scores,
    fuse_transaction_risk,
    generate_risk_summary,
)


@pytest.fixture
def sample_flags() -> list[Flag]:
    """Fixture providing flags with diverse severities and typologies."""
    return [
        Flag(
            flag_id="flag-struct-1",
            rule_id="RULE_STRUCTURING_01",
            rule_name="Structuring Flag",
            severity=RiskTier.HIGH,
            entity_id="ACC_TARGET",
            transaction_ids=["TX_1", "TX_2"],
            typology="Structuring",
            reason="3 transactions below $10k in 24h",
            evidence={"tx_count": 3, "total_amount": 28500.0},
        ),
        Flag(
            flag_id="flag-layer-1",
            rule_id="RULE_RAPID_LAYERING_01",
            rule_name="Layering Flag",
            severity=RiskTier.CRITICAL,
            entity_id="ACC_TARGET",
            transaction_ids=["TX_1", "TX_3"],
            typology="Pass-through",
            reason="Funds moved out within 15 minutes",
            evidence={"time_delta_minutes": 15.0},
        ),
    ]


def test_calculate_rule_score_empty():
    """Verify rule score is 0.0 for empty flag list."""
    assert calculate_rule_score([]) == 0.0


def test_calculate_rule_score_severities():
    """Test score computation across different severity weights."""
    low_flag = Flag(
        rule_id="R1", rule_name="Low", severity=RiskTier.LOW, reason="Low finding"
    )
    med_flag = Flag(
        rule_id="R2", rule_name="Med", severity=RiskTier.MEDIUM, reason="Med finding"
    )
    high_flag = Flag(
        rule_id="R3", rule_name="High", severity=RiskTier.HIGH, reason="High finding"
    )
    crit_flag = Flag(
        rule_id="R4", rule_name="Crit", severity=RiskTier.CRITICAL, reason="Crit finding"
    )

    # Single flag score checks
    assert calculate_rule_score([low_flag]) == 0.05
    assert calculate_rule_score([med_flag]) == 0.15
    assert calculate_rule_score([high_flag]) == 0.25
    assert calculate_rule_score([crit_flag]) == 0.40

    # Multi-flag combination with saturation curve
    combined_score = calculate_rule_score([crit_flag, high_flag])
    # 1 - (1 - 0.40) * (1 - 0.25) = 1 - 0.60 * 0.75 = 1 - 0.45 = 0.55
    assert combined_score == 0.55


def test_determine_risk_tier_thresholds_and_overrides(sample_flags: list[Flag]):
    """Verify risk tier categorization and critical flag override."""
    # Critical override even if numerical score is moderate
    tier_override = determine_risk_tier(0.40, sample_flags)
    assert tier_override == RiskTier.CRITICAL

    # Numerical score tiers without critical flag
    non_crit_flags = [sample_flags[0]]  # only HIGH flag
    assert determine_risk_tier(0.80, non_crit_flags) == RiskTier.CRITICAL
    assert determine_risk_tier(0.60, non_crit_flags) == RiskTier.HIGH
    assert determine_risk_tier(0.35, non_crit_flags) == RiskTier.MEDIUM
    assert determine_risk_tier(0.10, non_crit_flags) == RiskTier.LOW


def test_fuse_scores_with_and_without_ml():
    """Verify score combination logic with and without ML anomaly inputs."""
    # Without ML (e.g. ML tool skipped)
    assert fuse_scores(rule_score=0.55, ml_score=None) == 0.55

    # With ML anomaly score
    # 0.65 * 0.50 + 0.35 * 0.80 = 0.325 + 0.280 = 0.605
    fused = fuse_scores(rule_score=0.50, ml_score=0.80)
    assert fused == 0.605

    # Bounds enforcement
    assert fuse_scores(rule_score=1.5, ml_score=1.2) == 1.0
    assert fuse_scores(rule_score=-0.5, ml_score=-0.2) == 0.0


def test_fuse_entity_risk(sample_flags: list[Flag]):
    """Test generating comprehensive RiskResult for an account."""
    result = fuse_entity_risk(
        entity_id="ACC_TARGET",
        flags=sample_flags,
        ml_score=0.75,
        metadata={"total_volume": 55000.0},
    )

    assert isinstance(result, RiskResult)
    assert result.entity_id == "ACC_TARGET"
    assert result.risk_tier == RiskTier.CRITICAL
    assert result.rule_score > 0.5
    assert result.ml_score == 0.75
    assert len(result.flags) == 2
    assert "Structuring" in result.evidence_summary["typologies_detected"]
    assert "Pass-through" in result.evidence_summary["typologies_detected"]
    assert result.evidence_summary["total_volume"] == 55000.0
    assert "CRITICAL risk" in result.summary


def test_fuse_transaction_risk(sample_flags: list[Flag]):
    """Test generating transaction-level risk assessment."""
    result = fuse_transaction_risk(
        transaction_id="TX_1",
        flags=sample_flags,
        ml_score=0.85,
        entity_id="ACC_TARGET",
    )

    assert isinstance(result, RiskResult)
    assert result.transaction_id == "TX_1"
    assert result.entity_id == "ACC_TARGET"
    assert len(result.flags) == 2
    assert result.risk_tier == RiskTier.CRITICAL


def test_fuse_overall_risk(sample_flags: list[Flag]):
    """Test dataset-level aggregated risk calculation."""
    result = fuse_overall_risk(
        flags=sample_flags,
        ml_score=0.60,
        total_transactions=150,
        total_entities=45,
    )

    assert isinstance(result, RiskResult)
    assert result.entity_id is None
    assert result.transaction_id is None
    assert result.evidence_summary["total_transactions"] == 150
    assert result.evidence_summary["total_entities"] == 45
    assert result.evidence_summary["total_flags"] == 2


def test_generate_risk_summary_text():
    """Verify natural language risk summary formatting."""
    flag = Flag(
        rule_id="R1",
        rule_name="Fan-Out",
        severity=RiskTier.HIGH,
        typology="Fan-out",
        reason="Dispersed funds to 8 accounts in 1h",
    )
    summary = generate_risk_summary(
        subject="Account ACC_TEST",
        risk_tier=RiskTier.HIGH,
        risk_score=0.65,
        flags=[flag],
        ml_score=0.72,
    )

    assert "Account ACC_TEST" in summary
    assert "HIGH risk (score: 0.65)" in summary
    assert "Fan-out" in summary
    assert "Dispersed funds to 8 accounts in 1h" in summary
    assert "ML anomaly score evaluated at 0.72" in summary
