"""EDA Tool — profiling, distributions, and chart-ready summaries.

Invoked when the query calls for broad exploration; skipped for targeted or
single-entity queries. Output is JSON-safe and shaped for the Charts tab.
"""

import numpy as np
import pandas as pd


def run_eda(df: pd.DataFrame) -> dict:
    amounts = df["amount_paid"]

    # transactions per day (time series)
    per_day = (
        df.set_index("timestamp")
        .resample("D")["amount_paid"]
        .agg(count="count", volume="sum")
        .reset_index()
    )
    txns_per_day = [
        {
            "date": ts.strftime("%Y-%m-%d"),
            "count": int(c),
            "volume": round(float(v), 2),
        }
        for ts, c, v in zip(per_day["timestamp"], per_day["count"], per_day["volume"])
    ]

    # amount distribution — log-spaced bins (amounts span cents → millions)
    positive = amounts[amounts > 0]
    edges = np.logspace(
        np.log10(max(positive.min(), 0.01)), np.log10(positive.max()), num=25
    )
    hist, _ = np.histogram(positive, bins=edges)
    amount_hist = [
        {"bin_low": round(float(lo), 2), "bin_high": round(float(hi), 2), "count": int(n)}
        for lo, hi, n in zip(edges[:-1], edges[1:], hist)
    ]

    fmt_counts = df["payment_format"].value_counts()
    cur_counts = df["payment_currency"].value_counts().head(8)

    top_senders = (
        df.groupby("from_account", observed=True)["amount_paid"]
        .agg(count="count", volume="sum")
        .nlargest(10, "volume")
        .reset_index()
    )

    summary: dict = {
        "rows": int(len(df)),
        "accounts": int(
            pd.unique(
                pd.concat([df["from_account"], df["to_account"]], ignore_index=True)
            ).size
        ),
        "date_from": str(df["timestamp"].min()),
        "date_to": str(df["timestamp"].max()),
        "total_volume": round(float(amounts.sum()), 2),
        "amount_stats": {
            "mean": round(float(amounts.mean()), 2),
            "median": round(float(amounts.median()), 2),
            "p95": round(float(amounts.quantile(0.95)), 2),
            "max": round(float(amounts.max()), 2),
        },
        "charts": {
            "txns_per_day": txns_per_day,
            "amount_hist": amount_hist,
            "payment_formats": [
                {"format": str(k), "count": int(v)} for k, v in fmt_counts.items()
            ],
            "currencies": [
                {"currency": str(k), "count": int(v)} for k, v in cur_counts.items()
            ],
            "top_senders": [
                {
                    "account": str(r.from_account),
                    "count": int(r.count),
                    "volume": round(float(r.volume), 2),
                }
                for r in top_senders.itertuples()
            ],
        },
    }

    # ground-truth base rate, for reviewer context (never used by detection)
    if "is_laundering" in df.columns:
        summary["labeled_laundering_rate"] = round(
            float(df["is_laundering"].mean()), 6
        )

    return summary
