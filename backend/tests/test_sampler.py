import pandas as pd
import pandas.testing as pdt
import pytest

from app.tools.data_loader import load_transactions
from app.tools.sampler import sample_transactions


@pytest.fixture
def transactions() -> pd.DataFrame:
    return load_transactions("synthetic_transactions.csv")


def test_retains_all_laundering_rows_and_samples_requested_normals(transactions):
    sampled = sample_transactions(transactions, normal_sample_size=4)

    expected_laundering = transactions.loc[
        transactions["Is Laundering"] == 1
    ].reset_index(drop=True)
    sampled_laundering = sampled.loc[sampled["Is Laundering"] == 1].reset_index(drop=True)

    pdt.assert_frame_equal(sampled_laundering, expected_laundering)
    assert (sampled["Is Laundering"] == 0).sum() == 4
    assert len(sampled) == len(expected_laundering) + 4
    assert sampled.index.is_unique


def test_same_random_state_produces_identical_samples(transactions):
    first = sample_transactions(transactions, normal_sample_size=5, random_state=7)
    second = sample_transactions(transactions, normal_sample_size=5, random_state=7)

    pdt.assert_frame_equal(first, second)


def test_different_random_states_can_produce_different_normal_samples(transactions):
    first = sample_transactions(transactions, normal_sample_size=5, random_state=1)
    second = sample_transactions(transactions, normal_sample_size=5, random_state=2)

    first_normals = first.loc[first["Is Laundering"] == 0, "From Account"].sort_values()
    second_normals = second.loc[second["Is Laundering"] == 0, "From Account"].sort_values()

    assert not first_normals.reset_index(drop=True).equals(
        second_normals.reset_index(drop=True)
    )


def test_requesting_more_normals_than_available_returns_all_normals(transactions):
    sampled = sample_transactions(transactions, normal_sample_size=10_000)

    assert len(sampled) == len(transactions)
    assert (sampled["Is Laundering"] == 0).sum() == (
        transactions["Is Laundering"] == 0
    ).sum()


def test_zero_normal_sample_size_returns_only_laundering_rows(transactions):
    sampled = sample_transactions(transactions, normal_sample_size=0)

    assert len(sampled) == (transactions["Is Laundering"] == 1).sum()
    assert sampled["Is Laundering"].eq(1).all()


def test_negative_normal_sample_size_raises_value_error(transactions):
    with pytest.raises(ValueError, match="normal_sample_size must be non-negative"):
        sample_transactions(transactions, normal_sample_size=-1)


def test_missing_laundering_column_raises_value_error(transactions):
    without_label = transactions.drop(columns="Is Laundering")

    with pytest.raises(ValueError, match="missing 'Is Laundering'"):
        sample_transactions(without_label, normal_sample_size=2)


def test_input_columns_and_dtypes_are_preserved_without_mutation(transactions):
    original = transactions.copy(deep=True)

    sampled = sample_transactions(transactions, normal_sample_size=3)

    pdt.assert_frame_equal(transactions, original)
    assert sampled.columns.equals(transactions.columns)
    assert sampled.dtypes.equals(transactions.dtypes)
