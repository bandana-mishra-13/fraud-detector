"""Dataset loading with normalized columns and parquet caching.

First load parses the raw Kaggle CSVs (slow), then writes parquet caches to
`settings.cache_dir`; subsequent loads are near-instant. Caches invalidate
automatically when the source CSV is newer.
"""

import time
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..config import settings
from .sampler import build_sample

# The raw header has two columns literally named "Account"; we assign names
# positionally instead of trusting pandas' mangling.
TRANS_COLUMNS = [
    "timestamp",
    "from_bank",
    "from_account",
    "to_bank",
    "to_account",
    "amount_received",
    "receiving_currency",
    "amount_paid",
    "payment_currency",
    "payment_format",
    "is_laundering",
]

ACCOUNT_COLUMNS = ["bank_name", "bank_id", "account", "entity_id", "entity_name"]

# Bank ids carry leading zeros ("010") — they are identifiers, not numbers.
_TRANS_DTYPES = {
    "from_bank": "str",
    "from_account": "str",
    "to_bank": "str",
    "to_account": "str",
    "amount_received": "float64",
    "receiving_currency": "str",
    "amount_paid": "float64",
    "payment_currency": "str",
    "payment_format": "str",
    "is_laundering": "int8",
}


def _fresh(cache: Path, source: Path) -> bool:
    return cache.exists() and cache.stat().st_mtime >= source.stat().st_mtime


def _read_trans_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, header=0, names=TRANS_COLUMNS, dtype=_TRANS_DTYPES)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y/%m/%d %H:%M")
    for col in ("receiving_currency", "payment_currency", "payment_format"):
        df[col] = df[col].astype("category")
    return df


@lru_cache(maxsize=1)
def load_transactions() -> pd.DataFrame:
    """Full normalized transactions frame (parquet-cached)."""
    cache = settings.cache_dir / "trans_full.parquet"
    if _fresh(cache, settings.data_path):
        return pd.read_parquet(cache)
    df = _read_trans_csv(settings.data_path)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    return df


@lru_cache(maxsize=1)
def load_sample() -> pd.DataFrame:
    """Behaviour-preserving sample used by all analysis tools (parquet-cached)."""
    tag = int(settings.sample_account_fraction * 100)
    cache = settings.cache_dir / f"trans_sample_f{tag}.parquet"
    if _fresh(cache, settings.data_path):
        return pd.read_parquet(cache)
    sample = build_sample(load_transactions(), settings.sample_account_fraction)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    sample.to_parquet(cache, index=False)
    return sample


@lru_cache(maxsize=1)
def load_accounts() -> pd.DataFrame:
    """Account → bank / entity (customer) directory (parquet-cached)."""
    cache = settings.cache_dir / "accounts.parquet"
    if _fresh(cache, settings.accounts_path):
        return pd.read_parquet(cache)
    df = pd.read_csv(
        settings.accounts_path, header=0, names=ACCOUNT_COLUMNS, dtype="str"
    )
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    return df


def dataset_info() -> dict:
    """Summary the API exposes and the loader CLI prints."""
    full = load_transactions()
    sample = load_sample()
    accounts = load_accounts()
    return {
        "full_rows": int(len(full)),
        "sample_rows": int(len(sample)),
        "sample_fraction_of_accounts": settings.sample_account_fraction,
        "laundering_rows_full": int(full["is_laundering"].sum()),
        "laundering_rows_sample": int(sample["is_laundering"].sum()),
        "accounts": int(len(accounts)),
        "date_from": str(full["timestamp"].min()),
        "date_to": str(full["timestamp"].max()),
        "currencies": sorted(full["payment_currency"].cat.categories.tolist()),
        "payment_formats": sorted(full["payment_format"].cat.categories.tolist()),
    }


if __name__ == "__main__":
    t0 = time.time()
    info = dataset_info()
    for k, v in info.items():
        print(f"{k}: {v}")
    print(f"\nloaded in {time.time() - t0:.1f}s")
