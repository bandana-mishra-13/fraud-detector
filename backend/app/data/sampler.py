"""Deterministic, behaviour-preserving sampling of the transactions data.

Row-level random sampling would shred the per-account sequences that AML
features depend on (velocity, rolling sums, structuring bursts). So we sample
at the ACCOUNT level instead:

1. Every transaction touching a laundering-involved account is kept — the
   full context around every bad actor survives.
2. Of the remaining accounts, a deterministic fraction is selected by hashing
   the account id (stable across runs and machines — no RNG, no seed drift),
   and their FULL histories are kept.
"""

import hashlib

import pandas as pd


def _account_selected(account: str, fraction: float) -> bool:
    """Stable hash-based selection: same account → same answer, everywhere."""
    digest = hashlib.md5(account.encode()).hexdigest()[:8]
    return (int(digest, 16) % 10_000) < fraction * 10_000


def build_sample(df: pd.DataFrame, fraction: float) -> pd.DataFrame:
    """Return the behaviour-preserving sample of the full transactions frame."""
    laundering = df[df["is_laundering"] == 1]
    hot_accounts = set(laundering["from_account"]) | set(laundering["to_account"])

    unique_accounts = pd.unique(
        pd.concat([df["from_account"], df["to_account"]], ignore_index=True)
    )
    sampled_accounts = {
        a for a in unique_accounts if a not in hot_accounts and _account_selected(a, fraction)
    }
    keep = sampled_accounts | hot_accounts

    mask = df["from_account"].isin(keep) | df["to_account"].isin(keep)
    sample = df[mask].sort_values("timestamp").reset_index(drop=True)
    return sample
