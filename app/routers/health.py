"""
Health-check router.

Provides Kubernetes liveness, readiness, and version endpoints that the
infrastructure uses to determine pod health and route traffic.
"""

from __future__ import annotations

import os
import socket
import time
from typing import Any

from fastapi import APIRouter, Response

from app.models import HealthResponse

router = APIRouter(tags=["Health"])

# Module-level start time so uptime is computed relative to import
_START_TIME: float = time.time()


def _pod_name() -> str:
    """Return the pod name from ``POD_NAME`` env-var or the system hostname."""
    return os.getenv("POD_NAME", socket.gethostname())


def _version() -> str:
    """Return the application version from the ``VERSION`` env-var."""
    return os.getenv("VERSION", "1.0.0")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Aggregated health status",
    description=(
        "Returns ``ok`` when the service is fully operational, "
        "``degraded`` when a failure simulation is active."
    ),
)
async def health_check() -> HealthResponse:
    """Return the current health of the CloudPilot API.

    Status is ``degraded`` whenever an error-rate or latency failure
    simulation is running; otherwise ``ok``.
    """
    # Import here to avoid a circular dependency at module level
    from app.routers.simulate import failure_state

    status = "degraded" if (failure_state.active and failure_state.failure_type != "healthy") else "ok"

    return HealthResponse(
        status=status,  # type: ignore[arg-type]
        version=_version(),
        uptime_seconds=round(time.time() - _START_TIME, 2),
        pod_name=_pod_name(),
    )


@router.get(
    "/ready",
    summary="Kubernetes readiness probe",
    description=(
        "Returns HTTP 200 when the pod is ready to receive traffic. "
        "Returns HTTP 503 during active error-rate simulations."
    ),
)
async def readiness_check(response: Response) -> dict[str, Any]:
    """Readiness probe — signals to Kubernetes whether to route traffic here.

    If an ``error_rate`` or ``latency`` simulation is active the pod
    reports itself as *not ready* so the load-balancer stops sending
    traffic to it.
    """
    from app.routers.simulate import failure_state

    if failure_state.active and failure_state.failure_type in ("error_rate", "latency"):
        response.status_code = 503
        return {
            "ready": False,
            "reason": f"Failure simulation active: {failure_state.failure_type}",
        }

    return {"ready": True}


@router.get(
    "/live",
    summary="Kubernetes liveness probe",
    description="Always returns HTTP 200.  If this endpoint is unreachable the process has crashed.",
)
async def liveness_check() -> dict[str, bool]:
    """Liveness probe — always returns ``{alive: true}``.

    Kubernetes will restart the container if this endpoint stops responding.
    """
    return {"alive": True}


@router.get(
    "/version",
    summary="Build / version metadata",
    description="Returns version, build time, and git SHA sourced from environment variables.",
)
async def version_info() -> dict[str, str]:
    """Return version metadata injected at build time via environment variables."""
    return {
        "version": os.getenv("VERSION", "1.0.0"),
        "build_time": os.getenv("BUILD_TIME", "unknown"),
        "git_sha": os.getenv("GIT_SHA", "unknown"),
    }
