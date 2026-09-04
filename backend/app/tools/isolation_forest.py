"""Unsupervised Isolation Forest anomaly detection for AML features."""

from typing import Final

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.tools.features import FEATURE_COLUMNS


ANOMALY_SCORE_COLUMN: Final = "anomaly_score"
IS_ANOMALY_COLUMN: Final = "is_anomaly"


def detect_anomalies(
    featured_transactions: pd.DataFrame,
    contamination: float = 0.05,
    random_state: int = 42,
) -> pd.DataFrame:
    """Score transactions with Isolation Forest using engineered AML features only.

    ``anomaly_score`` is the negated Isolation Forest decision score, so larger
    values indicate more anomalous transactions. ``is_anomaly`` is ``1`` for an
    Isolation Forest outlier and ``0`` otherwise.
    """
    _validate_feature_columns(featured_transactions)
    _validate_contamination(contamination)

    results = featured_transactions.copy(deep=True)
    if results.empty:
        results[ANOMALY_SCORE_COLUMN] = pd.Series(index=results.index, dtype="float64")
        results[IS_ANOMALY_COLUMN] = pd.Series(index=results.index, dtype="int64")
        return results

    model_input = _prepare_model_input(results)
    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(model_input)

    results[ANOMALY_SCORE_COLUMN] = -model.decision_function(model_input)
    results[IS_ANOMALY_COLUMN] = (model.predict(model_input) == -1).astype("int64")
    return results


def _validate_feature_columns(transactions: pd.DataFrame) -> None:
    missing_columns = [
        column for column in FEATURE_COLUMNS if column not in transactions.columns
    ]
    if missing_columns:
        raise ValueError(
            "Transaction DataFrame is missing engineered feature columns: "
            + ", ".join(missing_columns)
        )


def _validate_contamination(contamination: float) -> None:
    if not 0 < contamination <= 0.5:
        raise ValueError("contamination must be greater than 0 and at most 0.5")


def _prepare_model_input(transactions: pd.DataFrame) -> pd.DataFrame:
    try:
        model_input = transactions.loc[:, FEATURE_COLUMNS].apply(
            pd.to_numeric,
            errors="raise",
        )
    except (TypeError, ValueError) as error:
        raise ValueError("Engineered feature columns must be numeric") from error

    if not np.isfinite(model_input.to_numpy(dtype=float)).all():
        raise ValueError("Engineered feature columns must not contain NaN or infinite values")
    return model_input
