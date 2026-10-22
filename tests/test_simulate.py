"""
Unit tests for Chaos and Failure Simulation endpoints.
"""

from fastapi.testclient import TestClient

from app.routers.simulate import failure_state


def test_start_and_stop_simulation(client: TestClient):
    """Verify triggering error_rate simulation and resetting to healthy."""
    payload = {
        "failure_type": "error_rate",
        "duration_seconds": 60,
        "error_rate_percent": 80,
    }
    response = client.post("/api/v1/simulate", json=payload)
    assert response.status_code == 200
    assert response.json()["failure_type"] == "error_rate"
    assert failure_state.active is True

    # Check status
    status_res = client.get("/api/v1/simulate/status")
    assert status_res.status_code == 200
    assert status_res.json()["active"] is True

    # Stop simulation
    del_res = client.delete("/api/v1/simulate")
    assert del_res.status_code == 200
    assert failure_state.active is False


def test_healthy_simulation_clears_active(client: TestClient):
    """Verify posting failure_type='healthy' resets active simulation."""
    client.post("/api/v1/simulate", json={"failure_type": "latency", "duration_seconds": 30})
    assert failure_state.active is True

    res = client.post("/api/v1/simulate", json={"failure_type": "healthy", "duration_seconds": 0})
    assert res.status_code == 200
    assert failure_state.active is False


def test_readiness_probe_fails_during_simulation(client: TestClient):
    """Verify Kubernetes readiness probe returns 503 during error simulation."""
    client.post("/api/v1/simulate", json={"failure_type": "error_rate", "duration_seconds": 30})
    ready_res = client.get("/ready")
    assert ready_res.status_code == 503
    assert ready_res.json()["ready"] is False
