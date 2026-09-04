"""Integration and unit tests for FastAPI /query endpoint (Task 3.6)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Fixture providing TestClient for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


def test_post_query_scenario_1_broad_analysis(client: TestClient):
    """Verify Demo Scenario 1 runs end-to-end full pipeline through POST /api/v1/query."""
    payload = {"query": "Analyse this dataset for suspicious activity"}
    response = client.post("/api/v1/query", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["query"] == "Analyse this dataset for suspicious activity"
    assert data["parsed_intent"]["intent"] == "broad_analysis"
    assert data["execution_plan"]["detected_intent"] == "broad_analysis"
    assert len(data["execution_plan"]["steps"]) == 6
    assert data["execution_plan"]["invoked_tools"] == [
        "eda", "features", "detectors_ml", "detectors_rules", "risk", "explain"
    ]
    assert data["execution_plan"]["skipped_tools"] == []
    assert data["risk_result"] is not None
    assert "risk_score" in data["risk_result"]
    assert "risk_tier" in data["risk_result"]
    assert data["synthesized_result"] is not None
    assert "executive_summary" in data["synthesized_result"]
    assert data["trace"]["status"] in ("SUCCESS", "PARTIAL_SUCCESS")
    assert data["trace"]["total_execution_time_ms"] > 0
    assert data["eda_summary"] is not None


def test_post_query_scenario_2_structuring_temporal(client: TestClient):
    """Verify Demo Scenario 2 executes targeted structuring search with skipped tools."""
    payload = {"query": "Find structuring patterns in the last 30 days"}
    response = client.post("/api/v1/query", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["parsed_intent"]["intent"] == "pattern_detection"
    assert data["execution_plan"]["invoked_tools"] == ["detectors_rules", "risk", "explain"]
    
    skipped_names = [st["tool_name"] for st in data["execution_plan"]["skipped_tools"]]
    assert "eda" in skipped_names
    assert "detectors_ml" in skipped_names
    assert len(data["flags"]) > 0
    assert any(f["typology"] == "Structuring" for f in data["flags"])


def test_post_query_scenario_3_aggregation_thresholds(client: TestClient):
    """Verify Demo Scenario 3 executes aggregation pipeline while skipping ML."""
    payload = {"query": "Which customers made 10+ transactions under $10,000?"}
    response = client.post("/api/v1/query", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["parsed_intent"]["intent"] == "aggregation"
    assert data["execution_plan"]["invoked_tools"] == ["features", "detectors_rules", "risk", "explain"]
    skipped_names = [st["tool_name"] for st in data["execution_plan"]["skipped_tools"]]
    assert "detectors_ml" in skipped_names
    assert "eda" in skipped_names


def test_post_query_scenario_4_entity_investigation(client: TestClient):
    """Verify Demo Scenario 4 targets single entity drill-down."""
    payload = {"query": "Is customer 4521 suspicious?"}
    response = client.post("/api/v1/query", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["parsed_intent"]["intent"] == "entity_investigation"
    assert data["execution_plan"]["target_entities"] == ["4521"]
    for step in data["execution_plan"]["steps"]:
        assert step["parameters"].get("entity_id") == "4521"


def test_post_query_root_path_accessible(client: TestClient):
    """Verify root /query endpoint is accessible alongside /api/v1/query."""
    payload = {"query": "Find structuring patterns in the last 30 days"}
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    assert response.json()["parsed_intent"]["intent"] == "pattern_detection"


def test_post_query_empty_query_validation(client: TestClient):
    """Verify empty query string returns 400 Bad Request."""
    response = client.post("/api/v1/query", json={"query": "   "})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_post_query_nonexistent_dataset_returns_404(client: TestClient):
    """Verify nonexistent dataset filename returns 404 Not Found."""
    payload = {
        "query": "Analyse transactions",
        "dataset_path": "nonexistent_file_12345.csv"
    }
    response = client.post("/api/v1/query", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_post_query_with_stratified_sampling(client: TestClient):
    """Verify normal_sample_size parameter executes successfully."""
    payload = {
        "query": "Analyse this dataset for suspicious activity",
        "normal_sample_size": 5
    }
    response = client.post("/api/v1/query", json=payload)
    assert response.status_code == 200
    assert response.json()["trace"]["status"] == "SUCCESS"
