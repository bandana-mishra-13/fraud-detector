import pandas as pd

from app.data.sampler import _account_selected, build_sample


def _frame() -> pd.DataFrame:
    rows = [
        # a laundering pair — every row touching A1/A2 must survive sampling
        ("2022-09-01 10:00", "010", "A1", "020", "A2", 9500.0, 1),
        ("2022-09-02 11:00", "010", "A1", "030", "B7", 120.0, 0),
        ("2022-09-03 12:00", "040", "C3", "020", "A2", 45.0, 0),
        # clean-only accounts
        ("2022-09-04 13:00", "050", "D4", "060", "E5", 300.0, 0),
        ("2022-09-05 14:00", "060", "E5", "050", "D4", 310.0, 0),
        ("2022-09-06 15:00", "070", "F6", "080", "G7", 77.0, 0),
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "timestamp",
            "from_bank",
            "from_account",
            "to_bank",
            "to_account",
            "amount_paid",
            "is_laundering",
        ],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def test_account_selection_is_deterministic():
    for account in ("A1", "B7", "8000EBD30"):
        assert _account_selected(account, 0.5) == _account_selected(account, 0.5)


def test_fraction_bounds():
    assert not _account_selected("ANY", 0.0)
    assert _account_selected("ANY", 1.0)


def test_laundering_context_always_survives():
    sample = build_sample(_frame(), fraction=0.0)
    # rows touching laundering-involved accounts (A1, A2) survive even at 0%
    assert set(sample["from_account"]) | set(sample["to_account"]) >= {"A1", "A2"}
    assert (sample["is_laundering"] == 1).sum() == 1
    # fully clean accounts are gone at fraction 0
    assert "F6" not in set(sample["from_account"])


def test_sampling_is_reproducible():
    a = build_sample(_frame(), fraction=0.5)
    b = build_sample(_frame(), fraction=0.5)
    pd.testing.assert_frame_equal(a, b)


def test_full_fraction_keeps_everything():
    df = _frame()
    assert len(build_sample(df, fraction=1.0)) == len(df)
