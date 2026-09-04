"""LLM-powered AML Result Synthesizer (Task 3.4).

Transforms raw deterministic tool outputs, execution plan context, and flag explanations
into an executive summary and key AML findings without altering risk scores or fabricating data.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from app.core.config import settings
from app.core.openrouter import chat_completion
from app.models.schemas import ExecutionPlan, RiskResult, SynthesizedResult


SYSTEM_PROMPT = """You are an AML Results Summarizer for compliance analysts and auditors.
Your ONLY role is to synthesize and summarize already-executed deterministic AML tool outputs and execution plans into an executive summary and key findings.

Strict Rules:
1. Do NOT make AML detection decisions, create new flags, or calculate risk scores.
2. Do NOT invent or alter transaction IDs, risk scores, risk tiers, entity IDs, or amounts.
3. Every key finding MUST correspond directly to supplied tool outputs (EDA, rule flags, ML scores, risk fusion, explanations).
4. Cite ONLY transaction IDs that are explicitly present in the supplied tool evidence.
5. Respect tools marked as SKIPPED: if a tool was skipped, state that it was skipped. Do NOT say "no anomalies found" for a tool that did not run.
6. Distinguish tools that ran with 0 findings from tools that were SKIPPED or FAILED.
7. Use professional, objective AML compliance language. Avoid legal guilt statements or proving crime.
8. Output ONLY a raw JSON object matching the required schema.

JSON Schema Format:
{
  "executive_summary": "High-level summary of analysis, executed workflow, and primary risk conclusions...",
  "key_findings": [
    "Bullet 1: Specific finding with cited transaction IDs...",
    "Bullet 2: Specific finding..."
  ],
  "cited_transaction_ids": ["TX101", "TX102"],
  "limitations": [
    "Note on skipped tools or execution caveats..."
  ]
}
"""


def _get_field(obj: Any, field_name: str, default: Any = None) -> Any:
    """Helper to safely retrieve a field from a dictionary or Pydantic model object."""
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


async def synthesize_results_async(
    execution_output: Dict[str, Any],
    query: Optional[str] = None,
) -> SynthesizedResult:
    """
    Asynchronously synthesize raw tool outputs and execution plan into an executive summary.

    Parameters
    ----------
    execution_output : Dict[str, Any]
        Dictionary returned by Plan Executor containing "plan" (ExecutionPlan) and "context" (dict).
    query : Optional[str]
        Original user query (optional override).

    Returns
    -------
    SynthesizedResult
        Pydantic model containing executive_summary, key_findings, cited_transaction_ids, limitations.
    """
    plan: Optional[ExecutionPlan] = execution_output.get("plan")
    context: Dict[str, Any] = execution_output.get("context", {})

    if not plan and "steps" in execution_output:
        plan = execution_output  # type: ignore

    # Extract all valid transaction IDs present in tool context for anti-hallucination validation
    valid_tx_ids = _extract_valid_tx_ids(context)

    # Format structured context payload for LLM prompt
    prompt_payload = _build_llm_prompt_payload(plan, context, query)

    if settings.OPENROUTER_API_KEY:
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Synthesize these AML investigation results:\n\n{json.dumps(prompt_payload, indent=2, default=str)}"},
            ]
            response_json = await chat_completion(messages=messages)
            choices = response_json.get("choices", [])
            if choices:
                raw_text = choices[0].get("message", {}).get("content", "")
                result = _validate_and_build_synthesis(raw_text, valid_tx_ids, plan, context)
                if result:
                    return result
        except Exception:
            pass

    # Deterministic fallback synthesis if OpenRouter API is unconfigured, offline, or fails
    return _deterministic_fallback_synthesis(plan, context, valid_tx_ids)


def synthesize_results(
    execution_output: Dict[str, Any],
    query: Optional[str] = None,
) -> SynthesizedResult:
    """Synchronous wrapper for synthesize_results_async."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(synthesize_results_async(execution_output, query))
    else:
        return asyncio.run(synthesize_results_async(execution_output, query))


def _extract_valid_tx_ids(context: Dict[str, Any]) -> Set[str]:
    """Extract set of all legitimate transaction IDs present in tool context."""
    valid: Set[str] = set()

    # From rule flags
    flags = context.get("rule_flags", [])
    for f in flags:
        tx_list = _get_field(f, "transaction_ids", [])
        if tx_list:
            valid.update(str(tx) for tx in tx_list)

    # From explanations
    exps = context.get("explanations", [])
    for exp in exps:
        tx_list = _get_field(exp, "transaction_ids", [])
        if tx_list:
            valid.update(str(tx) for tx in tx_list)

    # From raw transactions DataFrame
    raw_df = context.get("raw_transactions")
    if isinstance(raw_df, pd.DataFrame):
        for col in ("transaction_id", "Transaction ID"):
            if col in raw_df.columns:
                valid.update(raw_df[col].dropna().astype(str))

    return valid


def _build_llm_prompt_payload(
    plan: Optional[ExecutionPlan],
    context: Dict[str, Any],
    query: Optional[str],
) -> Dict[str, Any]:
    """Construct structured context payload for LLM synthesis prompt."""
    plan_info: Dict[str, Any] = {}
    if plan:
        plan_info = {
            "query": query or plan.query,
            "detected_intent": plan.detected_intent,
            "target_entities": plan.target_entities,
            "active_filters": plan.active_filters,
            "invoked_tools": plan.invoked_tools,
            "skipped_tools": [
                {"tool_name": _get_field(st, "tool_name"), "reason": _get_field(st, "reason")}
                for st in plan.skipped_tools
            ],
            "reasoning": plan.reasoning,
        }

    # Extract tool output summaries
    tool_summaries: Dict[str, Any] = {}

    if "eda_result" in context:
        eda = context["eda_result"]
        tool_summaries["eda"] = {
            "profile": _get_field(eda, "profile"),
            "volume_distribution": _get_field(eda, "volume_distribution"),
            "base_rates": _get_field(eda, "base_rates"),
        }

    if "rule_flags" in context:
        flags = context["rule_flags"]
        tool_summaries["rule_detectors"] = [
            {
                "rule_id": _get_field(f, "rule_id"),
                "rule_name": _get_field(f, "rule_name"),
                "severity": str(_get_field(f, "severity")),
                "entity_id": _get_field(f, "entity_id"),
                "typology": _get_field(f, "typology"),
                "reason": _get_field(f, "reason"),
                "transaction_ids": _get_field(f, "transaction_ids"),
            }
            for f in flags
        ]

    if "risk_result" in context:
        rr = context["risk_result"]
        if isinstance(rr, RiskResult):
            tool_summaries["risk_result"] = {
                "entity_id": rr.entity_id,
                "risk_score": rr.risk_score,
                "risk_tier": rr.risk_tier.value,
                "summary": rr.summary,
            }

    if "ml_scored_transactions" in context:
        ml_df = context["ml_scored_transactions"]
        if isinstance(ml_df, pd.DataFrame) and not ml_df.empty:
            anomaly_count = int(ml_df["is_anomaly"].sum()) if "is_anomaly" in ml_df.columns else 0
            max_score = float(ml_df["anomaly_score"].max()) if "anomaly_score" in ml_df.columns else None
            tool_summaries["detectors_ml"] = {
                "total_scored_transactions": len(ml_df),
                "anomalies_detected": anomaly_count,
                "max_anomaly_score": max_score,
            }

    if "explanations" in context:
        tool_summaries["explanations"] = context["explanations"]

    if "error" in context:
        tool_summaries["error"] = context["error"]

    return {
        "execution_plan": plan_info,
        "tool_summaries": tool_summaries,
    }


def _validate_and_build_synthesis(
    raw_text: str,
    valid_tx_ids: Set[str],
    plan: Optional[ExecutionPlan],
    context: Dict[str, Any],
) -> Optional[SynthesizedResult]:
    """Validate raw LLM JSON response and ground transaction ID citations."""
    try:
        json_str = raw_text.strip()
        if json_str.startswith("```"):
            json_str = re.sub(r"^```(?:json)?\n?", "", json_str)
            json_str = re.sub(r"\n?```$", "", json_str).strip()

        data = json.loads(json_str)

        summary = str(data.get("executive_summary", "")).strip()
        findings = [str(f) for f in data.get("key_findings", []) if f]
        raw_citations = [str(tx) for tx in data.get("cited_transaction_ids", []) if tx]
        limitations = [str(l) for l in data.get("limitations", []) if l]

        if not summary:
            return None

        # Filter transaction IDs against legitimate evidence to prevent LLM hallucinations
        grounded_citations = [tx for tx in raw_citations if not valid_tx_ids or tx in valid_tx_ids]

        return SynthesizedResult(
            executive_summary=summary,
            key_findings=findings,
            cited_transaction_ids=grounded_citations,
            limitations=limitations,
        )
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def _deterministic_fallback_synthesis(
    plan: Optional[ExecutionPlan],
    context: Dict[str, Any],
    valid_tx_ids: Set[str],
) -> SynthesizedResult:
    """
    Deterministic fallback synthesizer.
    Constructs executive summary and key findings using purely deterministic context fields.
    """
    intent = plan.detected_intent if plan else "broad_analysis"
    skipped = plan.skipped_tools if plan else []

    flags = context.get("rule_flags", [])
    risk_res: Optional[RiskResult] = context.get("risk_result")
    explanations = context.get("explanations", [])
    error = context.get("error")

    query_str = f"intent '{intent}'"
    if plan and plan.target_entities:
        query_str += f" for entity {', '.join(plan.target_entities)}"

    # Build Executive Summary
    if risk_res:
        entity_target = f"for entity {risk_res.entity_id}" if risk_res.entity_id else "across the dataset"
        summary = (
            f"AML investigation executed for {query_str}. "
            f"Risk assessment {entity_target} yielded a {risk_res.risk_tier.value} risk rating "
            f"with a composite risk score of {risk_res.risk_score:.4f}. "
            f"Total deterministic findings flagged: {len(flags)}."
        )
    elif flags:
        summary = (
            f"AML investigation executed for {query_str}. "
            f"Deterministic evaluation produced {len(flags)} flag(s) matching specified rules and thresholds."
        )
    else:
        summary = (
            f"AML investigation completed for {query_str}. "
            "No deterministic rule flags or suspicious anomalies were identified in the evaluated dataset."
        )

    # Build Key Findings
    findings: List[str] = []

    # Include explanations from explain.py if available
    if explanations:
        for exp in explanations[:10]:
            exp_text = _get_field(exp, "explanation") or _get_field(exp, "summary")
            if exp_text:
                findings.append(exp_text)
    elif flags:
        for f in flags[:10]:
            f_reason = _get_field(f, "reason")
            if f_reason:
                findings.append(f_reason)

    # Include ML anomaly summary if available
    ml_df = context.get("ml_scored_transactions")
    if isinstance(ml_df, pd.DataFrame) and not ml_df.empty:
        anomaly_count = int(ml_df["is_anomaly"].sum()) if "is_anomaly" in ml_df.columns else 0
        findings.append(
            f"ML Anomaly Detection: Scored {len(ml_df)} transactions and identified {anomaly_count} statistical anomaly instances."
        )

    # Include EDA volume highlight if available
    eda = context.get("eda_result")
    if eda and "profile" in eda:
        prof = eda["profile"]
        counts = prof.get("transaction_counts", {})
        vol = prof.get("volume", {})
        if counts.get("total_transactions"):
            findings.append(
                f"Dataset Baseline: Analyzed {counts.get('total_transactions')} transactions "
                f"totaling ${vol.get('total_amount', 0.0):,.2f}."
            )

    # Build Limitations / Caveats
    limitations: List[str] = []
    if skipped:
        for st in skipped:
            tool_name = _get_field(st, "tool_name")
            reason = _get_field(st, "reason")
            limitations.append(f"Tool '{tool_name}' was skipped: {reason}")

    if error:
        limitations.append(f"Execution caveat: Tool '{error.get('tool_name')}' failed during step {error.get('step_number')}: {error.get('message')}")

    cited_ids = sorted(list(valid_tx_ids))

    return SynthesizedResult(
        executive_summary=summary,
        key_findings=findings,
        cited_transaction_ids=cited_ids,
        limitations=limitations,
    )
