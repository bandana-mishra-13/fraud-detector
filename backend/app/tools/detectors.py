"""Deterministic AML Rule Detectors (Task 2.3).

Implements typology-specific rule detection algorithms:
- Structuring / sub-threshold CTR evasion
- Smurfing / multi-source fan-in consolidation
- Rapid layering / pass-through mule conduits
- Fan-out fund dispersion
- High-velocity transaction bursts
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Union

import pandas as pd

from app.models.schemas import Flag, RiskTier


def _get_tx_id(row: pd.Series, fallback_idx: int) -> str:
    """Helper to extract or generate a consistent transaction ID."""
    if "transaction_id" in row and pd.notna(row["transaction_id"]):
        return str(row["transaction_id"])
    if "Transaction ID" in row and pd.notna(row["Transaction ID"]):
        return str(row["Transaction ID"])
    return f"TX_{fallback_idx}"


def _ensure_datetime_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure DataFrame has a parsed Timestamp datetime column without mutating original."""
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy["Timestamp"]):
        df_copy["Timestamp"] = pd.to_datetime(df_copy["Timestamp"], errors="coerce")
    return df_copy


def detect_structuring(
    df: pd.DataFrame,
    min_amount: float = 7500.0,
    max_amount: float = 9999.99,
    min_tx_count: int = 2,
    window_hours: float = 72.0,
) -> List[Flag]:
    """Detect structuring / smurfing transactions just below CTR reporting thresholds.

    Identifies accounts sending or receiving multiple transactions within a rolling
    time window where each transaction is in the [min_amount, max_amount] range.
    """
    if df.empty or "Timestamp" not in df.columns:
        return []

    data = _ensure_datetime_timestamps(df)
    flags: List[Flag] = []

    # Check structuring on outbound (From Account) and inbound (To Account)
    for role, acct_col, amt_col in [
        ("Outbound", "From Account", "Amount Paid"),
        ("Inbound", "To Account", "Amount Received"),
    ]:
        if acct_col not in data.columns or amt_col not in data.columns:
            continue

        # Filter to candidate transactions in target range
        candidate_mask = (data[amt_col] >= min_amount) & (data[amt_col] <= max_amount)
        candidates = data[candidate_mask].copy()

        if candidates.empty:
            continue

        for account, group in candidates.groupby(acct_col):
            if len(group) < min_tx_count:
                continue

            sorted_group = group.sort_values("Timestamp")
            n = len(sorted_group)
            i = 0
            visited_indices: Set[int] = set()

            while i < n:
                if i in visited_indices:
                    i += 1
                    continue

                window_start = sorted_group.iloc[i]["Timestamp"]
                window_end = window_start + timedelta(hours=window_hours)

                window_mask = (sorted_group["Timestamp"] >= window_start) & (
                    sorted_group["Timestamp"] <= window_end
                )
                window_txs = sorted_group[window_mask]

                if len(window_txs) >= min_tx_count:
                    tx_indices = list(window_txs.index)
                    visited_indices.update(tx_indices)

                    tx_ids = [
                        _get_tx_id(window_txs.loc[idx], idx) for idx in tx_indices
                    ]
                    total_amount = float(window_txs[amt_col].sum())
                    tx_count = len(window_txs)
                    first_ts = window_txs["Timestamp"].min()
                    last_ts = window_txs["Timestamp"].max()
                    time_span_hours = (
                        (last_ts - first_ts).total_seconds() / 3600.0
                        if pd.notna(first_ts) and pd.notna(last_ts)
                        else 0.0
                    )

                    severity = (
                        RiskTier.CRITICAL
                        if tx_count >= 4 or total_amount >= 30000.0
                        else RiskTier.HIGH
                    )

                    flag = Flag(
                        flag_id=str(uuid.uuid4()),
                        rule_id="RULE_STRUCTURING_01",
                        rule_name=f"{role} Structuring below Reporting Threshold",
                        severity=severity,
                        entity_id=str(account),
                        transaction_ids=tx_ids,
                        typology="Structuring",
                        reason=(
                            f"Account {account} conducted {tx_count} {role.lower()} transactions "
                            f"between ${min_amount:,.2f} and ${max_amount:,.2f} totaling "
                            f"${total_amount:,.2f} within {time_span_hours:.1f} hours, indicating potential "
                            f"structuring to evade CTR reporting limits."
                        ),
                        evidence={
                            "role": role,
                            "tx_count": tx_count,
                            "total_amount": total_amount,
                            "min_tx_amount": float(window_txs[amt_col].min()),
                            "max_tx_amount": float(window_txs[amt_col].max()),
                            "time_span_hours": round(time_span_hours, 2),
                            "window_threshold_hours": window_hours,
                        },
                    )
                    flags.append(flag)

                i += 1

    return flags


def detect_smurfing(
    df: pd.DataFrame,
    min_senders: int = 3,
    window_hours: float = 24.0,
    min_total_amount: float = 10000.0,
) -> List[Flag]:
    """Detect smurfing / fan-in fund consolidation.

    Identifies destination accounts receiving funds from multiple distinct originators
    within a concentrated time window.
    """
    if df.empty or "Timestamp" not in df.columns:
        return []

    data = _ensure_datetime_timestamps(df)
    flags: List[Flag] = []

    if "To Account" not in data.columns or "From Account" not in data.columns:
        return []

    amt_col = "Amount Received" if "Amount Received" in data.columns else "Amount Paid"

    for dest_account, group in data.groupby("To Account"):
        sorted_group = group.sort_values("Timestamp")
        n = len(sorted_group)
        i = 0
        visited_indices: Set[int] = set()

        while i < n:
            if i in visited_indices:
                i += 1
                continue

            window_start = sorted_group.iloc[i]["Timestamp"]
            window_end = window_start + timedelta(hours=window_hours)

            window_mask = (sorted_group["Timestamp"] >= window_start) & (
                sorted_group["Timestamp"] <= window_end
            )
            window_txs = sorted_group[window_mask]

            distinct_senders = window_txs["From Account"].nunique()
            total_amount = float(window_txs[amt_col].sum())

            if distinct_senders >= min_senders and total_amount >= min_total_amount:
                tx_indices = list(window_txs.index)
                visited_indices.update(tx_indices)

                tx_ids = [_get_tx_id(window_txs.loc[idx], idx) for idx in tx_indices]
                sender_list = [str(s) for s in window_txs["From Account"].unique()][:10]

                first_ts = window_txs["Timestamp"].min()
                last_ts = window_txs["Timestamp"].max()
                time_span_hours = (
                    (last_ts - first_ts).total_seconds() / 3600.0
                    if pd.notna(first_ts) and pd.notna(last_ts)
                    else 0.0
                )

                severity = (
                    RiskTier.CRITICAL
                    if distinct_senders >= 5 or total_amount >= 50000.0
                    else RiskTier.HIGH
                )

                flag = Flag(
                    flag_id=str(uuid.uuid4()),
                    rule_id="RULE_SMURFING_FAN_IN_01",
                    rule_name="Multi-Source Fan-In Consolidation (Smurfing)",
                    severity=severity,
                    entity_id=str(dest_account),
                    transaction_ids=tx_ids,
                    typology="Smurfing",
                    reason=(
                        f"Account {dest_account} consolidated ${total_amount:,.2f} from {distinct_senders} "
                        f"distinct originating accounts within {time_span_hours:.1f} hours, matching smurfing patterns."
                    ),
                    evidence={
                        "distinct_senders": distinct_senders,
                        "total_amount": total_amount,
                        "time_span_hours": round(time_span_hours, 2),
                        "sample_senders": sender_list,
                    },
                )
                flags.append(flag)

            i += 1

    return flags


def detect_rapid_layering(
    df: pd.DataFrame,
    window_hours: float = 6.0,
    min_pass_through_ratio: float = 0.80,
    min_amount: float = 5000.0,
) -> List[Flag]:
    """Detect rapid layering / pass-through mule account behavior.

    Identifies accounts where significant funds are received and subsequently
    transferred out within a narrow time window with high turnover ratio.
    """
    if df.empty or "Timestamp" not in df.columns:
        return []

    data = _ensure_datetime_timestamps(df)
    flags: List[Flag] = []

    required_cols = {"From Account", "To Account", "Amount Received", "Amount Paid"}
    if not required_cols.issubset(data.columns):
        return []

    # Get all active accounts that appear as both sender and receiver
    senders = set(data["From Account"].dropna().unique())
    receivers = set(data["To Account"].dropna().unique())
    intermediaries = senders.intersection(receivers)

    for account in intermediaries:
        inbound = data[
            (data["To Account"] == account) & (data["Amount Received"] >= min_amount)
        ].sort_values("Timestamp")
        outbound = data[
            (data["From Account"] == account) & (data["Amount Paid"] >= min_amount * min_pass_through_ratio)
        ].sort_values("Timestamp")

        if inbound.empty or outbound.empty:
            continue

        for in_idx, in_row in inbound.iterrows():
            in_ts = in_row["Timestamp"]
            in_amt = float(in_row["Amount Received"])
            window_end = in_ts + timedelta(hours=window_hours)

            # Match outbound transfers shortly after inbound deposit
            matching_out = outbound[
                (outbound["Timestamp"] >= in_ts) & (outbound["Timestamp"] <= window_end)
            ]

            if matching_out.empty:
                continue

            total_out = float(matching_out["Amount Paid"].sum())
            pass_through_ratio = total_out / in_amt if in_amt > 0 else 0.0

            if pass_through_ratio >= min_pass_through_ratio:
                out_tx_ids = [
                    _get_tx_id(matching_out.loc[o_idx], o_idx)
                    for o_idx in matching_out.index
                ]
                in_tx_id = _get_tx_id(in_row, in_idx)
                all_tx_ids = [in_tx_id] + out_tx_ids

                first_out_ts = matching_out["Timestamp"].min()
                time_delta_mins = (
                    (first_out_ts - in_ts).total_seconds() / 60.0
                    if pd.notna(first_out_ts) and pd.notna(in_ts)
                    else 0.0
                )

                flag = Flag(
                    flag_id=str(uuid.uuid4()),
                    rule_id="RULE_RAPID_LAYERING_01",
                    rule_name="Rapid Layering / Pass-Through Conduit",
                    severity=RiskTier.CRITICAL,
                    entity_id=str(account),
                    transaction_ids=all_tx_ids,
                    typology="Pass-through",
                    reason=(
                        f"Account {account} received ${in_amt:,.2f} and transferred out "
                        f"${total_out:,.2f} ({pass_through_ratio:.1%} turnover) within "
                        f"{time_delta_mins:.1f} minutes, indicating pass-through conduit activity."
                    ),
                    evidence={
                        "in_amount": in_amt,
                        "out_amount": total_out,
                        "pass_through_ratio": round(pass_through_ratio, 4),
                        "time_delta_minutes": round(time_delta_mins, 2),
                        "in_transaction_id": in_tx_id,
                        "out_transaction_ids": out_tx_ids,
                    },
                )
                flags.append(flag)
                # Break to prevent duplicate flags on same in_row
                break

    return flags


def detect_fan_out(
    df: pd.DataFrame,
    min_recipients: int = 3,
    window_hours: float = 24.0,
    min_total_amount: float = 10000.0,
) -> List[Flag]:
    """Detect fan-out fund dispersion pattern.

    Identifies source accounts rapidly dispersing funds to multiple distinct
    beneficiary accounts within a concentrated window.
    """
    if df.empty or "Timestamp" not in df.columns:
        return []

    data = _ensure_datetime_timestamps(df)
    flags: List[Flag] = []

    if "From Account" not in data.columns or "To Account" not in data.columns:
        return []

    amt_col = "Amount Paid" if "Amount Paid" in data.columns else "Amount Received"

    for src_account, group in data.groupby("From Account"):
        sorted_group = group.sort_values("Timestamp")
        n = len(sorted_group)
        i = 0
        visited_indices: Set[int] = set()

        while i < n:
            if i in visited_indices:
                i += 1
                continue

            window_start = sorted_group.iloc[i]["Timestamp"]
            window_end = window_start + timedelta(hours=window_hours)

            window_mask = (sorted_group["Timestamp"] >= window_start) & (
                sorted_group["Timestamp"] <= window_end
            )
            window_txs = sorted_group[window_mask]

            distinct_recipients = window_txs["To Account"].nunique()
            total_amount = float(window_txs[amt_col].sum())

            if distinct_recipients >= min_recipients and total_amount >= min_total_amount:
                tx_indices = list(window_txs.index)
                visited_indices.update(tx_indices)

                tx_ids = [_get_tx_id(window_txs.loc[idx], idx) for idx in tx_indices]
                recipient_list = [str(r) for r in window_txs["To Account"].unique()][:10]

                first_ts = window_txs["Timestamp"].min()
                last_ts = window_txs["Timestamp"].max()
                time_span_hours = (
                    (last_ts - first_ts).total_seconds() / 3600.0
                    if pd.notna(first_ts) and pd.notna(last_ts)
                    else 0.0
                )

                severity = (
                    RiskTier.CRITICAL
                    if distinct_recipients >= 5 or total_amount >= 50000.0
                    else RiskTier.HIGH
                )

                flag = Flag(
                    flag_id=str(uuid.uuid4()),
                    rule_id="RULE_FAN_OUT_01",
                    rule_name="High Fan-Out Fund Dispersion",
                    severity=severity,
                    entity_id=str(src_account),
                    transaction_ids=tx_ids,
                    typology="Fan-out",
                    reason=(
                        f"Source account {src_account} dispersed ${total_amount:,.2f} across "
                        f"{distinct_recipients} distinct beneficiary accounts within {time_span_hours:.1f} hours."
                    ),
                    evidence={
                        "distinct_recipients": distinct_recipients,
                        "total_amount": total_amount,
                        "time_span_hours": round(time_span_hours, 2),
                        "sample_recipients": recipient_list,
                    },
                )
                flags.append(flag)

            i += 1

    return flags


def detect_high_velocity(
    df: pd.DataFrame,
    min_tx_count: int = 5,
    window_hours: float = 2.0,
    min_total_amount: float = 5000.0,
) -> List[Flag]:
    """Detect abnormal high-velocity bursts in transaction activity."""
    if df.empty or "Timestamp" not in df.columns:
        return []

    data = _ensure_datetime_timestamps(df)
    flags: List[Flag] = []

    for role, acct_col, amt_col in [
        ("Outbound", "From Account", "Amount Paid"),
        ("Inbound", "To Account", "Amount Received"),
    ]:
        if acct_col not in data.columns or amt_col not in data.columns:
            continue

        for account, group in data.groupby(acct_col):
            if len(group) < min_tx_count:
                continue

            sorted_group = group.sort_values("Timestamp")
            n = len(sorted_group)
            i = 0
            visited_indices: Set[int] = set()

            while i < n:
                if i in visited_indices:
                    i += 1
                    continue

                window_start = sorted_group.iloc[i]["Timestamp"]
                window_end = window_start + timedelta(hours=window_hours)

                window_mask = (sorted_group["Timestamp"] >= window_start) & (
                    sorted_group["Timestamp"] <= window_end
                )
                window_txs = sorted_group[window_mask]

                tx_count = len(window_txs)
                total_amount = float(window_txs[amt_col].sum())

                if tx_count >= min_tx_count and total_amount >= min_total_amount:
                    tx_indices = list(window_txs.index)
                    visited_indices.update(tx_indices)

                    tx_ids = [_get_tx_id(window_txs.loc[idx], idx) for idx in tx_indices]
                    first_ts = window_txs["Timestamp"].min()
                    last_ts = window_txs["Timestamp"].max()
                    time_span_mins = (
                        (last_ts - first_ts).total_seconds() / 60.0
                        if pd.notna(first_ts) and pd.notna(last_ts)
                        else 0.0
                    )

                    flag = Flag(
                        flag_id=str(uuid.uuid4()),
                        rule_id="RULE_HIGH_VELOCITY_01",
                        rule_name=f"High {role} Velocity Burst",
                        severity=RiskTier.MEDIUM,
                        entity_id=str(account),
                        transaction_ids=tx_ids,
                        typology="Velocity Spike",
                        reason=(
                            f"Account {account} executed {tx_count} {role.lower()} transactions "
                            f"totaling ${total_amount:,.2f} within {time_span_mins:.1f} minutes."
                        ),
                        evidence={
                            "role": role,
                            "tx_count": tx_count,
                            "total_amount": total_amount,
                            "time_span_minutes": round(time_span_mins, 2),
                        },
                    )
                    flags.append(flag)

                i += 1

    return flags


def run_rule_detectors(
    df: pd.DataFrame,
    entity_id: Optional[str] = None,
    rules: Optional[List[str]] = None,
) -> List[Flag]:
    """Master rule runner to execute all or selected deterministic AML rule detectors.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized AML transaction DataFrame.
    entity_id : Optional[str]
        If provided, filters analysis to transactions involving this account/entity.
    rules : Optional[List[str]]
        List of specific rule keys to execute (e.g. ['structuring', 'smurfing', 'layering', 'fan_out', 'velocity']).
        If None, all rule detectors are executed.

    Returns
    -------
    List[Flag]
        List of triggered Pydantic Flag models.
    """
    if df.empty:
        return []

    target_df = df.copy()
    if entity_id:
        target_df = target_df[
            (target_df["From Account"] == entity_id) | (target_df["To Account"] == entity_id)
        ]
        if target_df.empty:
            return []

    all_flags: List[Flag] = []

    available_detectors = {
        "structuring": lambda: detect_structuring(target_df),
        "smurfing": lambda: detect_smurfing(target_df),
        "layering": lambda: detect_rapid_layering(target_df),
        "rapid_layering": lambda: detect_rapid_layering(target_df),
        "fan_out": lambda: detect_fan_out(target_df),
        "velocity": lambda: detect_high_velocity(target_df),
        "high_velocity": lambda: detect_high_velocity(target_df),
    }

    if rules is None:
        selected_rules = ["structuring", "smurfing", "layering", "fan_out", "velocity"]
    else:
        selected_rules = [r.lower().replace("-", "_") for r in rules]

    executed: Set[str] = set()
    for rule_key in selected_rules:
        canonical_key = (
            "layering"
            if rule_key == "rapid_layering"
            else "velocity"
            if rule_key == "high_velocity"
            else rule_key
        )
        if canonical_key in executed:
            continue

        if rule_key in available_detectors:
            flags = available_detectors[rule_key]()
            all_flags.extend(flags)
            executed.add(canonical_key)

    # Filter to entity_id if specified
    if entity_id:
        all_flags = [f for f in all_flags if f.entity_id == entity_id]

    return all_flags
