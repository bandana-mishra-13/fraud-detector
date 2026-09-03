"""Deterministic sampling for normalized AML transaction data."""

from typing import Final

import pandas as pd


LAUNDERING_COLUMN: Final = "Is Laundering"
DEFAULT_RANDOM_STATE: Final = 42


def sample_transactions(
    transactions: pd.DataFrame,
    normal_sample_size: int,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> pd.DataFrame:
    """Keep all laundering rows and deterministically sample normal rows.

    The input DataFrame is never modified. The returned DataFrame has a fresh
    index while preserving the original transaction columns and dtypes.
    """
    if LAUNDERING_COLUMN not in transactions.columns:
        raise ValueError(f"Transaction DataFrame is missing '{LAUNDERING_COLUMN}'")
    if normal_sample_size < 0:
        raise ValueError("normal_sample_size must be non-negative")

    laundering_transactions = transactions.loc[
        transactions[LAUNDERING_COLUMN] == 1
    ]
    normal_transactions = transactions.loc[transactions[LAUNDERING_COLUMN] == 0]
    sample_size = min(normal_sample_size, len(normal_transactions))

    if sample_size == 0:
        sampled_normals = normal_transactions.iloc[0:0]
    elif sample_size == len(normal_transactions):
        sampled_normals = normal_transactions
    else:
        sampled_normals = normal_transactions.sample(
            n=sample_size,
            random_state=random_state,
        )

    return pd.concat([laundering_transactions, sampled_normals], ignore_index=True).copy()
