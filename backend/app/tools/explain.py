"""Typology-tied natural-language reason generator per flag (Task 2.6).

Converts structured AML flags and evidence metrics into concise, evidence-grounded
explanations with explicit citations for supporting transaction IDs.
"""

from typing import Any, Dict, List, Union
from app.models.schemas import Flag, RiskTier


def explain_flag(flag: Union[Flag, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a typology-tied natural language explanation for a single AML flag.

    Parameters
    ----------
    flag : Union[Flag, Dict[str, Any]]
        Pydantic Flag model instance or equivalent dictionary.

    Returns
    -------
    Dict[str, Any]
        Structured explanation object containing summary, detailed explanation,
        cited transaction IDs, and associated flag metadata.
    """
    # Parse fields from Flag model or dict safely
    if isinstance(flag, Flag):
        flag_id = flag.flag_id
        rule_id = flag.rule_id
        rule_name = flag.rule_name
        severity = flag.severity.value if isinstance(flag.severity, RiskTier) else str(flag.severity)
        entity_id = flag.entity_id
        tx_ids = list(flag.transaction_ids) if flag.transaction_ids else []
        typology = flag.typology or "General AML Anomaly"
        reason = flag.reason
        evidence = dict(flag.evidence) if flag.evidence else {}
        timestamp = flag.timestamp.isoformat() if flag.timestamp else ""
    elif isinstance(flag, dict):
        flag_id = str(flag.get("flag_id", ""))
        rule_id = str(flag.get("rule_id", ""))
        rule_name = str(flag.get("rule_name", ""))
        sev = flag.get("severity", "HIGH")
        severity = sev.value if isinstance(sev, RiskTier) else str(sev)
        entity_id = flag.get("entity_id")
        tx_ids = list(flag.get("transaction_ids", []))
        typology = flag.get("typology") or "General AML Anomaly"
        reason = str(flag.get("reason", ""))
        evidence = dict(flag.get("evidence", {}))
        ts = flag.get("timestamp")
        timestamp = ts.isoformat() if hasattr(ts, "isoformat") else str(ts or "")
    else:
        raise ValueError("Flag must be a Pydantic Flag instance or a dictionary")

    # Format transaction citation clause
    citation_clause = _format_citation_clause(tx_ids)

    # Generate typology-specific narrative grounded in evidence
    summary, narrative = _build_typology_explanation(
        typology=typology,
        rule_name=rule_name,
        entity_id=entity_id,
        reason=reason,
        evidence=evidence,
        tx_ids=tx_ids,
        severity=severity,
    )

    full_explanation = f"{narrative} {citation_clause}".strip()

    return {
        "flag_id": flag_id,
        "rule_id": rule_id,
        "rule_name": rule_name,
        "typology": typology,
        "severity": severity,
        "entity_id": entity_id,
        "summary": summary,
        "explanation": full_explanation,
        "transaction_ids": tx_ids,
        "evidence": evidence,
        "timestamp": timestamp,
    }


def explain_flags(flags: List[Union[Flag, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Generate explanations for a batch of AML flags.

    Parameters
    ----------
    flags : List[Union[Flag, Dict[str, Any]]]
        List of Flag models or flag dictionaries.

    Returns
    -------
    List[Dict[str, Any]]
        List of structured explanation objects preserving order.
    """
    return [explain_flag(f) for f in flags]


def _format_citation_clause(tx_ids: List[str]) -> str:
    """Format explicit transaction ID citations."""
    if not tx_ids:
        return "Transaction-level evidence was not supplied."
    if len(tx_ids) == 1:
        return f"Evidence transaction: {tx_ids[0]}."
    if len(tx_ids) <= 5:
        joined = ", ".join(tx_ids)
        return f"Evidence transactions: {joined}."
    sample = ", ".join(tx_ids[:5])
    return f"Evidence transactions ({len(tx_ids)} total): {sample}, ..."


def _build_typology_explanation(
    typology: str,
    rule_name: str,
    entity_id: str | None,
    reason: str,
    evidence: Dict[str, Any],
    tx_ids: List[str],
    severity: str,
) -> tuple[str, str]:
    """Build summary and evidence-grounded narrative for specific typologies."""
    entity_str = f"account {entity_id}" if entity_id else "the involved entity"
    typology_key = typology.lower().replace("-", "_").replace(" ", "_")

    if "structuring" in typology_key:
        tx_count = evidence.get("tx_count")
        total_amt = evidence.get("total_amount")
        min_amt = evidence.get("min_tx_amount")
        max_amt = evidence.get("max_tx_amount")
        time_span = evidence.get("time_span_hours")
        role = evidence.get("role", "transactions")

        summary = f"Structuring evasion pattern detected for {entity_str}."

        details = []
        if tx_count:
            details.append(f"{tx_count} {str(role).lower()} transactions")
        if min_amt is not None and max_amt is not None:
            details.append(f"ranging from ${min_amt:,.2f} to ${max_amt:,.2f}")
        if total_amt is not None:
            details.append(f"totaling ${total_amt:,.2f}")
        if time_span is not None:
            details.append(f"within {time_span:.1f} hours")

        if details:
            narrative = (
                f"Structuring pattern detected for {entity_str}: "
                + " ".join(details)
                + ", indicating potential currency transaction reporting (CTR) evasion."
            )
        else:
            narrative = f"Structuring pattern detected for {entity_str}: {reason}"

        return summary, narrative

    elif "smurfing" in typology_key or "fan_in" in typology_key:
        distinct_senders = evidence.get("distinct_senders")
        total_amt = evidence.get("total_amount")
        time_span = evidence.get("time_span_hours")

        summary = f"Multi-source smurfing (fan-in) consolidation detected for {entity_str}."

        details = []
        if total_amt is not None:
            details.append(f"${total_amt:,.2f}")
        if distinct_senders:
            details.append(f"from {distinct_senders} distinct originating accounts")
        if time_span is not None:
            details.append(f"within {time_span:.1f} hours")

        if details:
            narrative = (
                f"Smurfing (fan-in) consolidation detected for {entity_str}: consolidated "
                + " ".join(details)
                + "."
            )
        else:
            narrative = f"Smurfing pattern detected for {entity_str}: {reason}"

        return summary, narrative

    elif "pass_through" in typology_key or "layering" in typology_key:
        in_amt = evidence.get("in_amount")
        out_amt = evidence.get("out_amount")
        ratio = evidence.get("pass_through_ratio")
        mins = evidence.get("time_delta_minutes")

        summary = f"Rapid pass-through conduit layering detected for {entity_str}."

        details = []
        if in_amt is not None:
            details.append(f"received ${in_amt:,.2f}")
        if out_amt is not None:
            details.append(f"transferred out ${out_amt:,.2f}")
        if ratio is not None:
            details.append(f"({ratio:.1%} turnover)")
        if mins is not None:
            details.append(f"within {mins:.1f} minutes")

        if details:
            narrative = (
                f"Rapid layering conduit activity detected for {entity_str}: "
                + " ".join(details)
                + ", indicating pass-through mule account behavior."
            )
        else:
            narrative = f"Rapid layering pattern detected for {entity_str}: {reason}"

        return summary, narrative

    elif "fan_out" in typology_key:
        distinct_recipients = evidence.get("distinct_recipients")
        total_amt = evidence.get("total_amount")
        time_span = evidence.get("time_span_hours")

        summary = f"High fan-out fund dispersion detected for {entity_str}."

        details = []
        if total_amt is not None:
            details.append(f"${total_amt:,.2f}")
        if distinct_recipients:
            details.append(f"across {distinct_recipients} distinct beneficiary accounts")
        if time_span is not None:
            details.append(f"within {time_span:.1f} hours")

        if details:
            narrative = (
                f"Fan-out dispersion detected for {entity_str}: dispersed "
                + " ".join(details)
                + "."
            )
        else:
            narrative = f"Fan-out dispersion pattern detected for {entity_str}: {reason}"

        return summary, narrative

    elif "velocity" in typology_key or "burst" in typology_key:
        tx_count = evidence.get("tx_count")
        total_amt = evidence.get("total_amount")
        mins = evidence.get("time_span_minutes")

        summary = f"High velocity transaction burst detected for {entity_str}."

        details = []
        if tx_count:
            details.append(f"{tx_count} transactions")
        if total_amt is not None:
            details.append(f"totaling ${total_amt:,.2f}")
        if mins is not None:
            details.append(f"within {mins:.1f} minutes")

        if details:
            narrative = (
                f"Velocity burst detected for {entity_str}: executed "
                + " ".join(details)
                + "."
            )
        else:
            narrative = f"Velocity burst detected for {entity_str}: {reason}"

        return summary, narrative

    else:
        # Safe generic fallback for unknown/novel typologies
        summary = f"AML flag triggered by {rule_name or 'detector rule'} for {entity_str}."
        reason_text = reason if reason else "Unusual activity observed matching detection criteria."
        narrative = f"Flag generated by rule '{rule_name or 'AML Rule'}' for {entity_str}. Severity: {severity}. Reason: {reason_text}"
        return summary, narrative
