"""Hybrid Risk Fusion Engine (Task 2.5).

Combines deterministic AML rule flags and machine learning anomaly scores into
a unified, explainable risk score and categorical risk tier.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from app.models.schemas import Flag, RiskResult, RiskTier

# Severity weighting coefficients
SEVERITY_WEIGHTS: Dict[RiskTier, float] = {
    RiskTier.CRITICAL: 0.40,
    RiskTier.HIGH: 0.25,
    RiskTier.MEDIUM: 0.15,
    RiskTier.LOW: 0.05,
}

# Rule vs ML fusion weights when ML score is present
RULE_FUSION_WEIGHT: float = 0.65
ML_FUSION_WEIGHT: float = 0.35


def calculate_rule_score(flags: List[Flag]) -> float:
    """Calculate normalized rule score [0.0, 1.0] from a collection of AML flags.

    Uses a probabilistic saturation formula (1 - prod(1 - w_i)) ensuring smooth
    diminishing returns and strict bounded range [0.0, 1.0].
    """
    if not flags:
        return 0.0

    unmitigated_product = 1.0
    for flag in flags:
        severity = flag.severity
        if isinstance(severity, str):
            try:
                severity = RiskTier(severity.upper())
            except ValueError:
                severity = RiskTier.MEDIUM

        weight = SEVERITY_WEIGHTS.get(severity, 0.15)
        unmitigated_product *= (1.0 - weight)

    raw_score = 1.0 - unmitigated_product
    return round(min(1.0, max(0.0, raw_score)), 4)


def determine_risk_tier(
    risk_score: float,
    flags: Optional[List[Flag]] = None,
) -> RiskTier:
    """Determine categorical risk tier based on continuous risk score and critical triggers."""
    # Critical rule breach override
    if flags:
        for flag in flags:
            sev = flag.severity
            if (isinstance(sev, RiskTier) and sev == RiskTier.CRITICAL) or (
                isinstance(sev, str) and sev.upper() == "CRITICAL"
            ):
                return RiskTier.CRITICAL

    if risk_score >= 0.75:
        return RiskTier.CRITICAL
    elif risk_score >= 0.50:
        return RiskTier.HIGH
    elif risk_score >= 0.25:
        return RiskTier.MEDIUM
    else:
        return RiskTier.LOW


def fuse_scores(
    rule_score: float,
    ml_score: Optional[float] = None,
) -> float:
    """Combine rule score and ML anomaly score into a unified score in [0.0, 1.0]."""
    clamped_rule = min(1.0, max(0.0, rule_score))

    if ml_score is None:
        return clamped_rule

    clamped_ml = min(1.0, max(0.0, ml_score))
    fused = (RULE_FUSION_WEIGHT * clamped_rule) + (ML_FUSION_WEIGHT * clamped_ml)

    # If rules indicate critical/high risk, ensure fused score does not under-represent rule severity
    if clamped_rule >= 0.70:
        fused = max(fused, clamped_rule)

    return round(min(1.0, max(0.0, fused)), 4)


def generate_risk_summary(
    subject: str,
    risk_tier: RiskTier,
    risk_score: float,
    flags: List[Flag],
    ml_score: Optional[float] = None,
) -> str:
    """Generate human-readable compliance risk summary narrative."""
    typologies = list({f.typology for f in flags if f.typology})
    typology_text = f" ({', '.join(typologies)})" if typologies else ""

    ml_note = ""
    if ml_score is not None:
        ml_level = "elevated" if ml_score >= 0.6 else "nominal"
        ml_note = f" Isolation Forest ML anomaly score evaluated at {ml_score:.2f} ({ml_level})."

    if not flags:
        if ml_score is not None and ml_score >= 0.60:
            return (
                f"{subject} exhibits an anomalous transaction profile (ML score: {ml_score:.2f}) "
                f"with overall {risk_tier.value} risk ({risk_score:.2f}), though no deterministic AML rules were triggered."
            )
        return f"{subject} demonstrates low risk ({risk_score:.2f}) with no suspicious AML rule flags detected."

    flag_count = len(flags)
    plural = "flag" if flag_count == 1 else "flags"

    return (
        f"{subject} evaluated at {risk_tier.value} risk (score: {risk_score:.2f}) with "
        f"{flag_count} triggered AML detection {plural}{typology_text}.{ml_note} "
        f"Primary finding: {flags[0].reason}"
    )


def fuse_entity_risk(
    entity_id: str,
    flags: List[Flag],
    ml_score: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> RiskResult:
    """Generate fused risk assessment for an individual account or financial entity."""
    entity_flags = [f for f in flags if f.entity_id == entity_id] if flags else []
    # If flags passed were already filtered to entity
    if not entity_flags and flags and all(f.entity_id == entity_id or f.entity_id is None for f in flags):
        entity_flags = flags

    rule_score = calculate_rule_score(entity_flags)
    fused_score = fuse_scores(rule_score=rule_score, ml_score=ml_score)
    risk_tier = determine_risk_tier(fused_score, entity_flags)

    summary = generate_risk_summary(
        subject=f"Account {entity_id}",
        risk_tier=risk_tier,
        risk_score=fused_score,
        flags=entity_flags,
        ml_score=ml_score,
    )

    evidence_summary: Dict[str, Any] = {
        "entity_id": entity_id,
        "total_flags": len(entity_flags),
        "rule_score": rule_score,
        "ml_score": ml_score,
        "fused_risk_score": fused_score,
        "typologies_detected": list({f.typology for f in entity_flags if f.typology}),
    }
    if metadata:
        evidence_summary.update(metadata)

    return RiskResult(
        result_id=str(uuid.uuid4()),
        entity_id=entity_id,
        transaction_id=None,
        risk_score=fused_score,
        risk_tier=risk_tier,
        flags=entity_flags,
        rule_score=rule_score,
        ml_score=ml_score,
        summary=summary,
        evidence_summary=evidence_summary,
        created_at=datetime.now(timezone.utc),
    )


def fuse_transaction_risk(
    transaction_id: str,
    flags: List[Flag],
    ml_score: Optional[float] = None,
    entity_id: Optional[str] = None,
) -> RiskResult:
    """Generate fused risk assessment for an individual transaction."""
    tx_flags = [
        f for f in flags if transaction_id in f.transaction_ids
    ] if flags else []

    rule_score = calculate_rule_score(tx_flags)
    fused_score = fuse_scores(rule_score=rule_score, ml_score=ml_score)
    risk_tier = determine_risk_tier(fused_score, tx_flags)

    summary = generate_risk_summary(
        subject=f"Transaction {transaction_id}",
        risk_tier=risk_tier,
        risk_score=fused_score,
        flags=tx_flags,
        ml_score=ml_score,
    )

    evidence_summary = {
        "transaction_id": transaction_id,
        "entity_id": entity_id,
        "total_flags": len(tx_flags),
        "rule_score": rule_score,
        "ml_score": ml_score,
        "fused_risk_score": fused_score,
    }

    return RiskResult(
        result_id=str(uuid.uuid4()),
        entity_id=entity_id,
        transaction_id=transaction_id,
        risk_score=fused_score,
        risk_tier=risk_tier,
        flags=tx_flags,
        rule_score=rule_score,
        ml_score=ml_score,
        summary=summary,
        evidence_summary=evidence_summary,
        created_at=datetime.now(timezone.utc),
    )


def fuse_overall_risk(
    flags: List[Flag],
    ml_score: Optional[float] = None,
    total_transactions: Optional[int] = None,
    total_entities: Optional[int] = None,
) -> RiskResult:
    """Generate aggregated dataset-level or batch investigation risk result."""
    rule_score = calculate_rule_score(flags)
    fused_score = fuse_scores(rule_score=rule_score, ml_score=ml_score)
    risk_tier = determine_risk_tier(fused_score, flags)

    summary = generate_risk_summary(
        subject="Investigation dataset sample",
        risk_tier=risk_tier,
        risk_score=fused_score,
        flags=flags,
        ml_score=ml_score,
    )

    evidence_summary = {
        "total_flags": len(flags),
        "total_transactions": total_transactions,
        "total_entities": total_entities,
        "rule_score": rule_score,
        "ml_score": ml_score,
        "fused_risk_score": fused_score,
        "flagged_typologies": list({f.typology for f in flags if f.typology}),
    }

    return RiskResult(
        result_id=str(uuid.uuid4()),
        entity_id=None,
        transaction_id=None,
        risk_score=fused_score,
        risk_tier=risk_tier,
        flags=flags,
        rule_score=rule_score,
        ml_score=ml_score,
        summary=summary,
        evidence_summary=evidence_summary,
        created_at=datetime.now(timezone.utc),
    )
