"""
Incident management router.

Tracks operational incidents, MTTR, severity distributions, and connects
to the AI Incident Summarizer (Gemini API) for root cause analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status

from ai.incident_summarizer import IncidentData, IncidentSummarizer
from app.metrics import INCIDENT_COUNT, RECOVERY_TIME
from app.models import Incident, IncidentCreate

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])

# In-memory store: id -> Incident
incidents_db: dict[UUID, Incident] = {}

# Lazy-loaded AI summarizer
_ai_summarizer: Optional[IncidentSummarizer] = None


def get_ai_summarizer() -> IncidentSummarizer:
    """Return singleton AI summarizer instance."""
    global _ai_summarizer
    if _ai_summarizer is None:
        _ai_summarizer = IncidentSummarizer()
    return _ai_summarizer


@router.get(
    "",
    response_model=list[Incident],
    summary="List all incidents",
    description="Retrieve all logged incidents with optional filtering by status and severity.",
)
async def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status", description="open, investigating, resolved"),
    severity: Optional[str] = Query(None, description="P1, P2, P3, P4"),
) -> list[Incident]:
    """List incidents with optional filters."""
    results = list(incidents_db.values())
    if status_filter:
        results = [i for i in results if i.status == status_filter]
    if severity:
        results = [i for i in results if i.severity == severity]
    # Return newest first
    return sorted(results, key=lambda i: i.started_at, reverse=True)


@router.post(
    "",
    response_model=Incident,
    status_code=status.HTTP_201_CREATED,
    summary="Create an incident",
    description="Logs a new operational incident and increments Prometheus incident counters.",
)
async def create_incident(payload: IncidentCreate) -> Incident:
    """Create and record a new incident."""
    incident = Incident(
        id=uuid4(),
        title=payload.title,
        severity=payload.severity,
        status="open",
        started_at=datetime.now(timezone.utc),
    )
    incidents_db[incident.id] = incident
    INCIDENT_COUNT.labels(severity=incident.severity).inc()
    return incident


@router.get(
    "/metrics",
    summary="Incident metrics and MTTR",
    description="Calculates total incidents, open count, MTTR (Mean Time to Recovery), and breakdown by severity.",
)
async def get_incident_metrics() -> dict:
    """Return aggregated incident statistics including MTTR."""
    total = len(incidents_db)
    open_count = sum(1 for i in incidents_db.values() if i.status != "resolved")
    resolved_incidents = [i for i in incidents_db.values() if i.recovery_time_seconds is not None]

    mttr_seconds = (
        round(sum(i.recovery_time_seconds for i in resolved_incidents) / len(resolved_incidents), 2)  # type: ignore[arg-type]
        if resolved_incidents
        else 0.0
    )

    by_severity = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    for i in incidents_db.values():
        if i.severity in by_severity:
            by_severity[i.severity] += 1

    return {
        "total_incidents": total,
        "open_incidents": open_count,
        "resolved_incidents": len(resolved_incidents),
        "mttr_seconds": mttr_seconds,
        "by_severity": by_severity,
    }


@router.get(
    "/{incident_id}",
    response_model=Incident,
    summary="Get incident details",
)
async def get_incident(incident_id: UUID) -> Incident:
    """Fetch an incident by its UUID."""
    if incident_id not in incidents_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return incidents_db[incident_id]


@router.put(
    "/{incident_id}/resolve",
    response_model=Incident,
    summary="Resolve an incident",
    description="Marks the incident as resolved, calculates MTTR recovery time, and observes metrics.",
)
async def resolve_incident(incident_id: UUID) -> Incident:
    """Resolve an incident and record recovery duration."""
    if incident_id not in incidents_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )

    incident = incidents_db[incident_id]
    now = datetime.now(timezone.utc)
    incident.status = "resolved"
    incident.resolved_at = now

    recovery_seconds = (now - incident.started_at).total_seconds()
    incident.recovery_time_seconds = round(recovery_seconds, 2)

    # Observe Prometheus histogram
    RECOVERY_TIME.observe(incident.recovery_time_seconds)

    return incident


@router.get(
    "/{incident_id}/ai-summary",
    summary="Generate or fetch AI incident summary",
    description="Invokes Gemini AI to analyze logs, events, and metrics to produce root cause analysis.",
)
async def get_ai_incident_summary(incident_id: UUID) -> dict:
    """Generate or retrieve AI-powered incident diagnosis."""
    if incident_id not in incidents_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )

    incident = incidents_db[incident_id]

    # If already analyzed, return cached analysis
    if incident.ai_summary and incident.ai_root_cause:
        return {
            "incident_id": str(incident.id),
            "summary": incident.ai_summary,
            "root_cause": incident.ai_root_cause,
            "remediation_steps": (
                incident.ai_remediation.split("\n")
                if incident.ai_remediation
                else []
            ),
            "cached": True,
        }

    # Prepare data for AI analysis
    summarizer = get_ai_summarizer()
    incident_data = IncidentData(
        incident_id=str(incident.id),
        title=incident.title,
        severity=incident.severity,
        started_at=incident.started_at,
        pod_logs=[
            f"INFO Application started successfully",
            f"WARN Latency spike observed on /api/v1/items",
            f"ERROR Upstream connection timeout",
            f"ERROR HTTP 500 error returned to client",
        ],
        k8s_events=[
            "Normal Scheduled pod/cloudpilot-79c8d6487f-abcde successfully assigned",
            "Warning Unhealthy Readiness probe failed: HTTP 503",
            "Normal Killing Container cloudpilot failed liveness probe",
        ],
        metrics_snapshot={
            "error_rate": 0.42,
            "p99_latency_ms": 3200,
            "availability": 94.8,
            "cpu_utilization": 0.78,
        },
        failure_type="error_rate" if "Error" in incident.title else "latency",
    )

    analysis = await summarizer.analyze_incident(incident_data)

    # Cache results on incident object
    incident.ai_summary = analysis.summary
    incident.ai_root_cause = analysis.root_cause
    incident.ai_remediation = "\n".join(analysis.remediation_steps)

    return {
        "incident_id": str(incident.id),
        "summary": analysis.summary,
        "root_cause": analysis.root_cause,
        "affected_components": analysis.affected_components,
        "remediation_steps": analysis.remediation_steps,
        "severity_assessment": analysis.severity_assessment,
        "slo_impact": analysis.slo_impact,
        "prevention_measures": analysis.prevention_measures,
        "confidence": analysis.confidence,
        "model_used": analysis.model_used,
        "is_mock": analysis.is_mock,
        "cached": False,
    }


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Prometheus AlertManager webhook endpoint",
    description="Receives automated alerts from AlertManager and automatically opens incidents.",
)
async def alertmanager_webhook(payload: dict) -> dict:
    """Receive alerts from Prometheus AlertManager and automatically log incidents."""
    alerts = payload.get("alerts", [])
    created = []

    for alert in alerts:
        status_str = alert.get("status", "firing")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        alert_name = labels.get("alertname", "UnknownAlert")
        severity_map = {"critical": "P1", "warning": "P2", "info": "P3"}
        severity = severity_map.get(labels.get("severity", "warning"), "P2")

        if status_str == "firing":
            incident = Incident(
                id=uuid4(),
                title=f"[AlertManager] {alert_name}: {annotations.get('summary', 'Alert fired')}",
                severity=severity,  # type: ignore[arg-type]
                status="open",
                started_at=datetime.now(timezone.utc),
            )
            incidents_db[incident.id] = incident
            INCIDENT_COUNT.labels(severity=incident.severity).inc()
            created.append(str(incident.id))

    return {"status": "ok", "incidents_created": created}
