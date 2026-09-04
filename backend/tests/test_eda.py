import pandas as pd
import pytest

from app.tools.data_loader import load_transactions
from app.tools.eda import (
    get_base_rate_stats,
    get_eda_profile,
    get_top_counterparties,
    get_volume_distribution,
    run_eda,
)
from app.tools.sampler import sample_transactions


@pytest.fixture
def sample_eda_df():
    """Sample dataset matching IBM AML format."""
    return pd.DataFrame({
        "Timestamp": ["2022/09/01 00:20", "2022/09/01 01:15", "2022/09/01 02:30", "2022/09/01 03:45", "2022/09/01 04:10"],
        "From Bank": ["010", "020", "020", "030", "030"],
        "From Account": ["ACC001", "ACC002", "ACC002", "ACC003", "ACC003"],
        "To Bank": ["020", "030", "040", "040", "050"],
        "To Account": ["ACC002", "ACC003", "ACC004", "ACC004", "ACC005"],
        "Amount Received": [500.00, 2500.00, 7500.00, 15000.00, 60000.00],
        "Receiving Currency": ["US Dollar", "US Dollar", "US Dollar", "US Dollar", "US Dollar"],
        "Amount Paid": [500.00, 2500.00, 7500.00, 15000.00, 60000.00],
        "Payment Currency": ["US Dollar", "US Dollar", "US Dollar", "US Dollar", "US Dollar"],
        "Payment Format": ["Cash", "Wire", "ACH", "Wire", "Wire"],
        "Is Laundering": [0, 0, 0, 1, 1],
    })


# ============================================================================
# 1. Profiling Tests
# ============================================================================

def test_get_eda_profile(sample_eda_df):
    profile = get_eda_profile(sample_eda_df)
    assert profile["transaction_counts"]["total_transactions"] == 5
    assert profile["entity_cardinalities"]["unique_senders"] == 3
    assert profile["entity_cardinalities"]["unique_receivers"] == 4
    assert profile["volume"]["total_amount"] == 85500.00


# ============================================================================
# 2. Volume Distribution Tests
# ============================================================================

def test_get_volume_distribution(sample_eda_df):
    vol_dist = get_volume_distribution(sample_eda_df)
    assert vol_dist["count"] == 5
    assert vol_dist["min"] == 500.00
    assert vol_dist["max"] == 60000.00
    assert "percentiles" in vol_dist
    assert vol_dist["percentiles"]["p50"] == 7500.00

    buckets = vol_dist["buckets"]
    assert buckets["0-1k"]["count"] == 1
    assert buckets["1k-5k"]["count"] == 1
    assert buckets["5k-10k"]["count"] == 1
    assert buckets["10k-50k"]["count"] == 1
    assert buckets["50k+"]["count"] == 1


def test_get_volume_distribution_multi_currency():
    df = pd.DataFrame({
        "Amount Paid": [500.0, 2000.0, 1500.0],
        "Payment Currency": ["US Dollar", "US Dollar", "Euro"],
    })
    vol_dist = get_volume_distribution(df)
    assert vol_dist["is_multi_currency"] is True
    assert "US Dollar" in vol_dist["by_currency"]
    assert "Euro" in vol_dist["by_currency"]
    assert vol_dist["by_currency"]["US Dollar"]["count"] == 2
    assert vol_dist["by_currency"]["Euro"]["count"] == 1


def test_get_volume_distribution_empty():
    df = pd.DataFrame(columns=["Amount Paid", "Payment Currency"])
    vol_dist = get_volume_distribution(df)
    assert vol_dist["count"] == 0
    assert vol_dist["buckets"]["0-1k"]["count"] == 0


def test_get_volume_distribution_missing_cols():
    df = pd.DataFrame({"From Account": ["ACC01"]})
    with pytest.raises(ValueError, match="DataFrame missing required amount columns"):
        get_volume_distribution(df)


# ============================================================================
# 3. Base-Rate Statistics Tests
# ============================================================================

def test_get_base_rate_stats(sample_eda_df):
    rates = get_base_rate_stats(sample_eda_df)
    assert rates["is_available"] is True
    assert rates["total_labeled_transactions"] == 5
    assert rates["laundering_count"] == 2
    assert rates["normal_count"] == 3
    assert rates["laundering_rate_percent"] == 40.0
    assert rates["normal_rate_percent"] == 60.0


def test_get_base_rate_stats_missing_label():
    df = pd.DataFrame({"From Account": ["ACC01"]})
    rates = get_base_rate_stats(df)
    assert rates["is_available"] is False
    assert rates["laundering_count"] is None


# ============================================================================
# 4. Top Counterparties Tests
# ============================================================================

def test_get_top_counterparties(sample_eda_df):
    top = get_top_counterparties(sample_eda_df, top_n=2)
    assert top["top_n"] == 2
    assert len(top["top_senders_by_count"]) <= 2
    assert len(top["top_receivers_by_count"]) <= 2
    assert len(top["top_senders_by_volume"]) <= 2

    # Top sender by volume should be ACC003 ($15k + $60k = $75k)
    assert top["top_senders_by_volume"][0]["entity_id"] == "ACC003"
    assert top["top_senders_by_volume"][0]["total_volume"] == 75000.00


def test_get_top_counterparties_invalid_n(sample_eda_df):
    with pytest.raises(ValueError, match="top_n must be a positive integer"):
        get_top_counterparties(sample_eda_df, top_n=0)


def test_get_top_counterparties_missing_cols():
    df = pd.DataFrame({"Amount Paid": [100.0]})
    with pytest.raises(ValueError, match="DataFrame missing required entity columns"):
        get_top_counterparties(df)


# ============================================================================
# 5. Full EDA Execution & Non-Mutation Tests
# ============================================================================

def test_run_eda_full_contract(sample_eda_df):
    res = run_eda(sample_eda_df, top_n=5)
    assert "profile" in res
    assert "volume_distribution" in res
    assert "base_rates" in res
    assert "top_counterparties" in res

    assert res["profile"]["transaction_counts"]["total_transactions"] == 5
    assert res["volume_distribution"]["count"] == 5
    assert res["base_rates"]["laundering_count"] == 2
    assert res["top_counterparties"]["top_n"] == 5


def test_run_eda_non_mutating(sample_eda_df):
    df_copy = sample_eda_df.copy(deep=True)
    _ = run_eda(sample_eda_df)
    pd.testing.assert_frame_equal(sample_eda_df, df_copy)


# ============================================================================
# 6. Integration Test with Dev C's Loader & Sampler
# ============================================================================

def test_eda_integration_with_dev_c_loader_and_sampler():
    """Dev C loader -> Dev C sampler -> Dev A EDA tool pipeline integration."""
    full_df = load_transactions("synthetic_transactions.csv")
    assert len(full_df) > 0

    sampled_df = sample_transactions(full_df, normal_sample_size=10)
    assert len(sampled_df) > 0

    eda_output = run_eda(sampled_df, top_n=5)

    assert eda_output["profile"]["transaction_counts"]["total_transactions"] == len(sampled_df)
    assert eda_output["volume_distribution"]["count"] == len(sampled_df)
    assert eda_output["base_rates"]["is_available"] is True
    assert len(eda_output["top_counterparties"]["top_senders_by_count"]) > 0
