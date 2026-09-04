import pandas as pd
import pandas.testing as pdt
import pytest

from app.tools.data_loader import load_transactions
from app.tools.features import FEATURE_COLUMNS, engineer_features


def _transactions_for_features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Transaction ID": ["tx-3", "tx-1", "tx-2", "tx-4"],
            "Timestamp": [
                "2024-01-01 10:10:00",
                "2024-01-01 10:00:00",
                "2024-01-01 10:05:00",
                "2024-01-01 10:15:00",
            ],
            "From Account": ["A", "A", "A", "B"],
            "To Account": ["X", "X", "Y", "X"],
            "Amount Paid": [3000.0, 5000.0, 12000.0, 2000.0],
            "Amount Received": [3000.0, 5000.0, 12000.0, 2000.0],
        },
        index=[30, 10, 20, 40],
    )


def _row_by_id(featured: pd.DataFrame, transaction_id: str) -> pd.Series:
    return featured.loc[featured["Transaction ID"] == transaction_id].iloc[0]


def test_engineers_exact_rolling_features_without_reordering_or_mutation():
    transactions = _transactions_for_features()
    original = transactions.copy(deep=True)

    featured = engineer_features(transactions, window="1h", sub_threshold=10_000.0)

    pdt.assert_frame_equal(transactions, original)
    assert featured.index.equals(transactions.index)
    assert list(featured["Transaction ID"]) == list(transactions["Transaction ID"])
    assert list(featured.columns[: len(transactions.columns)]) == list(transactions.columns)
    assert pd.api.types.is_datetime64_any_dtype(featured["Timestamp"])

    tx1 = _row_by_id(featured, "tx-1")
    tx2 = _row_by_id(featured, "tx-2")
    tx3 = _row_by_id(featured, "tx-3")
    tx4 = _row_by_id(featured, "tx-4")

    assert tx1["outbound_rolling_amount_sum"] == 5000.0
    assert tx2["outbound_rolling_amount_sum"] == 17000.0
    assert tx3["outbound_rolling_amount_sum"] == 20000.0
    assert tx1["outbound_rolling_transaction_count"] == 1
    assert tx2["outbound_rolling_transaction_count"] == 2
    assert tx3["outbound_rolling_transaction_count"] == 3
    assert tx1["outbound_rolling_sub_threshold_count"] == 1
    assert tx2["outbound_rolling_sub_threshold_count"] == 1
    assert tx3["outbound_rolling_sub_threshold_count"] == 2
    assert tx1["outbound_amount_deviation_from_mean"] == 0.0
    assert tx2["outbound_amount_deviation_from_mean"] == 7000.0
    assert tx3["outbound_amount_deviation_from_mean"] == -5500.0
    assert tx1["outbound_rolling_fan_out_count"] == 1
    assert tx2["outbound_rolling_fan_out_count"] == 2
    assert tx3["outbound_rolling_fan_out_count"] == 2

    assert tx1["inbound_rolling_amount_sum"] == 5000.0
    assert tx3["inbound_rolling_amount_sum"] == 8000.0
    assert tx4["inbound_rolling_amount_sum"] == 10000.0
    assert tx1["inbound_rolling_transaction_count"] == 1
    assert tx3["inbound_rolling_transaction_count"] == 2
    assert tx4["inbound_rolling_transaction_count"] == 3
    assert tx1["inbound_rolling_sub_threshold_count"] == 1
    assert tx3["inbound_rolling_sub_threshold_count"] == 2
    assert tx4["inbound_rolling_sub_threshold_count"] == 3
    assert tx1["inbound_amount_deviation_from_mean"] == 0.0
    assert tx3["inbound_amount_deviation_from_mean"] == -2000.0
    assert tx4["inbound_amount_deviation_from_mean"] == -2000.0
    assert tx1["inbound_rolling_fan_in_count"] == 1
    assert tx3["inbound_rolling_fan_in_count"] == 1
    assert tx4["inbound_rolling_fan_in_count"] == 2


def test_earliest_transaction_does_not_use_later_data():
    featured = engineer_features(_transactions_for_features(), window="1h")
    earliest = _row_by_id(featured, "tx-1")

    assert earliest["outbound_rolling_amount_sum"] == 5000.0
    assert earliest["outbound_rolling_transaction_count"] == 1
    assert earliest["outbound_amount_deviation_from_mean"] == 0.0


def test_empty_dataframe_returns_empty_featured_dataframe():
    empty_transactions = _transactions_for_features().iloc[0:0]

    featured = engineer_features(empty_transactions)

    assert featured.empty
    assert list(featured.columns) == list(empty_transactions.columns) + list(FEATURE_COLUMNS)


def test_missing_required_column_raises_clear_value_error():
    transactions = _transactions_for_features().drop(columns="Amount Paid")

    with pytest.raises(ValueError, match="missing required columns: Amount Paid"):
        engineer_features(transactions)


def test_repeated_calls_are_deterministic():
    transactions = _transactions_for_features()

    first = engineer_features(transactions, window="1h")
    second = engineer_features(transactions, window="1h")

    pdt.assert_frame_equal(first, second)


def test_loaded_synthetic_data_integrates_with_feature_engineering():
    transactions = load_transactions("synthetic_transactions.csv")
    original = transactions.copy(deep=True)

    featured = engineer_features(transactions)

    pdt.assert_frame_equal(transactions, original)
    assert len(featured) == len(transactions)
    assert all(column in featured.columns for column in FEATURE_COLUMNS)
    assert featured.dtypes["From Account"] == transactions.dtypes["From Account"]
    assert featured.dtypes["Amount Paid"] == transactions.dtypes["Amount Paid"]
