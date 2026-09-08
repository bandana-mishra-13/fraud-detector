"""Evaluate the Isolation Forest AML detector against IBM ``Is Laundering`` labels.

Run from the backend directory:
    python validate.py
    python validate.py --dataset data/synthetic_transactions.csv

This validates the transaction-level ML detector only. Deterministic rule flags
are entity/group findings and do not have a stable row-level mapping when the
source CSV has no transaction identifier.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

from app.tools.data_loader import DEFAULT_DATASET_NAME, load_transactions
from app.tools.features import engineer_features
from app.tools.isolation_forest import IS_ANOMALY_COLUMN, detect_anomalies


GROUND_TRUTH_COLUMN = "Is Laundering"


@dataclass(frozen=True)
class ValidationMetrics:
    """Transaction-level detector metrics against IBM AML ground-truth labels."""

    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    total_rows: int
    actual_positives: int
    predicted_positives: int


def get_ground_truth_labels(transactions: pd.DataFrame) -> pd.Series:
    """Return validated binary IBM AML labels without changing the input frame."""
    if transactions.empty:
        raise ValueError("Transaction DataFrame is empty; no rows are available for validation")
    if GROUND_TRUTH_COLUMN not in transactions.columns:
        raise ValueError(
            f"Transaction DataFrame is missing ground-truth column '{GROUND_TRUTH_COLUMN}'"
        )

    labels = pd.to_numeric(transactions[GROUND_TRUTH_COLUMN], errors="coerce")
    if labels.isna().any() or not labels.isin([0, 1]).all():
        raise ValueError(f"{GROUND_TRUTH_COLUMN} must contain only binary 0/1 values")
    return labels.astype("int64")


def calculate_metrics(
    ground_truth: Sequence[int] | pd.Series | np.ndarray,
    predictions: Sequence[int] | pd.Series | np.ndarray,
) -> ValidationMetrics:
    """Calculate reproducible binary classification metrics using sklearn."""
    truth = _validate_binary_array(ground_truth, "Ground-truth labels")
    predicted = _validate_binary_array(predictions, "Predictions")
    if len(truth) == 0:
        raise ValueError("No rows are available for validation")
    if len(truth) != len(predicted):
        raise ValueError("Ground-truth labels and predictions must have the same length")

    true_negatives, false_positives, false_negatives, true_positives = (
        confusion_matrix(truth, predicted, labels=[0, 1]).ravel()
    )
    return ValidationMetrics(
        precision=float(precision_score(truth, predicted, zero_division=0)),
        recall=float(recall_score(truth, predicted, zero_division=0)),
        f1_score=float(f1_score(truth, predicted, zero_division=0)),
        true_positives=int(true_positives),
        false_positives=int(false_positives),
        true_negatives=int(true_negatives),
        false_negatives=int(false_negatives),
        total_rows=len(truth),
        actual_positives=int(truth.sum()),
        predicted_positives=int(predicted.sum()),
    )


def evaluate_transactions(
    transactions: pd.DataFrame,
    contamination: float = 0.05,
    random_state: int = 42,
) -> ValidationMetrics:
    """Evaluate existing feature engineering and Isolation Forest predictions.

    The label column is read only for final metric comparison. The detector
    receives engineered features exclusively through ``detect_anomalies``.
    """
    ground_truth = get_ground_truth_labels(transactions)
    featured_transactions = engineer_features(transactions)
    scored_transactions = detect_anomalies(
        featured_transactions,
        contamination=contamination,
        random_state=random_state,
    )
    if IS_ANOMALY_COLUMN not in scored_transactions.columns:
        raise ValueError(f"Detector output is missing '{IS_ANOMALY_COLUMN}'")

    return calculate_metrics(ground_truth, scored_transactions[IS_ANOMALY_COLUMN])


def evaluate_dataset(
    dataset: str | Path | None = None,
    contamination: float = 0.05,
    random_state: int = 42,
) -> ValidationMetrics:
    """Load a configured AML CSV and evaluate its transaction-level ML output."""
    return evaluate_transactions(
        load_transactions(dataset),
        contamination=contamination,
        random_state=random_state,
    )


def format_validation_report(metrics: ValidationMetrics, dataset: str | Path | None) -> str:
    """Return a concise, human-readable validation report."""
    dataset_name = str(dataset) if dataset is not None else DEFAULT_DATASET_NAME
    return "\n".join(
        [
            "Argus AML Validation (ML-only)",
            "-------------------------------",
            f"Dataset: {dataset_name}",
            f"Rows evaluated: {metrics.total_rows}",
            f"Ground-truth positives: {metrics.actual_positives}",
            f"Predicted positives: {metrics.predicted_positives}",
            "",
            "Confusion Matrix",
            f"TP: {metrics.true_positives}",
            f"FP: {metrics.false_positives}",
            f"TN: {metrics.true_negatives}",
            f"FN: {metrics.false_negatives}",
            "",
            "Metrics",
            f"Precision: {metrics.precision:.4f}",
            f"Recall:    {metrics.recall:.4f}",
            f"F1 Score:  {metrics.f1_score:.4f}",
        ]
    )


def _validate_binary_array(
    values: Sequence[int] | pd.Series | np.ndarray,
    name: str,
) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")

    numeric_values = pd.to_numeric(pd.Series(array), errors="coerce")
    if numeric_values.isna().any() or not numeric_values.isin([0, 1]).all():
        raise ValueError(f"{name} must contain only binary 0/1 values")
    return numeric_values.to_numpy(dtype="int64")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the Argus AML Isolation Forest against IBM AML labels.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="CSV path or filename. Defaults to the configured HI-Small_Trans.csv dataset.",
    )
    parser.add_argument(
        "--contamination",
        type=float,
        default=0.05,
        help="Isolation Forest contamination in (0, 0.5]. Default: 0.05.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Isolation Forest random seed. Default: 42.",
    )
    args = parser.parse_args()

    try:
        metrics = evaluate_dataset(
            dataset=args.dataset,
            contamination=args.contamination,
            random_state=args.random_state,
        )
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))

    print(format_validation_report(metrics, args.dataset))


if __name__ == "__main__":
    main()
