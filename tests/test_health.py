"""
Unit tests for Kubernetes health, readiness, and liveness endpoints.
"""

from fastapi.testclient import TestClient


def test_health_returns_ok_when_healthy(client: TestClient):
    """Verify /health returns status ok when no failure is active."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "pod_name" in data


def test_ready_returns_200_when_healthy(client: TestClient):
    """Verify readiness probe passes when service is ready."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"ready": True}


def test_live_always_returns_200(client: TestClient):
    """Verify liveness probe returns true."""
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"alive": True}


def test_version_returns_metadata(client: TestClient):
    """Verify /version endpoint exposes build information."""
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "git_sha" in data
