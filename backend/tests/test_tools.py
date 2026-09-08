"""Tool-layer tests on a synthetic frame with planted typologies."""

import pandas as pd
import pytest

from app.models.schemas import Escalation, QueryFilters, RiskLevel
from app.tools.detectors import run_isolation_forest, run_rules
from app.tools.eda import run_eda
from app.tools.features import build_features
from app.tools.filters import apply_filters
from app.tools.risk import classify


def _txn(ts, src, dst, amount, fmt="ACH", laundering=0):
    return {
        "timestamp": pd.Timestamp(ts),
        "from_bank": "010",
        "from_account": src,
        "to_bank": "020",
        "to_account": dst,
        "amount_received": amount,
        "receiving_currency": "US Dollar",
        "amount_paid": amount,
        "payment_currency": "US Dollar",
        "payment_format": fmt,
        "is_laundering": laundering,
    }


@pytest.fixture()
def frame() -> pd.DataFrame:
    rows = []
    # STRUCT1: 6 just-under-threshold payments in 3 days → structuring
    for i in range(6):
        rows.append(
            _txn(f"2022-09-0{(i % 3) + 1} 1{i}:00", "STRUCT1", f"DST{i}", 9_400 + i * 50, laundering=1)
        )
    # SMURF_T: 9 sub-threshold inbound from 6 distinct senders → smurfing
    for i in range(9):
        rows.append(
            _txn(f"2022-09-05 0{i}:30", f"MULE{i % 6}", "SMURF_T", 9_100 + i * 20)
        )
    # LAYER1: 90k in from 3 senders, 87k out to 3 receivers within hours
    # (volumes sit above the tuned layering_min_volume of 75k)
    for i in range(3):
        rows.append(_txn(f"2022-09-07 0{i}:00", f"SRC{i}", "LAYER1", 30_000))
        rows.append(_txn(f"2022-09-07 0{i + 3}:00", "LAYER1", f"SINK{i}", 29_000))
    # CASHOUT1: 30k in, 24k out as Cash the same day
    rows.append(_txn("2022-09-09 08:00", "PAYER", "CASHOUT1", 30_000))
    rows.append(_txn("2022-09-09 12:00", "CASHOUT1", "ATM", 24_000, fmt="Cash"))
    # clean background accounts
    for i in range(10):
        rows.append(_txn(f"2022-09-1{i % 8} 10:00", f"CLEAN{i}", f"SHOP{i % 3}", 120 + i))
    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return df


def test_filters_anchor_relative_dates_to_dataset_max(frame):
    filtered, applied = apply_filters(frame, QueryFilters(last_n_days=2))
    assert applied["rows_after"] > 0
    assert filtered["timestamp"].min() >= frame["timestamp"].max() - pd.Timedelta(days=2)


def test_structuring_detector_finds_plant_and_ignores_clean(frame):
    feats = build_features(frame)
    signals = run_rules(frame, feats, patterns=["structuring"])
    accounts = {s["account"] for s in signals}
    assert "STRUCT1" in accounts
    assert not any(a.startswith("CLEAN") for a in accounts)


def test_pattern_selection_runs_only_requested_rules(frame):
    feats = build_features(frame)
    signals = run_rules(frame, feats, patterns=["smurfing"])
    assert signals, "smurfing plant not detected"
    assert {s["pattern"] for s in signals} == {"smurfing"}
    assert any(s["account"] == "SMURF_T" for s in signals)


def test_layering_and_cashout_detected(frame):
    feats = build_features(frame)
    patterns = {s["pattern"]: s["account"] for s in run_rules(frame, feats)}
    assert patterns.get("layering") == "LAYER1"
    assert patterns.get("rapid_cash_out") == "CASHOUT1"


def test_isolation_forest_scores_bounded(frame):
    feats = build_features(frame)
    scores = run_isolation_forest(feats)
    assert scores.between(0.0, 1.0).all()
    assert len(scores) == len(feats)


def test_classify_produces_explained_escalated_flags(frame):
    feats = build_features(frame)
    signals = run_rules(frame, feats)
    flags = classify(signals, run_isolation_forest(feats))
    assert flags, "no flags produced"
    top = flags[0]
    assert top.score >= flags[-1].score  # sorted strongest-first
    struct = next(f for f in flags if f.pattern.value == "structuring")
    assert struct.entity_id == "STRUCT1"
    assert "reporting threshold" in struct.reason
    assert struct.escalation in {Escalation.REPORT, Escalation.REVIEW}
    assert struct.risk_level in {RiskLevel.HIGH, RiskLevel.MEDIUM}


def test_classification_is_deterministic(frame):
    feats = build_features(frame)
    a = classify(run_rules(frame, feats), run_isolation_forest(feats))
    b = classify(run_rules(frame, feats), run_isolation_forest(feats))
    assert [(f.entity_id, f.score) for f in a] == [(f.entity_id, f.score) for f in b]


def test_eda_returns_chart_ready_summary(frame):
    summary = run_eda(frame)
    assert summary["rows"] == len(frame)
    assert summary["charts"]["txns_per_day"]
    assert summary["charts"]["payment_formats"]
    assert 0 <= summary["labeled_laundering_rate"] <= 1
