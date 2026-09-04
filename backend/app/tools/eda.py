"""Exploratory Data Analysis (EDA) tool for AML transaction datasets."""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from app.utils.profiling import get_base_profile


def get_eda_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate dataset overview profile using Phase 1 base profiling utilities.

    Returns summary counts, entity cardinalities, and overall volume metrics.
    """
    return get_base_profile(df)


def get_volume_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute deterministic transaction-volume distribution statistics and amount range buckets.

    Handles single and multi-currency datasets safely without misaggregating.
    """
    amount_col = None
    if "Amount Paid" in df.columns:
        amount_col = "Amount Paid"
    elif "Amount Received" in df.columns:
        amount_col = "Amount Received"

    if amount_col is None:
        raise ValueError("DataFrame missing required amount columns ('Amount Paid', 'Amount Received')")

    currency_col = None
    if "Payment Currency" in df.columns:
        currency_col = "Payment Currency"
    elif "Receiving Currency" in df.columns:
        currency_col = "Receiving Currency"

    if len(df) == 0:
        return _empty_volume_distribution()

    currencies: List[str] = []
    if currency_col and currency_col in df.columns:
        currencies = list(df[currency_col].dropna().unique())

    if len(currencies) > 1:
        by_currency: Dict[str, Dict[str, Any]] = {}
        for curr in currencies:
            sub_df = df[df[currency_col] == curr]
            by_currency[str(curr)] = _compute_single_currency_distribution(sub_df, amount_col)
        return {
            "is_multi_currency": True,
            "currencies": currencies,
            "by_currency": by_currency,
        }

    single_currency = currencies[0] if currencies else "US Dollar"
    res = _compute_single_currency_distribution(df, amount_col)
    res["is_multi_currency"] = False
    res["currency"] = str(single_currency)
    return res


def _empty_volume_distribution() -> Dict[str, Any]:
    return {
        "count": 0,
        "mean": 0.0,
        "std": 0.0,
        "min": 0.0,
        "percentiles": {
            "p25": 0.0,
            "p50": 0.0,
            "p75": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        },
        "max": 0.0,
        "buckets": {
            "0-1k": {"count": 0, "percentage": 0.0},
            "1k-5k": {"count": 0, "percentage": 0.0},
            "5k-10k": {"count": 0, "percentage": 0.0},
            "10k-50k": {"count": 0, "percentage": 0.0},
            "50k+": {"count": 0, "percentage": 0.0},
        },
        "is_multi_currency": False,
        "currency": None,
    }


def _compute_single_currency_distribution(df: pd.DataFrame, amount_col: str) -> Dict[str, Any]:
    amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
    total_count = len(amounts)

    if total_count == 0:
        return _empty_volume_distribution()

    mean_val = float(amounts.mean())
    std_val = float(amounts.std(ddof=1)) if total_count > 1 else 0.0
    min_val = float(amounts.min())
    max_val = float(amounts.max())

    p25 = float(np.percentile(amounts, 25))
    p50 = float(np.percentile(amounts, 50))
    p75 = float(np.percentile(amounts, 75))
    p90 = float(np.percentile(amounts, 90))
    p95 = float(np.percentile(amounts, 95))
    p99 = float(np.percentile(amounts, 99))

    # Compute deterministic amount range buckets
    b_0_1k = int((amounts < 1000).sum())
    b_1k_5k = int(((amounts >= 1000) & (amounts < 5000)).sum())
    b_5k_10k = int(((amounts >= 5000) & (amounts < 10000)).sum())
    b_10k_50k = int(((amounts >= 10000) & (amounts < 50000)).sum())
    b_50k_plus = int((amounts >= 50000).sum())

    buckets = {
        "0-1k": {"count": b_0_1k, "percentage": round((b_0_1k / total_count) * 100, 2)},
        "1k-5k": {"count": b_1k_5k, "percentage": round((b_1k_5k / total_count) * 100, 2)},
        "5k-10k": {"count": b_5k_10k, "percentage": round((b_5k_10k / total_count) * 100, 2)},
        "10k-50k": {"count": b_10k_50k, "percentage": round((b_10k_50k / total_count) * 100, 2)},
        "50k+": {"count": b_50k_plus, "percentage": round((b_50k_plus / total_count) * 100, 2)},
    }

    return {
        "count": total_count,
        "mean": round(mean_val, 2),
        "std": round(std_val, 2),
        "min": round(min_val, 2),
        "percentiles": {
            "p25": round(p25, 2),
            "p50": round(p50, 2),
            "p75": round(p75, 2),
            "p90": round(p90, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
        },
        "max": round(max_val, 2),
        "buckets": buckets,
    }


def get_base_rate_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute base-rate statistics from ground-truth laundering labels.

    If label column is unavailable, returns explicit availability flags without fabricating data.
    """
    label_col = "Is Laundering"
    if label_col not in df.columns:
        return {
            "is_available": False,
            "total_labeled_transactions": 0,
            "laundering_count": None,
            "normal_count": None,
            "laundering_rate_percent": None,
            "normal_rate_percent": None,
        }

    labels = pd.to_numeric(df[label_col], errors="coerce").dropna()
    total_labeled = len(labels)

    if total_labeled == 0:
        return {
            "is_available": True,
            "total_labeled_transactions": 0,
            "laundering_count": 0,
            "normal_count": 0,
            "laundering_rate_percent": 0.0,
            "normal_rate_percent": 0.0,
        }

    laundering_count = int((labels == 1).sum())
    normal_count = int((labels == 0).sum())
    laundering_rate = round((laundering_count / total_labeled) * 100, 4)
    normal_rate = round((normal_count / total_labeled) * 100, 4)

    return {
        "is_available": True,
        "total_labeled_transactions": total_labeled,
        "laundering_count": laundering_count,
        "normal_count": normal_count,
        "laundering_rate_percent": laundering_rate,
        "normal_rate_percent": normal_rate,
    }


def get_top_counterparties(df: pd.DataFrame, top_n: int = 10) -> Dict[str, Any]:
    """
    Compute top counterparties by transaction count and transaction volume.

    Args:
        df: Input AML transactions DataFrame.
        top_n: Number of top counterparties to return (must be > 0).
    """
    if top_n <= 0:
        raise ValueError("top_n must be a positive integer")

    has_from = "From Account" in df.columns
    has_to = "To Account" in df.columns

    if not has_from and not has_to:
        raise ValueError("DataFrame missing required entity columns ('From Account', 'To Account')")

    amount_col = None
    if "Amount Paid" in df.columns:
        amount_col = "Amount Paid"
    elif "Amount Received" in df.columns:
        amount_col = "Amount Received"

    total_rows = len(df)

    top_senders_by_count: List[Dict[str, Any]] = []
    top_receivers_by_count: List[Dict[str, Any]] = []
    top_senders_by_volume: List[Dict[str, Any]] = []
    top_receivers_by_volume: List[Dict[str, Any]] = []
    top_entities_combined: List[Dict[str, Any]] = []

    if total_rows == 0:
        return {
            "top_n": top_n,
            "top_senders_by_count": [],
            "top_receivers_by_count": [],
            "top_senders_by_volume": [],
            "top_receivers_by_volume": [],
            "top_entities_combined": [],
        }

    if has_from:
        senders = df["From Account"].dropna().astype(str)
        senders = senders[senders.str.strip() != ""]
        sender_counts = senders.value_counts().head(top_n)
        for entity_id, count in sender_counts.items():
            top_senders_by_count.append({
                "entity_id": str(entity_id),
                "count": int(count),
                "percentage": round((count / total_rows) * 100, 2),
            })

        if amount_col and amount_col in df.columns:
            sub = df[["From Account", amount_col]].dropna()
            sub["From Account"] = sub["From Account"].astype(str)
            sub = sub[sub["From Account"].str.strip() != ""]
            sub[amount_col] = pd.to_numeric(sub[amount_col], errors="coerce")
            vol_agg = sub.groupby("From Account")[amount_col].agg(["sum", "count"]).sort_values(by="sum", ascending=False).head(top_n)
            for entity_id, row in vol_agg.iterrows():
                top_senders_by_volume.append({
                    "entity_id": str(entity_id),
                    "total_volume": round(float(row["sum"]), 2),
                    "count": int(row["count"]),
                })

    if has_to:
        receivers = df["To Account"].dropna().astype(str)
        receivers = receivers[receivers.str.strip() != ""]
        receiver_counts = receivers.value_counts().head(top_n)
        for entity_id, count in receiver_counts.items():
            top_receivers_by_count.append({
                "entity_id": str(entity_id),
                "count": int(count),
                "percentage": round((count / total_rows) * 100, 2),
            })

        if amount_col and amount_col in df.columns:
            sub = df[["To Account", amount_col]].dropna()
            sub["To Account"] = sub["To Account"].astype(str)
            sub = sub[sub["To Account"].str.strip() != ""]
            sub[amount_col] = pd.to_numeric(sub[amount_col], errors="coerce")
            vol_agg = sub.groupby("To Account")[amount_col].agg(["sum", "count"]).sort_values(by="sum", ascending=False).head(top_n)
            for entity_id, row in vol_agg.iterrows():
                top_receivers_by_volume.append({
                    "entity_id": str(entity_id),
                    "total_volume": round(float(row["sum"]), 2),
                    "count": int(row["count"]),
                })

    # Calculate combined top entities across senders and receivers
    entity_stats: Dict[str, Dict[str, Any]] = {}
    if has_from and amount_col:
        for _, row in df.iterrows():
            sender = str(row.get("From Account", "")).strip()
            amt = float(pd.to_numeric(row.get(amount_col, 0), errors="coerce") or 0.0)
            if sender:
                if sender not in entity_stats:
                    entity_stats[sender] = {"total_transactions": 0, "total_volume": 0.0}
                entity_stats[sender]["total_transactions"] += 1
                entity_stats[sender]["total_volume"] += amt

    if has_to and amount_col:
        for _, row in df.iterrows():
            receiver = str(row.get("To Account", "")).strip()
            amt = float(pd.to_numeric(row.get(amount_col, 0), errors="coerce") or 0.0)
            if receiver:
                if receiver not in entity_stats:
                    entity_stats[receiver] = {"total_transactions": 0, "total_volume": 0.0}
                entity_stats[receiver]["total_transactions"] += 1
                entity_stats[receiver]["total_volume"] += amt

    sorted_entities = sorted(entity_stats.items(), key=lambda item: item[1]["total_volume"], reverse=True)[:top_n]
    for entity_id, stats in sorted_entities:
        top_entities_combined.append({
            "entity_id": entity_id,
            "total_transactions": stats["total_transactions"],
            "total_volume": round(stats["total_volume"], 2),
        })

    return {
        "top_n": top_n,
        "top_senders_by_count": top_senders_by_count,
        "top_receivers_by_count": top_receivers_by_count,
        "top_senders_by_volume": top_senders_by_volume,
        "top_receivers_by_volume": top_receivers_by_volume,
        "top_entities_combined": top_entities_combined,
    }


def run_eda(df: pd.DataFrame, top_n: int = 10) -> Dict[str, Any]:
    """
    Main entry point for EDA tool execution.

    Combines base dataset profiling, volume distributions, base-rate statistics,
    and top counterparty analysis into a single JSON-serializable dictionary.
    """
    profile = get_eda_profile(df)
    volume_dist = get_volume_distribution(df)
    base_rates = get_base_rate_stats(df)
    top_counterparties = get_top_counterparties(df, top_n=top_n)

    return {
        "profile": profile,
        "volume_distribution": volume_dist,
        "base_rates": base_rates,
        "top_counterparties": top_counterparties,
    }
