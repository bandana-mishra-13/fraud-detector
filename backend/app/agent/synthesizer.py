"""Synthesizer: LLM writes the analyst-facing summary of a completed run.

Garnish, not substance — flags and plan are already final and deterministic.
If the LLM is unavailable the summary falls back to a template and the error
is surfaced in the response so the operator knows.
"""

from ..models.schemas import RiskResult
from .llm import LLMError, chat

SYSTEM_PROMPT = """You are the reporting layer of Argus, an AML analysis agent.
Write a concise analyst summary (3-5 sentences) of a completed analysis run.
Tie it to the user's original question. Mention: what was analysed (scope),
which tools were skipped and why that was appropriate, the headline findings
(counts, dominant patterns), and the recommended next action. Plain prose,
no markdown, no bullet lists. Never invent numbers not present in the data."""


def _template_summary(result: RiskResult) -> str:
    k = result.kpis
    skipped = [s.tool for s in result.plan.steps if s.action == "skipped"]
    parts = [
        f"Scanned {k.get('transactions_scanned', 0):,} transactions for intent "
        f"'{result.plan.intent}'.",
        f"Raised {k.get('flags_raised', 0)} flags "
        f"({k.get('high_risk', 0)} high risk).",
    ]
    if "aggregation_matches" in k:
        parts.append(f"Aggregation matched {k['aggregation_matches']} entities.")
    if skipped:
        parts.append(f"Tools skipped as unnecessary: {', '.join(skipped)}.")
    return " ".join(parts)


def synthesize(result: RiskResult) -> tuple[str, str | None]:
    """Return (summary, llm_error_or_None)."""
    top = [
        {
            "entity": f.entity_id,
            "pattern": f.pattern.value,
            "risk": f.risk_level.value,
            "score": f.score,
            "reason": f.reason,
        }
        for f in result.flags[:5]
    ]
    context = {
        "query": result.plan.query,
        "intent": result.plan.intent,
        "invoked": [
            {"tool": s.tool, "reason": s.reason}
            for s in result.plan.steps
            if s.action == "invoked"
        ],
        "skipped": [
            {"tool": s.tool, "reason": s.reason}
            for s in result.plan.steps
            if s.action == "skipped"
        ],
        "kpis": result.kpis,
        "top_flags": top,
        "aggregation_sample": (result.charts.get("aggregation_table") or [])[:5],
        "prior_flags": (result.charts.get("prior_flags") or [])[:5],
    }
    try:
        summary = chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": str(context)},
            ],
            temperature=0.3,
        )
        return summary, None
    except LLMError as exc:
        return _template_summary(result), str(exc)
