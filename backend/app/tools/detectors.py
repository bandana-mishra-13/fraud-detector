"""Anomaly Detection Tool — hybrid: deterministic typology rules + ML.

Rules encode named AML typologies with crisp, auditable thresholds — the same
input always produces the same signals (a compliance requirement). The
Isolation Forest supplies an unsupervised anomaly score that catches what the
rules don't name. The LLM is never involved in detection.

Thresholds are defaults, overridable per query — "context-appropriate
thresholds" (e.g. the agent can tighten them for a narrow, targeted search).
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .features import CTR_THRESHOLD, SUB_BAND_LOW

# Tuned against the 370 labeled laundering attempts in HI-Small_Patterns.txt
# (see validate.py): −15% flag volume vs the initial thresholds while holding
# 8-typology attempt coverage at 78% (−2pts), and calibrating smurfing to fire.
DEFAULT_THRESHOLDS: dict = {
    # structuring: repeated just-under-threshold payments in a short window
    "structuring_min_txns": 5,
    "structuring_window": "7D",
    # smurfing: many sub-threshold inbound payments from many senders
    "smurfing_min_txns": 5,
    "smurfing_min_senders": 3,
    # layering: fast in-and-out flow through an intermediary
    "layering_min_passthrough": 0.82,
    "layering_min_volume": 75_000.0,
    "layering_min_degree": 3,
    # rapid cash-out: inbound funds leaving as Cash within 24h
    "cashout_min_ratio": 0.55,
    "cashout_min_inflow": 30_000.0,
    # velocity: burst of activity in 24h
    "velocity_min_txns_24h": 30,
}


def _signal(account: str, pattern: str, strength: float, evidence: dict) -> dict:
    return {
        "account": str(account),
        "pattern": pattern,
        "strength": float(np.clip(strength, 0.0, 1.0)),
        "evidence": evidence,
    }


def detect_structuring(df: pd.DataFrame, th: dict) -> list[dict]:
    """Bursts of payments kept just under the $10k reporting threshold."""
    sub = df[
        (df["amount_paid"] >= SUB_BAND_LOW) & (df["amount_paid"] < CTR_THRESHOLD)
    ].sort_values(["from_account", "timestamp"])
    if sub.empty:
        return []

    rolled = (
        sub.groupby("from_account", observed=True)
        .rolling(th["structuring_window"], on="timestamp")["amount_paid"]
        .agg(["count", "sum"])
        .reset_index(level=0)
    )
    peak = rolled.groupby("from_account", observed=True)[["count", "sum"]].max()
    hits = peak[peak["count"] >= th["structuring_min_txns"]]

    signals = []
    for account, row in hits.iterrows():
        n = int(row["count"])
        signals.append(
            _signal(
                account,
                "structuring",
                strength=0.5 + min(n / (2 * th["structuring_min_txns"]), 0.5),
                evidence={
                    "sub_threshold_txns_in_window": n,
                    "window": th["structuring_window"],
                    "window_total": round(float(row["sum"]), 2),
                    "band": [SUB_BAND_LOW, CTR_THRESHOLD],
                },
            )
        )
    return signals


def detect_smurfing(feats: pd.DataFrame, th: dict) -> list[dict]:
    """Aggregation side of structuring: many sub-threshold inbound payments
    from many distinct senders (money mules fanning cash in)."""
    hits = feats[
        (feats["sub10k_in_count"] >= th["smurfing_min_txns"])
        & (feats["sub10k_in_senders"] >= th["smurfing_min_senders"])
    ]
    return [
        _signal(
            account,
            "smurfing",
            strength=0.5
            + min(row["sub10k_in_senders"] / (4 * th["smurfing_min_senders"]), 0.5),
            evidence={
                "sub_threshold_inbound_txns": int(row["sub10k_in_count"]),
                "distinct_senders": int(row["sub10k_in_senders"]),
            },
        )
        for account, row in hits.iterrows()
    ]


def detect_layering(feats: pd.DataFrame, th: dict) -> list[dict]:
    """Pass-through intermediaries: money in → money out within 24h, with
    fan-in and fan-out — the shape of a layering hop."""
    hits = feats[
        (feats["passthrough_24h_ratio"] >= th["layering_min_passthrough"])
        & (feats["in_total"] >= th["layering_min_volume"])
        & (feats["fan_in"] >= th["layering_min_degree"])
        & (feats["fan_out"] >= th["layering_min_degree"])
    ]
    return [
        _signal(
            account,
            "layering",
            strength=0.5 + 0.5 * float(row["passthrough_24h_ratio"] - th["layering_min_passthrough"])
            / max(1e-9, 1 - th["layering_min_passthrough"]),
            evidence={
                "passthrough_24h_ratio": round(float(row["passthrough_24h_ratio"]), 3),
                "inflow_total": round(float(row["in_total"]), 2),
                "fan_in": int(row["fan_in"]),
                "fan_out": int(row["fan_out"]),
            },
        )
        for account, row in hits.iterrows()
    ]


def detect_rapid_cash_out(feats: pd.DataFrame, th: dict) -> list[dict]:
    hits = feats[
        (feats["cash_out_24h_ratio"] >= th["cashout_min_ratio"])
        & (feats["in_total"] >= th["cashout_min_inflow"])
    ]
    return [
        _signal(
            account,
            "rapid_cash_out",
            strength=0.5 + 0.5 * float(row["cash_out_24h_ratio"]),
            evidence={
                "cash_out_within_24h_ratio": round(float(row["cash_out_24h_ratio"]), 3),
                "inflow_total": round(float(row["in_total"]), 2),
            },
        )
        for account, row in hits.iterrows()
    ]


def detect_velocity(feats: pd.DataFrame, th: dict) -> list[dict]:
    hits = feats[feats["max_txns_24h"] >= th["velocity_min_txns_24h"]]
    return [
        _signal(
            account,
            "velocity",
            strength=0.5 + min(row["max_txns_24h"] / (4 * th["velocity_min_txns_24h"]), 0.5),
            evidence={"max_txns_in_24h": int(row["max_txns_24h"])},
        )
        for account, row in hits.iterrows()
    ]


_RULES = {
    "structuring": ("df", detect_structuring),
    "smurfing": ("feats", detect_smurfing),
    "layering": ("feats", detect_layering),
    "rapid_cash_out": ("feats", detect_rapid_cash_out),
    "velocity": ("feats", detect_velocity),
}


def run_rules(
    df: pd.DataFrame,
    feats: pd.DataFrame,
    patterns: list[str] | None = None,
    thresholds: dict | None = None,
) -> list[dict]:
    """Run the selected typology rules (all when patterns is None)."""
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    selected = patterns or list(_RULES)
    signals: list[dict] = []
    for name in selected:
        if name not in _RULES:
            continue
        source, fn = _RULES[name]
        signals.extend(fn(df if source == "df" else feats, th))
    return signals


# feature columns the Isolation Forest learns from (labels excluded by design)
ML_FEATURES = [
    "out_count",
    "out_total",
    "out_mean",
    "out_max",
    "fan_out",
    "in_count",
    "in_total",
    "fan_in",
    "sub10k_out_count",
    "sub10k_in_count",
    "max_txns_24h",
    "max_sum_72h",
    "passthrough_24h_ratio",
    "cash_out_24h_ratio",
    "amount_z",
]


def run_isolation_forest(feats: pd.DataFrame, contamination: float | str = "auto") -> pd.Series:
    """Unsupervised anomaly score per account, scaled to [0, 1]."""
    X = np.log1p(feats[ML_FEATURES].clip(lower=0))
    model = IsolationForest(
        n_estimators=100, contamination=contamination, random_state=42, n_jobs=-1
    )
    model.fit(X)
    raw = -model.decision_function(X)  # higher = more anomalous
    lo, hi = float(raw.min()), float(raw.max())
    scaled = (raw - lo) / (hi - lo) if hi > lo else np.zeros_like(raw)
    return pd.Series(scaled, index=feats.index, name="anomaly_score")


# ── population-fit anomaly scores (consistency guarantee) ────────────────
# Fitting the forest on each query's filtered slice made an account's score
# depend on which query selected it — the normalization population changed
# per query, so the same behaviour flipped between risk levels across runs.
# Fix: fit ONCE on the full loaded population and cache; every query looks
# up the same per-account score. Same account → same score, always.

_POPULATION_CACHE: dict[tuple, pd.Series] = {}


def population_anomaly_scores(df: pd.DataFrame) -> pd.Series:
    """Anomaly score per account, fitted on the FULL loaded frame (cached)."""
    from .features import build_features

    key = (len(df), str(df["timestamp"].min()), str(df["timestamp"].max()))
    if key not in _POPULATION_CACHE:
        _POPULATION_CACHE[key] = run_isolation_forest(build_features(df))
    return _POPULATION_CACHE[key]
