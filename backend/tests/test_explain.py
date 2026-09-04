import pandas as pd
import pytest

from app.models.schemas import Flag, RiskTier
from app.tools.data_loader import load_transactions
from app.tools.detectors import (
    detect_fan_out,
    detect_rapid_layering,
    detect_smurfing,
    detect_structuring,
    run_rule_detectors,
)
from app.tools.explain import explain_flag, explain_flags


# ============================================================================
# 1. Structuring Typology Unit Tests
# ============================================================================

def test_explain_structuring_flag():
    flag = Flag(
        rule_id="RULE_STRUCTURING_01",
        rule_name="Outbound Structuring below Reporting Threshold",
        severity=RiskTier.HIGH,
        entity_id="ACC015",
        transaction_ids=["TX101", "TX102", "TX103"],
        typology="Structuring",
        reason="Account ACC015 conducted 3 transactions below $10k",
        evidence={
            "role": "Outbound",
            "tx_count": 3,
            "total_amount": 29840.00,
            "min_tx_amount": 9900.00,
            "max_tx_amount": 9990.00,
            "time_span_hours": 0.5,
        },
    )
    res = explain_flag(flag)
    assert res["flag_id"] == flag.flag_id
    assert res["typology"] == "Structuring"
    assert res["severity"] == "HIGH"
    assert res["entity_id"] == "ACC015"

    explanation = res["explanation"]
    assert "ACC015" in explanation
    assert "3 outbound transactions" in explanation
    assert "ranging from $9,900.00 to $9,990.00" in explanation
    assert "totaling $29,840.00" in explanation
    assert "Evidence transactions: TX101, TX102, TX103." in explanation


# ============================================================================
# 2. Smurfing Typology Unit Tests
# ============================================================================

def test_explain_smurfing_flag():
    flag = Flag(
        rule_id="RULE_SMURFING_FAN_IN_01",
        rule_name="Multi-Source Fan-In Consolidation (Smurfing)",
        severity=RiskTier.CRITICAL,
        entity_id="ACC020",
        transaction_ids=["TX201", "TX202", "TX203", "TX204"],
        typology="Smurfing",
        reason="Account ACC020 consolidated $50,000 from 4 accounts",
        evidence={
            "distinct_senders": 4,
            "total_amount": 50000.00,
            "time_span_hours": 12.0,
        },
    )
    res = explain_flag(flag)
    explanation = res["explanation"]
    assert "ACC020" in explanation
    assert "consolidated $50,000.00" in explanation
    assert "from 4 distinct originating accounts" in explanation
    assert "Evidence transactions: TX201, TX202, TX203, TX204." in explanation


# ============================================================================
# 3. Rapid Layering Typology Unit Tests
# ============================================================================

def test_explain_rapid_layering_flag():
    flag = Flag(
        rule_id="RULE_RAPID_LAYERING_01",
        rule_name="Rapid Layering / Pass-Through Conduit",
        severity=RiskTier.CRITICAL,
        entity_id="ACC030",
        transaction_ids=["TX301", "TX302"],
        typology="Pass-through",
        reason="Pass-through conduit detected",
        evidence={
            "in_amount": 25000.00,
            "out_amount": 24800.00,
            "pass_through_ratio": 0.992,
            "time_delta_minutes": 15.5,
        },
    )
    res = explain_flag(flag)
    explanation = res["explanation"]
    assert "ACC030" in explanation
    assert "received $25,000.00" in explanation
    assert "transferred out $24,800.00" in explanation
    assert "(99.2% turnover)" in explanation
    assert "within 15.5 minutes" in explanation
    assert "Evidence transactions: TX301, TX302." in explanation


# ============================================================================
# 4. Fan-Out Typology Unit Tests
# ============================================================================

def test_explain_fan_out_flag():
    flag = Flag(
        rule_id="RULE_FAN_OUT_01",
        rule_name="High Fan-Out Fund Dispersion",
        severity=RiskTier.HIGH,
        entity_id="ACC040",
        transaction_ids=["TX401", "TX402", "TX403"],
        typology="Fan-out",
        reason="Dispersed $30,000 to 3 recipients",
        evidence={
            "distinct_recipients": 3,
            "total_amount": 30000.00,
            "time_span_hours": 5.0,
        },
    )
    res = explain_flag(flag)
    explanation = res["explanation"]
    assert "ACC040" in explanation
    assert "dispersed $30,000.00" in explanation
    assert "across 3 distinct beneficiary accounts" in explanation
    assert "Evidence transactions: TX401, TX402, TX403." in explanation


# ============================================================================
# 5. Unknown Typology Fallback & Edge Cases
# ============================================================================

def test_explain_unknown_typology_fallback():
    flag = Flag(
        rule_id="RULE_CUSTOM_99",
        rule_name="Novel Cyber Laundering Rule",
        severity=RiskTier.MEDIUM,
        entity_id="ACC099",
        transaction_ids=["TX999"],
        typology="Novel_Cyber_Laundering",
        reason="Unusual API transaction pattern detected",
        evidence={},
    )
    res = explain_flag(flag)
    explanation = res["explanation"]
    assert "Novel Cyber Laundering Rule" in explanation
    assert "ACC099" in explanation
    assert "Unusual API transaction pattern detected" in explanation
    assert "Evidence transaction: TX999." in explanation


def test_explain_flag_missing_transaction_ids():
    flag = Flag(
        rule_id="RULE_GENERIC_01",
        rule_name="Generic Rule",
        severity=RiskTier.LOW,
        entity_id="ACC001",
        transaction_ids=[],
        typology="Generic",
        reason="Basic anomaly",
    )
    res = explain_flag(flag)
    assert res["transaction_ids"] == []
    assert "Transaction-level evidence was not supplied." in res["explanation"]
    assert "None" not in res["explanation"]


def test_explain_flags_batch():
    f1 = Flag(rule_id="R1", rule_name="Rule 1", severity=RiskTier.LOW, reason="R1", typology="Structuring")
    f2 = Flag(rule_id="R2", rule_name="Rule 2", severity=RiskTier.HIGH, reason="R2", typology="Fan-out")
    batch = explain_flags([f1, f2])
    assert len(batch) == 2
    assert batch[0]["rule_id"] == "R1"
    assert batch[1]["rule_id"] == "R2"


# ============================================================================
# 6. Integration Test with Real Dev B Detectors
# ============================================================================

def test_explain_integration_with_real_detectors():
    """Verify integration: Dev C loader -> Dev B rule detectors -> Dev A explain_flags."""
    df = load_transactions("synthetic_transactions.csv")
    assert not df.empty

    flags = run_rule_detectors(df)
    assert len(flags) > 0

    explanations = explain_flags(flags)
    assert len(explanations) == len(flags)

    for flag, exp in zip(flags, explanations):
        assert exp["flag_id"] == flag.flag_id
        assert exp["rule_id"] == flag.rule_id
        assert exp["severity"] == flag.severity.value
        assert exp["transaction_ids"] == flag.transaction_ids

        # Verify cited transaction IDs in text match the flag's transaction IDs
        for tx_id in flag.transaction_ids[:5]:
            assert tx_id in exp["explanation"]
