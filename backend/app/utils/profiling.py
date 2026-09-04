"""Base profiling and summary statistics utilities for AML transaction data."""

from typing import Any, Dict, List, Optional, Set
import numpy as np
import pandas as pd


def get_transaction_counts(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute transaction count summary statistics.

    Returns:
        Dict containing total_transactions, laundering_transactions,
        normal_transactions, and laundering_ratio (if label column exists).
    """
    total_transactions = int(len(df))

    if "Is Laundering" not in df.columns:
        return {
            "total_transactions": total_transactions,
            "laundering_transactions": None,
            "normal_transactions": None,
            "laundering_ratio": None,
        }

    if total_transactions == 0:
        return {
            "total_transactions": 0,
            "laundering_transactions": 0,
            "normal_transactions": 0,
            "laundering_ratio": 0.0,
        }

    laundering_series = df["Is Laundering"].dropna()
    laundering_count = int((laundering_series == 1).sum())
    normal_count = int((laundering_series == 0).sum())
    laundering_ratio = float(laundering_count / total_transactions) if total_transactions > 0 else 0.0

    return {
        "total_transactions": total_transactions,
        "laundering_transactions": laundering_count,
        "normal_transactions": normal_count,
        "laundering_ratio": round(laundering_ratio, 6),
    }


def get_entity_cardinalities(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute unique entity (accounts, banks) cardinalities.

    Returns:
        Dict containing unique_senders, unique_receivers,
        total_unique_entities, and unique_banks.
    """
    has_from_account = "From Account" in df.columns
    has_to_account = "To Account" in df.columns

    if not has_from_account and not has_to_account:
        raise ValueError("DataFrame missing required entity columns ('From Account', 'To Account')")

    senders_set: Set[str] = set()
    receivers_set: Set[str] = set()

    if has_from_account:
        senders_series = df["From Account"].dropna().astype(str)
        senders_set = set(senders_series[senders_series.str.strip() != ""])

    if has_to_account:
        receivers_series = df["To Account"].dropna().astype(str)
        receivers_set = set(receivers_series[receivers_series.str.strip() != ""])

    all_entities = senders_set.union(receivers_set)

    banks_set: Set[str] = set()
    if "From Bank" in df.columns:
        from_banks = df["From Bank"].dropna().astype(str)
        banks_set.update(from_banks[from_banks.str.strip() != ""])
    if "To Bank" in df.columns:
        to_banks = df["To Bank"].dropna().astype(str)
        banks_set.update(to_banks[to_banks.str.strip() != ""])

    return {
        "unique_senders": len(senders_set),
        "unique_receivers": len(receivers_set),
        "total_unique_entities": len(all_entities),
        "unique_banks": len(banks_set),
    }


def get_volume_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute transaction volume summary statistics (total, mean, median, min, max).
    Handles single-currency and multi-currency datasets safely without misaggregating.

    Returns:
        Dict containing volume metrics and currency breakdown if multi-currency.
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
        return {
            "total_amount": 0.0,
            "mean_amount": 0.0,
            "median_amount": 0.0,
            "min_amount": 0.0,
            "max_amount": 0.0,
            "count": 0,
            "is_multi_currency": False,
            "currency": None,
        }

    amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()

    if len(amounts) == 0:
        return {
            "total_amount": 0.0,
            "mean_amount": 0.0,
            "median_amount": 0.0,
            "min_amount": 0.0,
            "max_amount": 0.0,
            "count": 0,
            "is_multi_currency": False,
            "currency": None,
        }

    currencies: List[str] = []
    if currency_col and currency_col in df.columns:
        currencies = list(df[currency_col].dropna().unique())

    if len(currencies) > 1:
        # Multi-currency dataset: aggregate per currency to prevent adding different currencies together
        by_currency: Dict[str, Dict[str, Any]] = {}
        for curr in currencies:
            sub_df = df[df[currency_col] == curr]
            sub_amounts = pd.to_numeric(sub_df[amount_col], errors="coerce").dropna()
            if len(sub_amounts) > 0:
                by_currency[str(curr)] = {
                    "total_amount": round(float(sub_amounts.sum()), 2),
                    "mean_amount": round(float(sub_amounts.mean()), 2),
                    "median_amount": round(float(sub_amounts.median()), 2),
                    "min_amount": round(float(sub_amounts.min()), 2),
                    "max_amount": round(float(sub_amounts.max()), 2),
                    "count": int(len(sub_amounts)),
                }

        return {
            "is_multi_currency": True,
            "currencies": currencies,
            "by_currency": by_currency,
        }

    single_currency = currencies[0] if currencies else "US Dollar"
    return {
        "total_amount": round(float(amounts.sum()), 2),
        "mean_amount": round(float(amounts.mean()), 2),
        "median_amount": round(float(amounts.median()), 2),
        "min_amount": round(float(amounts.min()), 2),
        "max_amount": round(float(amounts.max()), 2),
        "count": int(len(amounts)),
        "is_multi_currency": False,
        "currency": str(single_currency),
    }


def get_base_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate comprehensive base profile summary dictionary for a transaction DataFrame.

    Combines transaction counts, entity cardinalities, and volume summary metrics.
    """
    counts = get_transaction_counts(df)
    cardinalities = get_entity_cardinalities(df)
    volume = get_volume_summary(df)

    return {
        "transaction_counts": counts,
        "entity_cardinalities": cardinalities,
        "volume": volume,
    }
