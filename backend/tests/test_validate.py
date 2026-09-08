import pandas as pd
import pandas.testing as pdt
import pytest

from app.tools.data_loader import load_transactions
from app.tools.features import FEATURE_COLUMNS
from validate import calculate_metrics, evaluate_transactions, get_ground_truth_labels


def test_calculate_metrics_reports_exact_confusion_matrix_and_scores():
    metrics = calculate_metrics(
        ground_truth=[1, 0, 0, 1, 0, 1],
        predictions=[1, 1, 0, 0, 0, 1],
    )

    assert metrics.true_positives == 2
    assert metrics.false_positives == 1
    assert metrics.true_negatives == 2
    assert metrics.false_negatives == 1
    assert metrics.total_rows == 6
    assert metrics.actual_positives == 3
    assert metrics.predicted_positives == 3
    assert metrics.precision == pytest.approx(2 / 3)
    assert metrics.recall == pytest.approx(2 / 3)
    assert metrics.f1_score == pytest.approx(2 / 3)


def test_synthetic_data_evaluates_through_existing_ml_pipeline_without_leakage():
    transactions = load_transactions("synthetic_transactions.csv")

    metrics = evaluate_transactions(transactions, contamination=0.1, random_state=7)

    assert metrics.total_rows == len(transactions)
    assert metrics.actual_positives == int(transactions["Is Laundering"].sum())
    assert 0.0 <= metrics.precision <= 1.0
    assert 0.0 <= metrics.recall <= 1.0
    assert 0.0 <= metrics.f1_score <= 1.0
    assert "Is Laundering" not in FEATURE_COLUMNS


def test_evaluation_is_deterministic_and_does_not_mutate_input():
    transactions = load_transactions("synthetic_transactions.csv").copy(deep=True)
    original = transactions.copy(deep=True)

    first = evaluate_transactions(transactions, contamination=0.1, random_state=11)
    second = evaluate_transactions(transactions, contamination=0.1, random_state=11)

    assert first == second
    pdt.assert_frame_equal(transactions, original)


def test_missing_ground_truth_column_raises_clear_value_error():
    transactions = pd.DataFrame({"Amount Paid": [10.0]})

    with pytest.raises(ValueError, match="missing ground-truth column"):
        get_ground_truth_labels(transactions)


def test_non_binary_ground_truth_labels_raise_clear_value_error():
    transactions = pd.DataFrame({"Is Laundering": [0, 2]})

    with pytest.raises(ValueError, match="binary 0/1"):
        get_ground_truth_labels(transactions)


def test_empty_transactions_raise_clear_value_error():
    transactions = pd.DataFrame({"Is Laundering": pd.Series(dtype="int64")})

    with pytest.raises(ValueError, match="empty"):
        get_ground_truth_labels(transactions)


def test_zero_predicted_positives_are_safe():
    metrics = calculate_metrics(ground_truth=[0, 1, 0], predictions=[0, 0, 0])

    assert metrics.predicted_positives == 0
    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1_score == 0.0
