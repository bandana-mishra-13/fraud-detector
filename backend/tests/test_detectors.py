"""Unit tests for deterministic AML rule detectors (Task 2.3)."""

from datetime import datetime, timedelta
import pandas as pd
import pytest

from app.models.schemas import Flag, RiskTier
from app.tools.data_loader import load_transactions
from app.tools.detectors import (
    detect_fan_out,
    detect_high_velocity,
    detect_rapid_layering,
    detect_smurfing,
    detect_structuring,
    run_rule_detectors,
)


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    """Fixture providing normalized synthetic transactions DataFrame."""
    return load_transactions("synthetic_transactions.csv")


def test_detect_structuring_on_synthetic_data(synthetic_df: pd.DataFrame):
    """Verify structuring detector flags known structuring cluster in synthetic dataset."""
    flags = detect_structuring(synthetic_df)
    assert len(flags) > 0

    acc015_flags = [f for f in flags if f.entity_id == "ACC015"]
    assert len(acc015_flags) >= 1
    flag = acc015_flags[0]
    assert flag.rule_id == "RULE_STRUCTURING_01"
    assert flag.typology == "Structuring"
    assert flag.severity in (RiskTier.HIGH, RiskTier.CRITICAL)
    assert flag.evidence["tx_count"] == 3
    assert flag.evidence["total_amount"] == 29840.0


def test_detect_structuring_controlled_dataset():
    """Test structuring detection on custom time series."""
    base_time = pd.Timestamp("2023-01-01 10:00:00")
    df = pd.DataFrame({
        "Timestamp": [base_time, base_time + pd.Timedelta(hours=2), base_time + pd.Timedelta(hours=4)],
        "From Bank": ["001", "001", "001"],
        "From Account": ["ACCT_SMURF_1", "ACCT_SMURF_1", "ACCT_SMURF_1"],
        "To Bank": ["002", "002", "002"],
        "To Account": ["ACCT_DEST_1", "ACCT_DEST_2", "ACCT_DEST_3"],
        "Amount Received": [9500.0, 9200.0, 9800.0],
        "Receiving Currency": ["US Dollar", "US Dollar", "US Dollar"],
        "Amount Paid": [9500.0, 9200.0, 9800.0],
        "Payment Currency": ["US Dollar", "US Dollar", "US Dollar"],
        "Payment Format": ["Wire", "Wire", "Wire"],
        "Is Laundering": [1, 1, 1],
    })

    flags = detect_structuring(df, min_amount=7500.0, max_amount=9999.99, min_tx_count=2, window_hours=24.0)
    assert len(flags) >= 1
    flag = flags[0]
    assert flag.entity_id == "ACCT_SMURF_1"
    assert flag.evidence["tx_count"] == 3
    assert flag.evidence["total_amount"] == 28500.0


def test_detect_structuring_no_match():
    """Verify structuring detector returns empty list when amounts are outside threshold range."""
    df = pd.DataFrame({
        "Timestamp": [pd.Timestamp("2023-01-01 10:00:00"), pd.Timestamp("2023-01-01 12:00:00")],
        "From Bank": ["001", "001"],
        "From Account": ["ACC1", "ACC1"],
        "To Bank": ["002", "002"],
        "To Account": ["ACC2", "ACC2"],
        "Amount Received": [15000.0, 20000.0],
        "Receiving Currency": ["US Dollar", "US Dollar"],
        "Amount Paid": [15000.0, 20000.0],
        "Payment Currency": ["US Dollar", "US Dollar"],
        "Payment Format": ["Wire", "Wire"],
        "Is Laundering": [0, 0],
    })
    flags = detect_structuring(df)
    assert flags == []


def test_detect_smurfing_fan_in():
    """Test multi-source fan-in consolidation detection."""
    base_time = pd.Timestamp("2023-02-01 08:00:00")
    df = pd.DataFrame({
        "Timestamp": [
            base_time,
            base_time + pd.Timedelta(minutes=30),
            base_time + pd.Timedelta(hours=1),
            base_time + pd.Timedelta(hours=2),
        ],
        "From Bank": ["001", "002", "003", "004"],
        "From Account": ["SENDER_A", "SENDER_B", "SENDER_C", "SENDER_D"],
        "To Bank": ["010", "010", "010", "010"],
        "To Account": ["CONSOLIDATOR_1", "CONSOLIDATOR_1", "CONSOLIDATOR_1", "CONSOLIDATOR_1"],
        "Amount Received": [4500.0, 4800.0, 4200.0, 5100.0],
        "Receiving Currency": ["US Dollar"] * 4,
        "Amount Paid": [4500.0, 4800.0, 4200.0, 5100.0],
        "Payment Currency": ["US Dollar"] * 4,
        "Payment Format": ["Cash"] * 4,
        "Is Laundering": [1] * 4,
    })

    flags = detect_smurfing(df, min_senders=3, window_hours=24.0, min_total_amount=10000.0)
    assert len(flags) == 1
    flag = flags[0]
    assert flag.entity_id == "CONSOLIDATOR_1"
    assert flag.typology == "Smurfing"
    assert flag.rule_id == "RULE_SMURFING_FAN_IN_01"
    assert flag.evidence["distinct_senders"] == 4
    assert flag.evidence["total_amount"] == 18600.0


def test_detect_rapid_layering_pass_through():
    """Test rapid pass-through conduit detection."""
    t0 = pd.Timestamp("2023-03-01 09:00:00")
    t1 = pd.Timestamp("2023-03-01 09:35:00")

    df = pd.DataFrame({
        "Timestamp": [t0, t1],
        "From Bank": ["001", "002"],
        "From Account": ["ORIGIN_ACCT", "MULE_CONDUIT"],
        "To Bank": ["002", "003"],
        "To Account": ["MULE_CONDUIT", "FINAL_BENEFICIARY"],
        "Amount Received": [50000.0, 48500.0],
        "Receiving Currency": ["US Dollar", "US Dollar"],
        "Amount Paid": [50000.0, 48500.0],
        "Payment Currency": ["US Dollar", "US Dollar"],
        "Payment Format": ["Wire", "Wire"],
        "Is Laundering": [1, 1],
    })

    flags = detect_rapid_layering(df, window_hours=6.0, min_pass_through_ratio=0.80, min_amount=5000.0)
    assert len(flags) == 1
    flag = flags[0]
    assert flag.entity_id == "MULE_CONDUIT"
    assert flag.severity == RiskTier.CRITICAL
    assert flag.typology == "Pass-through"
    assert flag.rule_id == "RULE_RAPID_LAYERING_01"
    assert flag.evidence["in_amount"] == 50000.0
    assert flag.evidence["out_amount"] == 48500.0
    assert flag.evidence["pass_through_ratio"] == 0.97
    assert flag.evidence["time_delta_minutes"] == 35.0


def test_detect_fan_out():
    """Test single source dispersion to multiple recipients."""
    t0 = pd.Timestamp("2023-04-01 12:00:00")
    df = pd.DataFrame({
        "Timestamp": [
            t0,
            t0 + pd.Timedelta(minutes=15),
            t0 + pd.Timedelta(minutes=30),
            t0 + pd.Timedelta(minutes=45),
        ],
        "From Bank": ["001"] * 4,
        "From Account": ["DISPERSER_ACCT"] * 4,
        "To Bank": ["011", "012", "013", "014"],
        "To Account": ["RECIP_1", "RECIP_2", "RECIP_3", "RECIP_4"],
        "Amount Received": [6000.0, 6500.0, 7000.0, 8000.0],
        "Receiving Currency": ["US Dollar"] * 4,
        "Amount Paid": [6000.0, 6500.0, 7000.0, 8000.0],
        "Payment Currency": ["US Dollar"] * 4,
        "Payment Format": ["Wire"] * 4,
        "Is Laundering": [1] * 4,
    })

    flags = detect_fan_out(df, min_recipients=3, window_hours=24.0, min_total_amount=10000.0)
    assert len(flags) == 1
    flag = flags[0]
    assert flag.entity_id == "DISPERSER_ACCT"
    assert flag.typology == "Fan-out"
    assert flag.rule_id == "RULE_FAN_OUT_01"
    assert flag.evidence["distinct_recipients"] == 4
    assert flag.evidence["total_amount"] == 27500.0


def test_detect_high_velocity():
    """Test high velocity transaction burst detection."""
    t0 = pd.Timestamp("2023-05-01 14:00:00")
    timestamps = [t0 + pd.Timedelta(minutes=i * 5) for i in range(6)]

    df = pd.DataFrame({
        "Timestamp": timestamps,
        "From Bank": ["001"] * 6,
        "From Account": ["VELOCITY_USER"] * 6,
        "To Bank": ["002"] * 6,
        "To Account": [f"TARGET_{i}" for i in range(6)],
        "Amount Received": [1200.0] * 6,
        "Receiving Currency": ["US Dollar"] * 6,
        "Amount Paid": [1200.0] * 6,
        "Payment Currency": ["US Dollar"] * 6,
        "Payment Format": ["ACH"] * 6,
        "Is Laundering": [1] * 6,
    })

    flags = detect_high_velocity(df, min_tx_count=5, window_hours=2.0, min_total_amount=5000.0)
    assert len(flags) >= 1
    flag = flags[0]
    assert flag.entity_id == "VELOCITY_USER"
    assert flag.typology == "Velocity Spike"
    assert flag.evidence["tx_count"] == 6


def test_run_rule_detectors_master_runner(synthetic_df: pd.DataFrame):
    """Test master runner executing all detectors and filtering by entity / rule list."""
    all_flags = run_rule_detectors(synthetic_df)
    assert len(all_flags) > 0
    assert all(isinstance(f, Flag) for f in all_flags)

    # Filter by specific entity
    filtered_flags = run_rule_detectors(synthetic_df, entity_id="ACC015")
    assert len(filtered_flags) >= 1
    assert all(f.entity_id == "ACC015" for f in filtered_flags)

    # Filter by specific rule subset
    structuring_only = run_rule_detectors(synthetic_df, rules=["structuring"])
    assert len(structuring_only) >= 1
    assert all(f.typology == "Structuring" for f in structuring_only)


def test_empty_dataframe_handling():
    """Test detectors gracefully handle empty DataFrames."""
    empty_df = pd.DataFrame()
    assert detect_structuring(empty_df) == []
    assert detect_smurfing(empty_df) == []
    assert detect_rapid_layering(empty_df) == []
    assert detect_fan_out(empty_df) == []
    assert detect_high_velocity(empty_df) == []
    assert run_rule_detectors(empty_df) == []
