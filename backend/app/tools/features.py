"""Deterministic transaction features for AML rules and anomaly models."""

from collections import Counter, deque
from typing import Final

import pandas as pd


REQUIRED_FEATURE_COLUMNS: Final = (
    "Timestamp",
    "From Account",
    "To Account",
    "Amount Paid",
    "Amount Received",
)
FEATURE_COLUMNS: Final = (
    "outbound_rolling_amount_sum",
    "inbound_rolling_amount_sum",
    "outbound_rolling_transaction_count",
    "inbound_rolling_transaction_count",
    "outbound_rolling_sub_threshold_count",
    "inbound_rolling_sub_threshold_count",
    "outbound_amount_deviation_from_mean",
    "inbound_amount_deviation_from_mean",
    "outbound_rolling_fan_out_count",
    "inbound_rolling_fan_in_count",
)
_FEATURE_DTYPES: Final = {
    "outbound_rolling_amount_sum": "float64",
    "inbound_rolling_amount_sum": "float64",
    "outbound_rolling_transaction_count": "int64",
    "inbound_rolling_transaction_count": "int64",
    "outbound_rolling_sub_threshold_count": "int64",
    "inbound_rolling_sub_threshold_count": "int64",
    "outbound_amount_deviation_from_mean": "float64",
    "inbound_amount_deviation_from_mean": "float64",
    "outbound_rolling_fan_out_count": "int64",
    "inbound_rolling_fan_in_count": "int64",
}


def engineer_features(
    transactions: pd.DataFrame,
    window: str | pd.Timedelta = "24h",
    sub_threshold: float = 10_000.0,
) -> pd.DataFrame:
    """Add rolling transaction features without modifying ``transactions``.

    Windows include the current transaction and earlier transactions in the
    same account stream. Deviation is measured against the preceding rolling
    mean, using ``0.0`` where no earlier transaction is available.
    """
    _validate_required_columns(transactions)
    rolling_window = _parse_window(window)
    if sub_threshold < 0:
        raise ValueError("sub_threshold must be non-negative")

    featured = transactions.copy(deep=True)
    featured["Timestamp"] = pd.to_datetime(featured["Timestamp"], errors="raise")
    if featured["Timestamp"].isna().any():
        raise ValueError("Timestamp contains missing values")

    featured["Amount Paid"] = pd.to_numeric(featured["Amount Paid"], errors="raise")
    featured["Amount Received"] = pd.to_numeric(
        featured["Amount Received"],
        errors="raise",
    )
    if featured[["Amount Paid", "Amount Received"]].isna().any().any():
        raise ValueError("Amount Paid and Amount Received must not contain missing values")

    featured["_feature_position"] = range(len(featured))
    featured = featured.sort_values(
        ["Timestamp", "_feature_position"],
        kind="stable",
    )

    outbound = _calculate_directional_features(
        featured,
        account_column="From Account",
        counterparty_column="To Account",
        amount_column="Amount Paid",
        prefix="outbound",
        window=rolling_window,
        sub_threshold=sub_threshold,
    )
    inbound = _calculate_directional_features(
        featured,
        account_column="To Account",
        counterparty_column="From Account",
        amount_column="Amount Received",
        prefix="inbound",
        window=rolling_window,
        sub_threshold=sub_threshold,
    )

    feature_values = {**outbound, **inbound}
    for feature_name in FEATURE_COLUMNS:
        values = feature_values[feature_name]
        ordered_values = [values[position] for position in featured["_feature_position"]]
        featured[feature_name] = pd.Series(
            ordered_values,
            index=featured.index,
            dtype=_FEATURE_DTYPES[feature_name],
        )

    return featured.sort_values("_feature_position", kind="stable").drop(
        columns="_feature_position"
    )


def _validate_required_columns(transactions: pd.DataFrame) -> None:
    missing_columns = [
        column for column in REQUIRED_FEATURE_COLUMNS if column not in transactions.columns
    ]
    if missing_columns:
        raise ValueError(
            "Transaction DataFrame is missing required columns: "
            + ", ".join(missing_columns)
        )


def _parse_window(window: str | pd.Timedelta) -> pd.Timedelta:
    try:
        parsed_window = pd.Timedelta(window)
    except (TypeError, ValueError) as error:
        raise ValueError("window must be a valid positive pandas timedelta") from error

    if parsed_window <= pd.Timedelta(0):
        raise ValueError("window must be a positive pandas timedelta")
    return parsed_window


def _calculate_directional_features(
    transactions: pd.DataFrame,
    *,
    account_column: str,
    counterparty_column: str,
    amount_column: str,
    prefix: str,
    window: pd.Timedelta,
    sub_threshold: float,
) -> dict[str, list[float | int]]:
    amount_sums = [0.0] * len(transactions)
    transaction_counts = [0] * len(transactions)
    sub_threshold_counts = [0] * len(transactions)
    deviations = [0.0] * len(transactions)
    distinct_counterparty_counts = [0] * len(transactions)

    for _, account_transactions in transactions.groupby(
        account_column,
        sort=False,
        dropna=False,
    ):
        rolling_rows: deque[tuple[pd.Timestamp, float, bool, object]] = deque()
        counterparties: Counter[object] = Counter()
        rolling_sum = 0.0
        rolling_count = 0
        rolling_sub_threshold_count = 0

        selected_columns = [
            "_feature_position",
            "Timestamp",
            amount_column,
            counterparty_column,
        ]
        for position, timestamp, amount, counterparty in account_transactions[
            selected_columns
        ].itertuples(index=False, name=None):
            cutoff = timestamp - window
            while rolling_rows and rolling_rows[0][0] < cutoff:
                _, expired_amount, expired_is_sub_threshold, expired_counterparty = (
                    rolling_rows.popleft()
                )
                rolling_sum -= expired_amount
                rolling_count -= 1
                rolling_sub_threshold_count -= int(expired_is_sub_threshold)
                counterparties[expired_counterparty] -= 1
                if counterparties[expired_counterparty] == 0:
                    del counterparties[expired_counterparty]

            numeric_amount = float(amount)
            prior_mean = rolling_sum / rolling_count if rolling_count else 0.0
            is_sub_threshold = numeric_amount < sub_threshold
            counterparty_key = None if pd.isna(counterparty) else counterparty

            rolling_rows.append(
                (timestamp, numeric_amount, is_sub_threshold, counterparty_key)
            )
            rolling_sum += numeric_amount
            rolling_count += 1
            rolling_sub_threshold_count += int(is_sub_threshold)
            counterparties[counterparty_key] += 1

            row_position = int(position)
            amount_sums[row_position] = rolling_sum
            transaction_counts[row_position] = rolling_count
            sub_threshold_counts[row_position] = rolling_sub_threshold_count
            deviations[row_position] = numeric_amount - prior_mean if rolling_count > 1 else 0.0
            distinct_counterparty_counts[row_position] = len(counterparties)

    counterpart_feature = "fan_out" if prefix == "outbound" else "fan_in"
    return {
        f"{prefix}_rolling_amount_sum": amount_sums,
        f"{prefix}_rolling_transaction_count": transaction_counts,
        f"{prefix}_rolling_sub_threshold_count": sub_threshold_counts,
        f"{prefix}_amount_deviation_from_mean": deviations,
        f"{prefix}_rolling_{counterpart_feature}_count": distinct_counterparty_counts,
    }
