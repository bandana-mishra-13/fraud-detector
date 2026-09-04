"""Deterministic AML detection & analytics tools package."""

from app.tools.data_loader import load_transactions
from app.tools.detectors import (
    detect_fan_out,
    detect_high_velocity,
    detect_rapid_layering,
    detect_smurfing,
    detect_structuring,
    run_rule_detectors,
)
from app.tools.eda import (
    get_base_rate_stats,
    get_eda_profile,
    get_top_counterparties,
    get_volume_distribution,
    run_eda,
)
from app.tools.explain import (
    explain_flag,
    explain_flags,
)
from app.tools.risk import (
    calculate_rule_score,
    determine_risk_tier,
    fuse_entity_risk,
    fuse_overall_risk,
    fuse_scores,
    fuse_transaction_risk,
)
from app.tools.sampler import sample_transactions

__all__ = [
    "load_transactions",
    "sample_transactions",
    "get_eda_profile",
    "get_volume_distribution",
    "get_base_rate_stats",
    "get_top_counterparties",
    "run_eda",
    "detect_structuring",
    "detect_smurfing",
    "detect_rapid_layering",
    "detect_fan_out",
    "detect_high_velocity",
    "run_rule_detectors",
    "calculate_rule_score",
    "determine_risk_tier",
    "fuse_scores",
    "fuse_entity_risk",
    "fuse_transaction_risk",
    "fuse_overall_risk",
    "explain_flag",
    "explain_flags",
]
