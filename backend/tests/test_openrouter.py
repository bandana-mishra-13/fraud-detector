import json

import httpx
import pytest

from app.core import openrouter


@pytest.mark.anyio
async def test_chat_completion_sends_expected_openrouter_request(monkeypatch):
    captured_request: dict[str, httpx.Request] = {}
    expected_response = {"id": "test-response", "choices": []}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["request"] = request
        return httpx.Response(200, json=expected_response, request=request)

    real_async_client = httpx.AsyncClient

    def mock_async_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(openrouter.httpx, "AsyncClient", mock_async_client)
    monkeypatch.setattr(openrouter.settings, "OPENROUTER_API_KEY", "test-api-key")

    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Summarize this transaction."}],
        }
    ]

    response = await openrouter.chat_completion(messages, model="openrouter/free")

    request = captured_request["request"]
    assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer test-api-key"
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == {
        "model": "openrouter/free",
        "messages": messages,
    }
    assert response == expected_response
