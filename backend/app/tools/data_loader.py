"""Load and normalize AML transaction data for analytics tools."""

from pathlib import Path
from typing import Final

import pandas as pd

from app.core.config import settings


DEFAULT_DATASET_NAME: Final = "HI-Small_Trans.csv"
REQUIRED_TRANSACTION_COLUMNS: Final = (
    "Timestamp",
    "From Bank",
    "From Account",
    "To Bank",
    "To Account",
    "Amount Received",
    "Receiving Currency",
    "Amount Paid",
    "Payment Currency",
    "Payment Format",
    "Is Laundering",
)
STRING_COLUMNS: Final = (
    "From Bank",
    "From Account",
    "To Bank",
    "To Account",
    "Receiving Currency",
    "Payment Currency",
    "Payment Format",
)

_transaction_cache: dict[Path, pd.DataFrame] = {}


def load_transactions(path: str | Path | None = None) -> pd.DataFrame:
    """Load, validate, and normalize an AML transaction CSV.

    When no path is provided, the local IBM AML dataset is loaded from
    ``settings.DATA_DIR``. Pass ``synthetic_transactions.csv`` explicitly for
    the small, version-controlled test dataset. Returned DataFrames are cached
    by resolved path and should be treated as read-only by callers.
    """
    csv_path = _resolve_csv_path(path)

    if csv_path in _transaction_cache:
        return _transaction_cache[csv_path]

    if not csv_path.is_file():
        raise FileNotFoundError(f"Transaction CSV not found: {csv_path}")

    transactions = pd.read_csv(csv_path, dtype="string")
    _normalize_legacy_account_columns(transactions)
    _validate_required_columns(transactions, csv_path)
    _normalize_column_types(transactions)

    _transaction_cache[csv_path] = transactions
    return transactions


def _resolve_csv_path(path: str | Path | None) -> Path:
    if path is None:
        path = Path(settings.DATA_DIR) / DEFAULT_DATASET_NAME

    csv_path = Path(path).expanduser()
    if not csv_path.is_absolute() and csv_path.parent == Path("."):
        csv_path = Path(settings.DATA_DIR) / csv_path

    return csv_path.resolve()


def _normalize_legacy_account_columns(transactions: pd.DataFrame) -> None:
    """Map IBM's duplicate Account headers to the canonical account names."""
    columns = list(transactions.columns)

    if "From Account" not in columns and "Account" in columns:
        columns[columns.index("Account")] = "From Account"

    if "To Account" not in columns:
        for legacy_column in ("Account.1", "Account_1"):
            if legacy_column in columns:
                columns[columns.index(legacy_column)] = "To Account"
                break

    transactions.columns = columns


def _validate_required_columns(transactions: pd.DataFrame, csv_path: Path) -> None:
    missing_columns = [
        column for column in REQUIRED_TRANSACTION_COLUMNS if column not in transactions.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(
            f"Transaction CSV is missing required columns: {missing} ({csv_path})"
        )


def _normalize_column_types(transactions: pd.DataFrame) -> None:
    transactions["Timestamp"] = pd.to_datetime(transactions["Timestamp"], errors="raise")

    for column in STRING_COLUMNS:
        transactions[column] = transactions[column].astype("string")

    for column in ("Amount Received", "Amount Paid"):
        transactions[column] = pd.to_numeric(transactions[column], errors="raise")

    laundering = pd.to_numeric(transactions["Is Laundering"], errors="raise")
    if not laundering.isin([0, 1]).all():
        raise ValueError("Is Laundering must contain only 0 or 1")
    transactions["Is Laundering"] = laundering.astype("int64")
