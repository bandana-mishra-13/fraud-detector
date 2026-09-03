from pathlib import Path
from shutil import copyfile

import pandas as pd
import pytest

from app.core.config import settings
from app.tools import data_loader


SYNTHETIC_DATASET = Path(settings.DATA_DIR) / "synthetic_transactions.csv"


@pytest.fixture(autouse=True)
def clear_transaction_cache():
    data_loader._transaction_cache.clear()
    yield
    data_loader._transaction_cache.clear()


def test_loads_and_normalizes_synthetic_transactions():
    transactions = data_loader.load_transactions(SYNTHETIC_DATASET)

    assert tuple(transactions.columns) == data_loader.REQUIRED_TRANSACTION_COLUMNS
    assert len(transactions) == 19
    assert pd.api.types.is_datetime64_any_dtype(transactions["Timestamp"])
    assert pd.api.types.is_numeric_dtype(transactions["Amount Received"])
    assert pd.api.types.is_numeric_dtype(transactions["Amount Paid"])
    assert pd.api.types.is_integer_dtype(transactions["Is Laundering"])
    assert set(transactions["Is Laundering"]) <= {0, 1}

    for column in ("From Bank", "From Account", "To Bank", "To Account"):
        assert pd.api.types.is_string_dtype(transactions[column])
        assert all(isinstance(value, str) for value in transactions[column].dropna())


def test_loads_bare_synthetic_filename_from_data_directory():
    transactions = data_loader.load_transactions("synthetic_transactions.csv")

    assert len(transactions) == 19
    assert tuple(transactions.columns) == data_loader.REQUIRED_TRANSACTION_COLUMNS


def test_repeated_calls_for_the_same_path_use_the_cache(tmp_path, monkeypatch):
    cached_dataset = tmp_path / "transactions.csv"
    copyfile(SYNTHETIC_DATASET, cached_dataset)
    real_read_csv = data_loader.pd.read_csv
    read_csv_calls = 0

    def counting_read_csv(*args, **kwargs):
        nonlocal read_csv_calls
        read_csv_calls += 1
        return real_read_csv(*args, **kwargs)

    monkeypatch.setattr(data_loader.pd, "read_csv", counting_read_csv)

    first = data_loader.load_transactions(cached_dataset)
    second = data_loader.load_transactions(cached_dataset)

    assert first is second
    assert read_csv_calls == 1


def test_missing_file_raises_clear_error(tmp_path):
    missing_file = tmp_path / "missing_transactions.csv"

    with pytest.raises(FileNotFoundError, match="Transaction CSV not found"):
        data_loader.load_transactions(missing_file)


def test_normalizes_legacy_ibm_account_headers(tmp_path):
    legacy_dataset = tmp_path / "HI-Small_Trans.csv"
    legacy_dataset.write_text(
        "Timestamp,From Bank,Account,To Bank,Account,Amount Received,Receiving Currency,"
        "Amount Paid,Payment Currency,Payment Format,Is Laundering\n"
        "2022/09/01 00:20,010,ACC001,020,ACC002,2500.00,US Dollar,2500.00,"
        "US Dollar,Wire,0\n",
        encoding="utf-8",
    )

    transactions = data_loader.load_transactions(legacy_dataset)

    assert tuple(transactions.columns) == data_loader.REQUIRED_TRANSACTION_COLUMNS
    assert transactions.at[0, "From Account"] == "ACC001"
    assert transactions.at[0, "To Account"] == "ACC002"


def test_missing_required_column_raises_clear_error(tmp_path):
    incomplete_dataset = tmp_path / "incomplete_transactions.csv"
    pd.DataFrame({"Timestamp": ["2022/09/01 00:20"]}).to_csv(
        incomplete_dataset,
        index=False,
    )

    with pytest.raises(ValueError, match="missing required columns: From Bank"):
        data_loader.load_transactions(incomplete_dataset)
