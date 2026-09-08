"""End-to-end resilience and caching tests for the investigation API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agent import executor
from app.api import query as query_api
from app.main import app
from app.utils.query_cache import query_response_cache


@pytest.fixture(autouse=True)
def reset_query_response_cache():
    query_response_cache.clear()
    yield
    query_response_cache.clear()
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_query_happy_path_returns_complete_response_schema(client: TestClient):
    response = client.post(
        "/api/v1/query",
        json={
            "query": "Analyse this dataset for suspicious activity",
            "dataset_path": "synthetic_transactions.csv",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_id"]
    assert payload["parsed_intent"]
    assert payload["execution_plan"]
    assert payload["trace"]
    assert isinstance(payload["flags"], list)
    assert query_api.QueryResponse.model_validate(payload)


def test_cache_hit_avoids_recomputation_and_audit_writes(client: TestClient, monkeypatch):
    calls = {"parse": 0, "plan": 0, "execute": 0, "synthesize": 0, "audit": 0}
    originals = {
        "parse": query_api.parse_intent_async,
        "plan": query_api.create_execution_plan_async,
        "execute": query_api.execute_plan,
        "synthesize": query_api.synthesize_results_async,
    }

    async def count_parse(*args, **kwargs):
        calls["parse"] += 1
        return await originals["parse"](*args, **kwargs)

    async def count_plan(*args, **kwargs):
        calls["plan"] += 1
        return await originals["plan"](*args, **kwargs)

    def count_execute(*args, **kwargs):
        calls["execute"] += 1
        return originals["execute"](*args, **kwargs)

    async def count_synthesize(*args, **kwargs):
        calls["synthesize"] += 1
        return await originals["synthesize"](*args, **kwargs)

    class CountingAuditStore:
        def log_execution_trace(self, *args, **kwargs):
            calls["audit"] += 1

        def log_flags(self, *args, **kwargs):
            calls["audit"] += 1

    monkeypatch.setattr(query_api, "parse_intent_async", count_parse)
    monkeypatch.setattr(query_api, "create_execution_plan_async", count_plan)
    monkeypatch.setattr(query_api, "execute_plan", count_execute)
    monkeypatch.setattr(query_api, "synthesize_results_async", count_synthesize)
    app.dependency_overrides[query_api.get_audit_store] = CountingAuditStore

    request = {"query": "Analyse this dataset for suspicious activity"}
    first = client.post("/api/v1/query", json=request)
    second = client.post("/api/v1/query", json=request)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert calls == {"parse": 1, "plan": 1, "execute": 1, "synthesize": 1, "audit": 2}


def test_failed_response_is_not_cached(client: TestClient, monkeypatch):
    original_parse = query_api.parse_intent_async

    async def fail_parse(*args, **kwargs):
        raise RuntimeError("parser failure")

    monkeypatch.setattr(query_api, "parse_intent_async", fail_parse)
    request = {"query": "Analyse this dataset for suspicious activity"}
    failed = client.post("/api/v1/query", json=request)
    assert failed.status_code == 500
    assert "parser failure" not in failed.json()["detail"]

    calls = {"parse": 0}

    async def count_parse(*args, **kwargs):
        calls["parse"] += 1
        return await original_parse(*args, **kwargs)

    monkeypatch.setattr(query_api, "parse_intent_async", count_parse)
    successful = client.post("/api/v1/query", json=request)

    assert successful.status_code == 200
    assert calls["parse"] == 1


def test_synthesizer_failure_returns_deterministic_results(client: TestClient, monkeypatch):
    async def fail_synthesis(*args, **kwargs):
        raise RuntimeError("synthesis unavailable")

    monkeypatch.setattr(query_api, "synthesize_results_async", fail_synthesis)
    response = client.post(
        "/api/v1/query",
        json={"query": "Find structuring patterns in the last 30 days"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["synthesized_result"] is None
    assert isinstance(payload["flags"], list)
    assert payload["trace"]


def test_audit_failure_is_non_fatal(client: TestClient):
    class FailingAuditStore:
        def log_execution_trace(self, *args, **kwargs):
            raise RuntimeError("audit unavailable")

    app.dependency_overrides[query_api.get_audit_store] = FailingAuditStore
    response = client.post(
        "/api/v1/query",
        json={"query": "Find structuring patterns in the last 30 days"},
    )

    assert response.status_code == 200
    assert query_api.QueryResponse.model_validate(response.json())


def test_dataset_failures_are_clear_without_internal_details(client: TestClient, tmp_path):
    missing = client.post(
        "/api/v1/query",
        json={"query": "Analyse transactions", "dataset_path": "does-not-exist.csv"},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Dataset not found."

    malformed_path = tmp_path / "malformed.csv"
    malformed_path.write_text("wrong,column\n1,2\n", encoding="utf-8")
    malformed = client.post(
        "/api/v1/query",
        json={"query": "Analyse transactions", "dataset_path": str(malformed_path)},
    )
    assert malformed.status_code == 500
    assert malformed.json()["detail"] == "Unable to load transaction data."
    assert "traceback" not in malformed.text.lower()


def test_whitespace_query_and_unexpected_executor_failure_are_safe(client: TestClient, monkeypatch):
    blank = client.post("/api/v1/query", json={"query": "   "})
    assert blank.status_code == 400
    assert "empty" in blank.json()["detail"].lower()

    def fail_execution(*args, **kwargs):
        raise RuntimeError("secret internal execution detail")

    monkeypatch.setattr(query_api, "execute_plan", fail_execution)
    failed = client.post(
        "/api/v1/query",
        json={"query": "Analyse this dataset for suspicious activity"},
    )
    assert failed.status_code == 500
    assert failed.json()["detail"] == "Unable to execute the investigation plan."
    assert "secret" not in failed.text.lower()
    assert "traceback" not in failed.text.lower()


def test_structured_executor_partial_result_remains_a_successful_response(client: TestClient, monkeypatch):
    def fail_features(*args, **kwargs):
        raise RuntimeError("feature engineering unavailable")

    monkeypatch.setattr(executor, "engineer_features", fail_features)
    response = client.post(
        "/api/v1/query",
        json={"query": "Analyse this dataset for suspicious activity"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace"]["status"] == "PARTIAL_SUCCESS"
    assert any(step["status"] == "FAILED" for step in payload["execution_plan"]["steps"])
