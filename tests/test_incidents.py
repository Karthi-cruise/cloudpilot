"""
Unit tests for Incidents lifecycle, MTTR metrics, and AI summary.
"""

from fastapi.testclient import TestClient


def test_create_and_resolve_incident(client: TestClient):
    """Verify opening an incident, resolving it, and checking recovery time."""
    payload = {
        "title": "High P99 Latency on API Gateway",
        "severity": "P1",
    }
    create_res = client.post("/api/v1/incidents", json=payload)
    assert create_res.status_code == 201
    incident = create_res.json()
    assert incident["status"] == "open"
    assert incident["severity"] == "P1"

    inc_id = incident["id"]

    # Resolve incident
    resolve_res = client.put(f"/api/v1/incidents/{inc_id}/resolve")
    assert resolve_res.status_code == 200
    resolved = resolve_res.json()
    assert resolved["status"] == "resolved"
    assert resolved["recovery_time_seconds"] is not None

    # Verify metrics
    metrics_res = client.get("/api/v1/incidents/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["total_incidents"] >= 1
    assert metrics["resolved_incidents"] >= 1


def test_ai_summary_generation(client: TestClient):
    """Verify AI incident summary endpoint generates structured analysis."""
    create_res = client.post("/api/v1/incidents", json={"title": "CrashLoopBackOff on pod-2", "severity": "P2"})
    inc_id = create_res.json()["id"]

    ai_res = client.get(f"/api/v1/incidents/{inc_id}/ai-summary")
    assert ai_res.status_code == 200
    analysis = ai_res.json()
    assert "summary" in analysis
    assert "root_cause" in analysis
    assert "remediation_steps" in analysis
    assert len(analysis["remediation_steps"]) > 0


def test_alertmanager_webhook(client: TestClient):
    """Verify AlertManager webhook receiver logs incidents automatically."""
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "CloudPilotSLOFastBurn", "severity": "critical"},
                "annotations": {"summary": "Error budget burning fast"},
            }
        ]
    }
    resp = client.post("/api/v1/incidents/webhook", json=payload)
    assert resp.status_code == 200
    assert len(resp.json()["incidents_created"]) == 1
