"""Feature Engineering Tool — account-level AML behaviour features.

Built on demand for the slice the query selected. Produces exactly the
feature families the problem statement names: transaction frequency, rolling
sums, amount deviation, velocity, and rapid cash-out — plus fan-in/fan-out
degrees and sub-threshold (structuring) counts.

The ground-truth `is_laundering` label is deliberately NEVER used here:
detection must stand on behaviour alone; labels are only for validation.
"""

import numpy as np
import pandas as pd

CTR_THRESHOLD = 10_000.0  # the reporting threshold structurers stay under
SUB_BAND_LOW = 8_500.0    # "just under" band: [8500, 10000)
PASS_WINDOW = pd.Timedelta("24h")

FEATURE_COLUMNS = [
    "out_count", "out_total", "out_mean", "out_std", "out_max", "fan_out",
    "in_count", "in_total", "fan_in", "sub10k_out_count", "sub10k_out_total",
    "sub10k_in_count", "sub10k_in_senders", "max_txns_24h", "max_sum_72h",
    "quick_out_total", "cash_quick_out_total", "passthrough_24h_ratio",
    "cash_out_24h_ratio", "amount_z"
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row of behaviour features per account."""
    # 0. ZERO-ROW SAFETY NET (Prevents rolling/merge crashes on empty filters)
    if df.empty:
        empty_df = pd.DataFrame(columns=FEATURE_COLUMNS, dtype=float)
        empty_df.index.name = "account"
        return empty_df

    out_g = df.groupby("from_account", observed=True)
    in_g = df.groupby("to_account", observed=True)

    feats = pd.DataFrame(
        {
            "out_count": out_g.size(),
            "out_total": out_g["amount_paid"].sum(),
            "out_mean": out_g["amount_paid"].mean(),
            "out_std": out_g["amount_paid"].std(),
            "out_max": out_g["amount_paid"].max(),
            "fan_out": out_g["to_account"].nunique(),
        }
    )
    feats = feats.join(
        pd.DataFrame(
            {
                "in_count": in_g.size(),
                "in_total": in_g["amount_paid"].sum(),
                "fan_in": in_g["from_account"].nunique(),
            }
        ),
        how="outer",
    )

    # ── sub-threshold (structuring / smurfing) counts ─────────────────────
    sub = df[
        (df["amount_paid"] >= SUB_BAND_LOW) & (df["amount_paid"] < CTR_THRESHOLD)
    ]
    feats = feats.join(
        sub.groupby("from_account", observed=True)["amount_paid"]
        .agg(sub10k_out_count="count", sub10k_out_total="sum"),
        how="left",
    )
    sub_in = sub.groupby("to_account", observed=True)
    feats = feats.join(
        pd.DataFrame(
            {
                "sub10k_in_count": sub_in.size(),
                "sub10k_in_senders": sub_in["from_account"].nunique(),
            }
        ),
        how="left",
    )

    # ── velocity & rolling sums (time-windowed, per account) ─────────────
    ordered = df.sort_values(["from_account", "timestamp"])
    
    # 24h rolling transaction counts (Simplified index grouping)
    rolled24 = ordered.groupby("from_account", observed=True).rolling(
        "24h", on="timestamp"
    )["amount_paid"]
    max_txns_24h = rolled24.count().groupby("from_account", observed=True).max().rename("max_txns_24h")
    feats = feats.join(max_txns_24h, how="left")

    # 72h rolling transaction sums (Simplified index grouping)
    rolled72 = ordered.groupby("from_account", observed=True).rolling(
        "72h", on="timestamp"
    )["amount_paid"]
    max_sum_72h = rolled72.sum().groupby("from_account", observed=True).max().rename("max_sum_72h")
    feats = feats.join(max_sum_72h, how="left")

    # ── pass-through & rapid cash-out ─────────────────────────────────────
    # Force account to str to avoid categorical dtype mismatch in merge_asof
    inflows = (
        df[["to_account", "timestamp"]]
        .rename(columns={"to_account": "account"})
        .assign(account=lambda x: x["account"].astype(str))
        .sort_values("timestamp")
    )
    outflows = (
        df[["from_account", "timestamp", "amount_paid", "payment_format"]]
        .rename(columns={"from_account": "account"})
        .assign(account=lambda x: x["account"].astype(str))
        .sort_values("timestamp")
    )
    
    matched = pd.merge_asof(
        outflows,
        inflows.assign(inflow_ts=inflows["timestamp"]),
        on="timestamp",
        by="account",
        direction="backward",
    )
    gap = matched["timestamp"] - matched["inflow_ts"]
    matched["quick"] = gap.notna() & (gap <= PASS_WINDOW)
    
    quick_out = (
        matched[matched["quick"]]
        .groupby("account", observed=True)["amount_paid"]
        .sum()
        .rename("quick_out_total")
    )
    cash_quick_out = (
        matched[matched["quick"] & (matched["payment_format"] == "Cash")]
        .groupby("account", observed=True)["amount_paid"]
        .sum()
        .rename("cash_quick_out_total")
    )
    feats = feats.join(quick_out, how="left").join(cash_quick_out, how="left")

    # ── ratios and amount deviation ───────────────────────────────────────
    with np.errstate(divide="ignore", invalid="ignore"):
        feats["passthrough_24h_ratio"] = np.clip(
            np.where(feats["in_total"] > 0, feats["quick_out_total"] / feats["in_total"], 0.0),
            0.0,
            1.0,
        )
        feats["cash_out_24h_ratio"] = np.clip(
            np.where(feats["in_total"] > 0, feats["cash_quick_out_total"] / feats["in_total"], 0.0),
            0.0,
            1.0,
        )
        # amount deviation: how far the account's largest payment sits from typical behaviour
        feats["amount_z"] = np.where(
            feats["out_std"] > 0,
            (feats["out_max"] - feats["out_mean"]) / feats["out_std"],
            0.0,
        )

    # FINAL CLEANUP: Replaces any div-by-zero infs or missing NaNs at the VERY END
    feats = feats.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    feats.index.name = "account"
    return feats