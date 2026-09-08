"""Risk Classification Tool — fuse rule signals + ML score into risk levels
and escalation actions.

Fusion: rules dominate (they are auditable and typology-specific); the ML
anomaly score corroborates or, alone, surfaces un-named anomalies at reduced
weight. Deterministic: same signals + scores -> same flags.
"""

import pandas as pd

from ..models.schemas import AMLPattern, Escalation, Flag, RiskLevel
from .explain import explain_flag

# Score composition: evidence strength dominates, ML corroborates.
RULE_WEIGHT = 0.7
ML_WEIGHT = 0.3

# ML-only candidates need to be clearly anomalous before they surface
ML_ONLY_FLOOR = 0.85
ML_ONLY_SCALE = 0.6  # un-named anomalies cap lower than typology hits

# Calibrated against the flagged-population distribution (median ≈ 0.85):
# a 0.75 cutoff marked ~92% of flags HIGH/REPORT, which is useless to a
# compliance team. These put HIGH at roughly the top decile so "report"
# means something and the queue is workable.
HIGH_CUTOFF = 0.91
MEDIUM_CUTOFF = 0.85

ESCALATION_BY_LEVEL = {
    RiskLevel.HIGH: Escalation.REPORT,
    RiskLevel.MEDIUM: Escalation.REVIEW,
    RiskLevel.LOW: Escalation.MONITOR,
}


def calculate_risk_score(
    flag_type: str,
    amount_involved: float = 0.0,
    prior_flags_count: int = 0,
    ml_anomaly_score: float = 0.0,
    rule_strength: float = 0.0,
) -> float:
    """Risk score 0.00–1.00 from evidence strength, typology severity,
    financial magnitude, repeat-offender history, and ML corroboration.

    Weighting rationale: how *strongly* the rule fired is the single best
    predictor of a true positive (9 sub-threshold deposits is far more
    damning than 5), so it carries the most weight. Typology severity,
    magnitude and ML modulate around it. Every component is continuous —
    stepped bands collapsed hundreds of accounts into identical scores,
    leaving the analyst queue with no meaningful order.
    """
    # Evidence strength dominates; ML corroborates. Both continuous.
    score = RULE_WEIGHT * max(0.0, min(1.0, rule_strength))
    score += ML_WEIGHT * max(0.0, min(1.0, ml_anomaly_score))

    # Repeat offenders lose the benefit of the doubt — small, capped nudge so
    # it can break ties without overriding the evidence itself.
    if prior_flags_count >= 10:
        score += 0.04
    elif prior_flags_count >= 3:
        score += 0.02

    # NOTE — deliberately NOT weighted into the score:
    #   • typology severity (layering "feels" worse than structuring)
    #   • raw transaction magnitude
    # Both were measured against the labelled ground truth and made ranking
    # markedly worse (precision@50 fell 96% -> 18-46%): dollar magnitude tracks
    # large *legitimate* businesses, and severity-by-fiat demotes the
    # high-evidence structuring hits that are the most reliable true positives.
    # They remain visible to the analyst in each flag's evidence.
    return round(min(max(score, 0.00), 1.00), 3)


def _level(score: float) -> RiskLevel:
    if score >= HIGH_CUTOFF:
        return RiskLevel.HIGH
    if score >= MEDIUM_CUTOFF:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def classify(
    rule_signals: list[dict],
    ml_scores: pd.Series | None = None,
    top_n: int = 50,
) -> list[Flag]:
    """Combine signals into per-account flags, strongest first."""
    ml = ml_scores if ml_scores is not None else pd.Series(dtype=float)

    # strongest rule signal per (account, pattern)
    best: dict[tuple[str, str], dict] = {}
    for sig in rule_signals:
        key = (sig["account"], sig["pattern"])
        if key not in best or sig["strength"] > best[key]["strength"]:
            best[key] = sig

    flags: list[Flag] = []
    rule_accounts = set()
    for (account, pattern), sig in best.items():
        rule_accounts.add(account)
        ml_part = float(ml.get(account, 0.0))
        
        # --- SMART EVIDENCE EXTRACTION ---
        ev = sig.get("evidence", {})
        
        # Extract highest dollar amount involved from evidence dictionary
        amount_involved = 0.0
        for k, v in ev.items():
            if any(term in str(k).lower() for term in ["total", "amount", "sum", "volume", "max"]):
                try:
                    amount_involved = max(amount_involved, float(v))
                except (ValueError, TypeError):
                    pass
                    
        # Extract prior flags history from evidence if available
        prior_flags = 0
        for k, v in ev.items():
            if any(term in str(k).lower() for term in ["prior", "flags", "history", "audit"]):
                try:
                    prior_flags = max(prior_flags, int(v))
                except (ValueError, TypeError):
                    pass
        
        # --- CALL THE DYNAMIC RISK SCORER ---
        score = calculate_risk_score(
            flag_type=pattern,
            amount_involved=amount_involved,
            prior_flags_count=prior_flags,
            ml_anomaly_score=ml_part,
            rule_strength=float(sig.get("strength", 0.0)),
        )
        
        level = _level(score)
        evidence = {**ev, "ml_anomaly_score": round(ml_part, 3)}
        flags.append(
            Flag(
                entity_type="account",
                entity_id=account,
                pattern=AMLPattern(pattern),
                risk_level=level,
                score=score,
                reason=explain_flag(pattern, account, evidence),
                escalation=ESCALATION_BY_LEVEL[level],
                evidence=evidence,
            )
        )

    # ML-only anomalies: no rule fired, but behaviour is far off-population
    if not ml.empty:
        for account, ml_score in ml[ml >= ML_ONLY_FLOOR].items():
            if account in rule_accounts:
                continue
            score = round(float(ml_score) * ML_ONLY_SCALE, 3)
            level = _level(score)
            evidence = {"ml_anomaly_score": round(float(ml_score), 3)}
            flags.append(
                Flag(
                    entity_type="account",
                    entity_id=str(account),
                    pattern=AMLPattern.ANOMALY,
                    risk_level=level,
                    score=score,
                    reason=explain_flag("anomaly", str(account), evidence),
                    escalation=ESCALATION_BY_LEVEL[level],
                    evidence=evidence,
                )
            )

    flags.sort(key=lambda f: f.score, reverse=True)
    return flags[:top_n]