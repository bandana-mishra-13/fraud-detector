"""Integration and unit tests for FastAPI /audit endpoints (Task 3.6)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Flag, RiskTier
from app.storage.audit_store import get_audit_store


@pytest.fixture
def client() -> TestClient:
    """Fixture providing TestClient for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


def test_audit_feedback_workflow(client: TestClient):
    """Test full feedback logging lifecycle via POST /api/v1/audit/feedback."""
    audit_store = get_audit_store()
    flag = Flag(
        flag_id="flag-api-test-01",
        rule_id="RULE_STRUCTURING_01",
        rule_name="Structuring Test",
        severity=RiskTier.HIGH,
        entity_id="ACC_API_TEST",
        reason="Structuring pattern found",
    )
    audit_store.log_flags([flag], query_id="query-api-test")

    # 1. Post analyst review feedback
    feedback_payload = {
        "flag_id": "flag-api-test-01",
        "feedback_status": "CONFIRMED_SUSPICIOUS",
        "analyst_id": "compliance_officer_1",
        "notes": "Confirmed intentional structuring behavior.",
        "query_id": "query-api-test",
    }
    res = client.post("/api/v1/audit/feedback", json=feedback_payload)
    assert res.status_code == 200

    data = res.json()
    assert data["flag_id"] == "flag-api-test-01"
    assert data["feedback_status"] == "CONFIRMED_SUSPICIOUS"
    assert data["analyst_id"] == "compliance_officer_1"
    assert data["notes"] == "Confirmed intentional structuring behavior."

    # 2. Verify GET /api/v1/audit/flags/{flag_id} reflects updated state and history
    flag_res = client.get("/api/v1/audit/flags/flag-api-test-01")
    assert flag_res.status_code == 200
    flag_data = flag_res.json()
    assert flag_data["feedback_status"] == "CONFIRMED_SUSPICIOUS"
    assert flag_data["analyst_notes"] == "Confirmed intentional structuring behavior."
    assert len(flag_data["feedback_history"]) >= 1


def test_audit_feedback_nonexistent_flag_returns_404(client: TestClient):
    """Verify posting feedback for a nonexistent flag returns 404."""
    feedback_payload = {
        "flag_id": "nonexistent_flag_9999",
        "feedback_status": "FALSE_POSITIVE",
        "analyst_id": "officer_2",
    }
    res = client.post("/api/v1/audit/feedback", json=feedback_payload)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_audit_queries_and_query_by_id(client: TestClient):
    """Test retrieving query logs via GET /api/v1/audit/queries."""
    audit_store = get_audit_store()
    qid = audit_store.log_query(
        query_text="Find structuring transactions",
        detected_intent="TYPOLOGY_SEARCH",
        status="SUCCESS",
    )

    # List queries
    list_res = client.get("/api/v1/audit/queries?limit=10")
    assert list_res.status_code == 200
    queries = list_res.json()
    assert len(queries) >= 1
    assert any(q["query_id"] == qid for q in queries)

    # Get single query
    single_res = client.get(f"/api/v1/audit/queries/{qid}")
    assert single_res.status_code == 200
    assert single_res.json()["query_id"] == qid
    assert single_res.json()["query_text"] == "Find structuring transactions"


def test_get_audit_query_by_id_nonexistent_returns_404(client: TestClient):
    """Verify getting nonexistent query returns 404."""
    res = client.get("/api/v1/audit/queries/nonexistent_qid_999")
    assert res.status_code == 404


def test_get_audit_flags_filtering(client: TestClient):
    """Test listing flags with query parameter filters."""
    audit_store = get_audit_store()
    flag1 = Flag(
        flag_id="flag-filter-01",
        rule_id="RULE_SMURFING_FAN_IN_01",
        rule_name="Smurfing",
        severity=RiskTier.CRITICAL,
        entity_id="ACC_FILTER_1",
        reason="Smurfing",
    )
    flag2 = Flag(
        flag_id="flag-filter-02",
        rule_id="RULE_STRUCTURING_01",
        rule_name="Structuring",
        severity=RiskTier.LOW,
        entity_id="ACC_FILTER_2",
        reason="Structuring",
    )
    audit_store.log_flags([flag1, flag2], query_id="q-filter-test")

    # Filter by severity
    crit_res = client.get("/api/v1/audit/flags?severity=CRITICAL")
    assert crit_res.status_code == 200
    crit_flags = crit_res.json()
    assert any(f["flag_id"] == "flag-filter-01" for f in crit_flags)
    assert not any(f["flag_id"] == "flag-filter-02" for f in crit_flags)

    # Filter by entity_id
    ent_res = client.get("/api/v1/audit/flags?entity_id=ACC_FILTER_2")
    assert ent_res.status_code == 200
    ent_flags = ent_res.json()
    assert len(ent_flags) >= 1
    assert ent_flags[0]["entity_id"] == "ACC_FILTER_2"


def test_get_audit_summary_endpoint(client: TestClient):
    """Verify GET /api/v1/audit/summary returns aggregate statistics."""
    res = client.get("/api/v1/audit/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_queries" in data
    assert "total_flags" in data
    assert "total_feedback_events" in data
    assert "flags_by_severity" in data
    assert "flags_by_feedback_status" in data
