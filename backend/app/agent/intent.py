"""Intent parsing: natural-language query → structured IntentSpec.

The LLM extracts WHAT the user wants (intent, pattern, filters, entities).
Everything downstream — which tools run, what gets flagged — is deterministic
code keyed off this spec.
"""

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from ..models.schemas import AMLPattern, QueryFilters
from .llm import chat

Intent = Literal[
    "full_analysis",   # broad "find suspicious activity" sweeps
    "pattern_search",  # a named AML typology is the target
    "aggregation",     # count/threshold question answerable by aggregation
    "entity_lookup",   # one specific customer/account
    "eda_only",        # profile/describe the data, no detection asked
]


class IntentSpec(BaseModel):
    intent: Intent
    pattern: AMLPattern | None = None
    filters: QueryFilters = Field(default_factory=QueryFilters)
    top_n: int = 200


SYSTEM_PROMPT = """You are the query parser for Argus, an anti-money-laundering analysis agent.
Turn the user's question about a bank transaction dataset into strict JSON:

{
  "intent": "full_analysis" | "pattern_search" | "aggregation" | "entity_lookup" | "eda_only",
  "pattern": null | "structuring" | "smurfing" | "layering" | "rapid_cash_out" | "velocity" | "anomaly",
  "filters": {
    "last_n_days": null | int,
    "date_from": null | "YYYY-MM-DD",
    "date_to": null | "YYYY-MM-DD",
    "min_amount": null | number,
    "max_amount": null | number,
    "currency": null | string,
    "payment_format": null | string,
    "bank": null | string,
    "account": null | string,
    "customer": null | string,
    "min_txn_count": null | int
  },
  "top_n": 200
}

Filter Field Descriptions:
- last_n_days: Integer number of days for relative windows (e.g., "last 30 days" -> 30).
- date_from: Start date in explicit "YYYY-MM-DD" format.
- date_to: End date in explicit "YYYY-MM-DD" format.
- min_amount: Numeric value for minimum transaction amounts. E.g., "over $10,000" -> 10000. Do not include currency symbols or commas.
- max_amount: Numeric value for maximum transaction amounts. E.g., "under $10,000" -> 10000. Do not include currency symbols or commas.
- currency: Currency name string (e.g. "US Dollar").
- payment_format: One of: ACH, Bitcoin, Cash, Cheque, Credit Card, Reinvestment, Wire.
- bank: Bank ID string.
- account: Account ID string.
- customer: Customer ID or name suffix (e.g. "4521").
- min_txn_count: Minimum transaction count (e.g., "10+ transactions" -> 10).

Intent rules:
- Broad sweeps ("analyse for suspicious activity", "flag high-risk customers") -> "full_analysis".
- A named typology (structuring, smurfing, layering, cash-out, velocity/burst) -> "pattern_search" + pattern.
- Counting/threshold questions (e.g., "10+ transactions under $10,000" or "5+ transactions over $50,000") -> "aggregation" (set min_txn_count and max_amount or min_amount). No pattern.
- One specific customer or account ("is customer 4521 suspicious?") -> "entity_lookup" (set filters.customer or filters.account).
- "Profile / describe / explore the data" with no detection ask -> "eda_only".
Respond with the JSON object only.

Additional instructions:
- Do not include commas or currency symbols in the parsed numbers (e.g., "$10,000" must be parsed as the number 10000).
- Be extremely careful with the number of zeros. For example, "$10,000" has four zeros (10000), not three (1000).
- For any amount threshold like $10,000 or $50,000, write the full parsed integer value (10000 or 50000) in the JSON.
"""


def parse_intent(query: str) -> IntentSpec:
    import re
    # Remove commas inside numbers (e.g. 10,000 -> 10000) and currency symbols
    cleaned_query = re.sub(r'(\d),(\d)', r'\1\2', query)
    cleaned_query = cleaned_query.replace('$', '').replace('€', '').replace('£', '')

    raw = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": cleaned_query},
        ],
        temperature=0.0,
        json_mode=True,
    )
    try:
        return IntentSpec.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError):
        # one corrective retry with the error shown to the model
        raw2 = chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": "That was not valid JSON for the schema. "
                    "Reply with ONLY the corrected JSON object.",
                },
            ],
            temperature=0.0,
            json_mode=True,
        )
        return IntentSpec.model_validate(json.loads(raw2))
