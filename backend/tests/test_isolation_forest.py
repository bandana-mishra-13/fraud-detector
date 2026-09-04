import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from app.tools import isolation_forest
from app.tools.data_loader import load_transactions
from app.tools.features import FEATURE_COLUMNS, engineer_features
from app.tools.isolation_forest import detect_anomalies


def _engineered_transactions(rows: int = 8) -> pd.DataFrame:
    data = {
        "Transaction ID": [f"tx-{index}" for index in range(rows)],
        "Timestamp": pd.date_range("2024-01-01", periods=rows, freq="h"),
        "From Account": ["sender"] * rows,
        "To Account": ["receiver"] * rows,
        "Is Laundering": [0] * rows,
    }
    for offset, feature_name in enumerate(FEATURE_COLUMNS, start=1):
        data[feature_name] = [float(offset + index) for index in range(rows)]
    return pd.DataFrame(data, index=range(100, 100 + rows))


def test_outputs_scores_and_flags_without_mutating_or_reordering_input():
    featured_transactions = _engineered_transactions()
    original = featured_transactions.copy(deep=True)

    results = detect_anomalies(featured_transactions, contamination=0.25)

    pdt.assert_frame_equal(featured_transactions, original)
    assert results.index.equals(featured_transactions.index)
    assert list(results.columns[: len(featured_transactions.columns)]) == list(
        featured_transactions.columns
    )
    assert pd.api.types.is_numeric_dtype(results["anomaly_score"])
    assert set(results["is_anomaly"]) <= {0, 1}


def test_required_feature_columns_are_validated():
    featured_transactions = _engineered_transactions().drop(
        columns="outbound_rolling_amount_sum"
    )

    with pytest.raises(ValueError, match="missing engineered feature columns"):
        detect_anomalies(featured_transactions)


def test_empty_featured_dataframe_returns_empty_anomaly_columns():
    empty_transactions = _engineered_transactions().iloc[0:0]

    results = detect_anomalies(empty_transactions)

    assert results.empty
    assert list(results.columns) == list(empty_transactions.columns) + [
        "anomaly_score",
        "is_anomaly",
    ]


def test_repeated_calls_with_same_random_state_are_deterministic():
    featured_transactions = _engineered_transactions()

    first = detect_anomalies(featured_transactions, contamination=0.25, random_state=7)
    second = detect_anomalies(featured_transactions, contamination=0.25, random_state=7)

    pdt.assert_frame_equal(first, second)


@pytest.mark.parametrize("contamination", [0.0, -0.1, 0.51])
def test_invalid_contamination_raises_clear_value_error(contamination):
    with pytest.raises(ValueError, match="contamination must be greater than 0"):
        detect_anomalies(_engineered_transactions(), contamination=contamination)


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf])
def test_non_finite_feature_values_are_rejected(invalid_value):
    featured_transactions = _engineered_transactions()
    featured_transactions.loc[100, "outbound_rolling_amount_sum"] = invalid_value

    with pytest.raises(ValueError, match="must not contain NaN or infinite values"):
        detect_anomalies(featured_transactions)


def test_model_input_contains_only_engineered_features_and_excludes_labels(monkeypatch):
    captured: dict[str, list[str]] = {}

    class RecordingIsolationForest:
        def __init__(self, **kwargs):
            captured["parameters"] = kwargs

        def fit(self, model_input):
            captured["columns"] = list(model_input.columns)
            return self

        def decision_function(self, model_input):
            return np.zeros(len(model_input))

        def predict(self, model_input):
            return np.ones(len(model_input), dtype=int)

    monkeypatch.setattr(isolation_forest, "IsolationForest", RecordingIsolationForest)

    results = isolation_forest.detect_anomalies(
        _engineered_transactions(),
        contamination=0.25,
        random_state=13,
    )

    assert captured["columns"] == list(FEATURE_COLUMNS)
    assert "Is Laundering" not in captured["columns"]
    assert "Timestamp" not in captured["columns"]
    assert captured["parameters"] == {"contamination": 0.25, "random_state": 13}
    assert results["is_anomaly"].eq(0).all()


def test_obvious_outlier_has_higher_anomaly_score():
    featured_transactions = _engineered_transactions(rows=11)
    for feature_name in FEATURE_COLUMNS:
        featured_transactions.loc[110, feature_name] = 1_000_000.0

    results = detect_anomalies(featured_transactions, contamination=0.1, random_state=42)

    outlier_score = results.loc[110, "anomaly_score"]
    typical_scores = results.drop(index=110)["anomaly_score"]
    assert outlier_score > typical_scores.max()
    assert results.loc[110, "is_anomaly"] == 1


def test_loader_feature_engineering_and_anomaly_detection_integrate():
    transactions = load_transactions("synthetic_transactions.csv")
    featured_transactions = engineer_features(transactions)

    results = detect_anomalies(featured_transactions, contamination=0.1)

    assert len(results) == len(transactions)
    assert "anomaly_score" in results.columns
    assert "is_anomaly" in results.columns
