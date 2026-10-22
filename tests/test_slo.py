"""
Unit tests for SLO Engine, Error Budgets, and Burn Rate Calculations.
"""

from fastapi.testclient import TestClient

from app.slo import SLOConfig, slo_tracker


def test_slo_initial_status(client: TestClient):
    """Verify default 1h SLO status endpoint returns valid metrics."""
    response = client.get("/api/v1/slo")
    assert response.status_code == 200
    data = response.json()
    assert data["window"] == "1h"
    assert "availability_percent" in data
    assert "error_budget_remaining_percent" in data
    assert data["slo_target_percent"] == 99.5


def test_slo_windows_endpoint(client: TestClient):
    """Verify querying various observation windows."""
    for win in ["1h", "24h", "7d", "30d"]:
        response = client.get(f"/api/v1/slo/{win}")
        assert response.status_code == 200
        assert response.json()["window"] == win


def test_slo_burn_rate_endpoint(client: TestClient):
    """Verify burn-rate reporting endpoint."""
    response = client.get("/api/v1/slo/burn-rate")
    assert response.status_code == 200
    data = response.json()
    assert "fast_burn" in data
    assert "slow_burn" in data
    assert "burn_rate_1h" in data


def test_slo_tracker_records_errors():
    """Verify that recording errors drops measured availability."""
    for _ in range(50):
        slo_tracker.record_request(is_error=True, latency_ms=100.0)

    status = slo_tracker.get_slo_status("1h")
    assert status.availability_percent < 99.5
    assert status.errors_total >= 50
