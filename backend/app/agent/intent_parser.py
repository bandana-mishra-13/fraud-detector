"""LLM-powered Natural Language AML Query Intent Parser (Task 3.1).

Parses natural language user queries into structured, validated intent contracts:
{intent, filters, entities, pattern, time_window}

Does NOT execute tools, compute risk scores, or determine if entities are suspicious.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.openrouter import chat_completion
from app.models.schemas import IntentType, ParsedIntent, TimeWindowSpec


SYSTEM_PROMPT = """You are an AML Query Intent Parser. Your ONLY job is to parse a natural language AML query into a structured JSON object representing the user's intent.

Strict Rules:
1. Do NOT perform AML analysis or evaluate whether activity is suspicious.
2. Do NOT calculate risk scores, risk tiers, or generate flags.
3. Do NOT execute any tools or databases.
4. Do NOT invent entities, amounts, patterns, or time windows not present in the user query.
5. If the user asks about a specific entity (e.g., "customer 4521", "account ACC015"), extract the entity ID into "entities".
6. If the user asks for a specific AML pattern (e.g., "structuring", "smurfing", "rapid_layering", "fan_out", "velocity"), extract it into "pattern".
7. If the user specifies numeric thresholds (e.g. "10+ transactions", "under $10,000"), extract them into "filters" as "min_transaction_count", "max_transaction_amount", "min_transaction_amount", etc.
8. If the user specifies temporal limits (e.g. "last 30 days", "past week"), extract it into "time_window" with fields "type", "value", "unit", "raw_text".
9. Categorize "intent" into exactly one of: "broad_analysis", "pattern_detection", "aggregation", "entity_investigation", "unsupported".
10. Return ONLY a raw JSON object matching the required schema.

JSON Schema Output Format:
{
  "intent": "broad_analysis | pattern_detection | aggregation | entity_investigation | unsupported",
  "filters": {},
  "entities": [],
  "pattern": "structuring | smurfing | rapid_layering | fan_out | velocity | null",
  "time_window": {
    "type": "relative | absolute | range | null",
    "value": 30,
    "unit": "days | hours | weeks | months | null",
    "raw_text": "last 30 days"
  }
}
"""


async def parse_intent_async(query: str) -> ParsedIntent:
    """
    Asynchronously parse a natural language user query into a validated ParsedIntent.

    Args:
        query: Raw natural language AML query string.

    Returns:
        ParsedIntent: Validated Pydantic model with intent, filters, entities, pattern, time_window.
    """
    clean_query = query.strip() if query else ""
    if not clean_query:
        raise ValueError("Query cannot be empty")

    # If OpenRouter API key is configured, attempt LLM parsing
    if settings.OPENROUTER_API_KEY:
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Parse this user query:\n\n{clean_query}"},
            ]
            response_json = await chat_completion(messages=messages)
            choices = response_json.get("choices", [])
            if choices:
                raw_text = choices[0].get("message", {}).get("content", "")
                parsed = _validate_and_build_intent(clean_query, raw_text)
                if parsed:
                    return parsed
        except Exception:
            # Fall back to deterministic parsing if OpenRouter fails or times out
            pass

    # Deterministic fallback parsing (used if API key unconfigured, offline, or fallback required)
    return _deterministic_fallback_parse(clean_query)


def parse_intent(query: str) -> ParsedIntent:
    """
    Synchronous wrapper for parse_intent_async.

    Args:
        query: Raw natural language AML query string.

    Returns:
        ParsedIntent: Validated Pydantic model.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Running inside an active event loop
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(parse_intent_async(query))
    else:
        return asyncio.run(parse_intent_async(query))


def _validate_and_build_intent(query: str, raw_text: str) -> Optional[ParsedIntent]:
    """Extract and validate JSON from raw LLM text output into a ParsedIntent model."""
    try:
        # Clean markdown code blocks if present
        json_str = raw_text.strip()
        if json_str.startswith("```"):
            json_str = re.sub(r"^```(?:json)?\n?", "", json_str)
            json_str = re.sub(r"\n?```$", "", json_str).strip()

        data = json.loads(json_str)

        intent_raw = str(data.get("intent", "unsupported")).lower()
        try:
            intent_enum = IntentType(intent_raw)
        except ValueError:
            intent_enum = IntentType.UNSUPPORTED

        filters = data.get("filters") if isinstance(data.get("filters"), dict) else {}
        entities = [str(e) for e in data.get("entities", []) if e is not None]
        pattern = data.get("pattern")
        if pattern:
            pattern = str(pattern).lower()

        tw_data = data.get("time_window")
        time_window = None
        if isinstance(tw_data, dict) and any(tw_data.values()):
            time_window = TimeWindowSpec(
                type=tw_data.get("type"),
                value=tw_data.get("value"),
                unit=tw_data.get("unit"),
                start_date=tw_data.get("start_date"),
                end_date=tw_data.get("end_date"),
                raw_text=tw_data.get("raw_text"),
            )

        return ParsedIntent(
            query=query,
            intent=intent_enum,
            filters=filters,
            entities=entities,
            pattern=pattern,
            time_window=time_window,
            raw_llm_response=raw_text,
        )
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def _deterministic_fallback_parse(query: str) -> ParsedIntent:
    """
    Deterministic rule-based fallback parser for AML queries.
    Used when LLM service is offline or unconfigured, ensuring reliable testing and operation.
    """
    q_lower = query.lower().strip()
    reserved_words = {
        "made", "with", "who", "which", "in", "for", "under", "over", "above", "below",
        "have", "has", "is", "are", "instructions", "rules", "rule", "all", "the", "ignore"
    }

    # Check for prompt injection keywords attempting to hijack output
    if "ignore" in q_lower and ("risk score" in q_lower or "instructions" in q_lower):
        matches = re.findall(r"\b(?:customer|account|entity)\s+([A-Za-z0-9_-]+)\b", query, re.IGNORECASE)
        valid_entities = [m for m in matches if m.lower() not in reserved_words]
        return ParsedIntent(
            query=query,
            intent=IntentType.ENTITY_INVESTIGATION if valid_entities else IntentType.UNSUPPORTED,
            filters={},
            entities=valid_entities,
            pattern=None,
            time_window=None,
            raw_llm_response="[Fallback] Prompt injection attempt neutralized.",
        )

    # Check for aggregation query first (e.g. "Which customers made 10+ transactions under $10,000?")
    count_match = re.search(r"(\d+)\+?\s*transactions", q_lower)
    amount_under = re.search(r"under\s*\$?([\d,]+)", q_lower)
    amount_over = re.search(r"(?:over|above)\s*\$?([\d,]+)", q_lower)

    if "which customers" in q_lower or "customers with" in q_lower or count_match or amount_under or amount_over:
        filters: Dict[str, Any] = {}
        if count_match:
            filters["min_transaction_count"] = int(count_match.group(1))
        if amount_under:
            filters["max_transaction_amount"] = float(amount_under.group(1).replace(",", ""))
        if amount_over:
            filters["min_transaction_amount"] = float(amount_over.group(1).replace(",", ""))

        if filters:
            return ParsedIntent(
                query=query,
                intent=IntentType.AGGREGATION,
                filters=filters,
                entities=[],
                pattern=None,
                time_window=None,
                raw_llm_response="[Fallback] Parsed aggregation query.",
            )

    # Check for single entity investigation (e.g. "Is customer 4521 suspicious?", "Check account ACC015")
    matches = re.findall(r"\b(?:customer|account|entity)\s+([A-Za-z0-9_-]+)\b", query, re.IGNORECASE)
    valid_entities = [m for m in matches if m.lower() not in reserved_words]
    if valid_entities:
        return ParsedIntent(
            query=query,
            intent=IntentType.ENTITY_INVESTIGATION,
            filters={},
            entities=valid_entities,
            pattern=None,
            time_window=None,
            raw_llm_response="[Fallback] Parsed entity investigation query.",
        )

    # Check for pattern detection (e.g., "Find structuring patterns in the last 30 days")
    patterns_map = {
        "structuring": "structuring",
        "smurfing": "smurfing",
        "layering": "rapid_layering",
        "pass_through": "rapid_layering",
        "fan_out": "fan_out",
        "velocity": "velocity",
    }

    detected_pattern = None
    for p_key, p_name in patterns_map.items():
        if p_key in q_lower:
            detected_pattern = p_name
            break

    # Parse time window
    time_window = None
    tw_match = re.search(r"(?:last|past|in the last|in the past)\s*(\d+)\s*(days?|hours?|weeks?|months?)", q_lower)
    if tw_match:
        val = int(tw_match.group(1))
        unit = tw_match.group(2).rstrip("s") + "s"
        time_window = TimeWindowSpec(
            type="relative",
            value=val,
            unit=unit,
            raw_text=tw_match.group(0),
        )

    if detected_pattern:
        return ParsedIntent(
            query=query,
            intent=IntentType.PATTERN_DETECTION,
            filters={},
            entities=[],
            pattern=detected_pattern,
            time_window=time_window,
            raw_llm_response="[Fallback] Parsed pattern detection query.",
        )

    # Check for broad dataset analysis (e.g., "Analyse this dataset for suspicious activity")
    if "analyse" in q_lower or "analyze" in q_lower or "dataset" in q_lower or "suspicious activity" in q_lower:
        return ParsedIntent(
            query=query,
            intent=IntentType.BROAD_ANALYSIS,
            filters={},
            entities=[],
            pattern=None,
            time_window=time_window,
            raw_llm_response="[Fallback] Parsed broad analysis query.",
        )

    # Unrelated queries (e.g. "What is the weather today?")
    return ParsedIntent(
        query=query,
        intent=IntentType.UNSUPPORTED,
        filters={},
        entities=[],
        pattern=None,
        time_window=None,
        raw_llm_response="[Fallback] Query unsupported.",
    )
