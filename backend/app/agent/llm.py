"""Thin OpenRouter chat client.

The LLM has exactly two jobs in Argus: parse query intent, and write the
final summary. It never decides a flag — detection is deterministic.
"""

import httpx

from ..config import settings

API_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMError(RuntimeError):
    """LLM call failed — carries a human-actionable message."""


class RateLimited(LLMError):
    """OpenRouter returned 429 — the key is rate-limited or out of credits."""


def chat(
    messages: list[dict],
    temperature: float = 0.0,
    json_mode: bool = False,
    max_tokens: int = 1024,
) -> str:
    if not settings.openrouter_api_key:
        raise LLMError(
            "OPENROUTER_API_KEY is not set (backend/.env or .env.local)."
        )

    payload: dict = {
        "model": settings.openrouter_model,
        "messages": messages,
        "temperature": temperature,
        # always cap output — un-capped requests reserve the model's full
        # context against the account budget and can 402 on small balances
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        resp = httpx.post(
            API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "X-Title": "argus-aml",
            },
            timeout=45.0,
        )
    except httpx.HTTPError as exc:
        raise LLMError(f"OpenRouter request failed: {exc}") from exc

    if resp.status_code == 429:
        raise RateLimited(
            "OpenRouter rate limit hit (HTTP 429) — generate a new key or "
            "wait, then retry."
        )
    if resp.status_code != 200:
        raise LLMError(
            f"OpenRouter error {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected OpenRouter response shape: {data}") from exc

    # some models wrap JSON in markdown fences despite json_mode
    return content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
