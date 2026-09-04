import pandas as pd
import pytest

from app.tools.data_loader import load_transactions
from app.tools.sampler import sample_transactions
from app.utils.profiling import (
    get_base_profile,
    get_entity_cardinalities,
    get_transaction_counts,
    get_volume_summary,
)


@pytest.fixture
def sample_df():
    """Sample DataFrame matching IBM AML data schema."""
    return pd.DataFrame({
        "Timestamp": ["2022/09/01 00:20", "2022/09/01 01:15", "2022/09/01 02:30"],
        "From Bank": ["010", "020", "020"],
        "From Account": ["ACC001", "ACC002", "ACC002"],
        "To Bank": ["020", "030", "040"],
        "To Account": ["ACC002", "ACC003", "ACC004"],
        "Amount Received": [2500.00, 4800.00, 7200.00],
        "Receiving Currency": ["US Dollar", "US Dollar", "US Dollar"],
        "Amount Paid": [2500.00, 4800.00, 7200.00],
        "Payment Currency": ["US Dollar", "US Dollar", "US Dollar"],
        "Payment Format": ["Cash", "Wire", "ACH"],
        "Is Laundering": [0, 0, 1],
    })


# ============================================================================
# 1. Transaction Counts Tests
# ============================================================================

def test_transaction_counts_valid(sample_df):
    counts = get_transaction_counts(sample_df)
    assert counts["total_transactions"] == 3
    assert counts["laundering_transactions"] == 1
    assert counts["normal_transactions"] == 2
    assert counts["laundering_ratio"] == round(1 / 3, 6)


def test_transaction_counts_empty_df():
    empty_df = pd.DataFrame(columns=["Is Laundering"])
    counts = get_transaction_counts(empty_df)
    assert counts["total_transactions"] == 0
    assert counts["laundering_transactions"] == 0
    assert counts["normal_transactions"] == 0
    assert counts["laundering_ratio"] == 0.0


def test_transaction_counts_missing_label_col():
    df = pd.DataFrame({"From Account": ["ACC01", "ACC02"]})
    counts = get_transaction_counts(df)
    assert counts["total_transactions"] == 2
    assert counts["laundering_transactions"] is None
    assert counts["normal_transactions"] is None
    assert counts["laundering_ratio"] is None


# ============================================================================
# 2. Entity Cardinality Tests
# ============================================================================

def test_entity_cardinalities_valid(sample_df):
    card = get_entity_cardinalities(sample_df)
    # Senders: ACC001, ACC002 -> 2
    assert card["unique_senders"] == 2
    # Receivers: ACC002, ACC003, ACC004 -> 3
    assert card["unique_receivers"] == 3
    # Total unique: ACC001, ACC002, ACC003, ACC004 -> 4
    assert card["total_unique_entities"] == 4
    # Banks: 010, 020, 030, 040 -> 4
    assert card["unique_banks"] == 4


def test_entity_cardinalities_handles_nulls_and_empty():
    df = pd.DataFrame({
        "From Account": ["ACC01", "", None, "ACC02"],
        "To Account": ["ACC02", "ACC03", " ", None],
    })
    card = get_entity_cardinalities(df)
    assert card["unique_senders"] == 2  # ACC01, ACC02
    assert card["unique_receivers"] == 2  # ACC02, ACC03
    assert card["total_unique_entities"] == 3  # ACC01, ACC02, ACC03


def test_entity_cardinalities_missing_columns():
    df = pd.DataFrame({"Amount Paid": [100.0]})
    with pytest.raises(ValueError, match="DataFrame missing required entity columns"):
        get_entity_cardinalities(df)


# ============================================================================
# 3. Volume Summary Tests
# ============================================================================

def test_volume_summary_single_currency(sample_df):
    vol = get_volume_summary(sample_df)
    assert vol["is_multi_currency"] is False
    assert vol["currency"] == "US Dollar"
    assert vol["total_amount"] == 2500.00 + 4800.00 + 7200.00
    assert vol["mean_amount"] == round((2500.00 + 4800.00 + 7200.00) / 3, 2)
    assert vol["median_amount"] == 4800.00
    assert vol["min_amount"] == 2500.00
    assert vol["max_amount"] == 7200.00
    assert vol["count"] == 3


def test_volume_summary_multi_currency():
    df = pd.DataFrame({
        "Amount Paid": [1000.0, 2000.0, 500.0],
        "Payment Currency": ["US Dollar", "US Dollar", "Euro"],
    })
    vol = get_volume_summary(df)
    assert vol["is_multi_currency"] is True
    assert "US Dollar" in vol["by_currency"]
    assert "Euro" in vol["by_currency"]
    assert vol["by_currency"]["US Dollar"]["total_amount"] == 3000.0
    assert vol["by_currency"]["Euro"]["total_amount"] == 500.0


def test_volume_summary_empty_df():
    df = pd.DataFrame(columns=["Amount Paid", "Payment Currency"])
    vol = get_volume_summary(df)
    assert vol["total_amount"] == 0.0
    assert vol["count"] == 0
    assert vol["is_multi_currency"] is False


def test_volume_summary_missing_columns():
    df = pd.DataFrame({"From Account": ["ACC01"]})
    with pytest.raises(ValueError, match="DataFrame missing required amount columns"):
        get_volume_summary(df)


# ============================================================================
# 4. Base Profile Integration & Non-Mutation Tests
# ============================================================================

def test_get_base_profile_combines_sections(sample_df):
    profile = get_base_profile(sample_df)
    assert "transaction_counts" in profile
    assert "entity_cardinalities" in profile
    assert "volume" in profile

    assert profile["transaction_counts"]["total_transactions"] == 3
    assert profile["entity_cardinalities"]["total_unique_entities"] == 4
    assert profile["volume"]["total_amount"] == 14500.00


def test_profiling_does_not_mutate_input(sample_df):
    df_copy = sample_df.copy(deep=True)
    _ = get_base_profile(sample_df)
    pd.testing.assert_frame_equal(sample_df, df_copy)


# ============================================================================
# 5. Integration Test with Dev C's Loader & Sampler
# ============================================================================

def test_integration_with_dev_c_loader_and_sampler():
    """Verify end-to-end integration: Dev C loader -> Dev C sampler -> Dev A profiling."""
    full_df = load_transactions("synthetic_transactions.csv")
    assert len(full_df) > 0

    sampled_df = sample_transactions(full_df, normal_sample_size=5)
    assert len(sampled_df) > 0

    profile = get_base_profile(sampled_df)

    assert profile["transaction_counts"]["total_transactions"] == len(sampled_df)
    assert profile["transaction_counts"]["laundering_transactions"] > 0
    assert profile["entity_cardinalities"]["total_unique_entities"] > 0
    assert profile["volume"]["total_amount"] > 0.0
