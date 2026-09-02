from typing import Any

import httpx

from app.core.config import settings


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


async def chat_completion(
    messages: list[dict[str, Any]],
    model: str | None = None,
) -> dict[str, Any]:
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model or settings.OPENROUTER_MODEL,
        "messages": messages,
    }

    async with httpx.AsyncClient(
        base_url=OPENROUTER_BASE_URL,
        timeout=60.0,
    ) as client:
        response = await client.post(
            "chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()
