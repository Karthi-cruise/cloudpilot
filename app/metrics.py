"""
CloudPilot Prometheus metrics definitions.

All counters, histograms, and gauges are declared here so that they are
created exactly once (singleton pattern via module import).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# ---------------------------------------------------------------------------
# Request / latency metrics
# ---------------------------------------------------------------------------

REQUEST_COUNT: Counter = Counter(
    name="cloudpilot_requests_total",
    documentation="Total number of HTTP requests handled by CloudPilot.",
    labelnames=["method", "endpoint", "status_code"],
)

REQUEST_LATENCY: Histogram = Histogram(
    name="cloudpilot_request_duration_seconds",
    documentation="HTTP request duration in seconds.",
    labelnames=["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
)

ERROR_COUNT: Counter = Counter(
    name="cloudpilot_errors_total",
    documentation="Total number of HTTP errors returned by CloudPilot.",
    labelnames=["method", "endpoint", "error_type"],
)

ACTIVE_REQUESTS: Gauge = Gauge(
    name="cloudpilot_active_requests",
    documentation="Number of HTTP requests currently being processed.",
)

# ---------------------------------------------------------------------------
# SLO metrics
# ---------------------------------------------------------------------------

SLO_AVAILABILITY: Gauge = Gauge(
    name="cloudpilot_slo_availability_percent",
    documentation="Current SLO availability percentage for the given window.",
    labelnames=["window"],
)

ERROR_BUDGET_REMAINING: Gauge = Gauge(
    name="cloudpilot_error_budget_remaining_percent",
    documentation="Remaining SLO error budget as a percentage of the monthly budget.",
    labelnames=["window"],
)

# ---------------------------------------------------------------------------
# Incident metrics
# ---------------------------------------------------------------------------

INCIDENT_COUNT: Counter = Counter(
    name="cloudpilot_incidents_total",
    documentation="Total number of incidents opened, labelled by severity.",
    labelnames=["severity"],
)

RECOVERY_TIME: Histogram = Histogram(
    name="cloudpilot_recovery_time_seconds",
    documentation="Time in seconds from incident open to resolved (MTTR).",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

# ---------------------------------------------------------------------------
# Failure simulation metrics
# ---------------------------------------------------------------------------

SIMULATED_FAILURES: Counter = Counter(
    name="cloudpilot_simulated_failures_total",
    documentation="Number of failure simulations started, labelled by type.",
    labelnames=["failure_type"],
)

CURRENT_FAILURE_MODE: Gauge = Gauge(
    name="cloudpilot_failure_mode_active",
    documentation="Set to 1 when the given failure mode is currently active.",
    labelnames=["failure_type"],
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def track_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
) -> None:
    """Record a completed HTTP request into all relevant Prometheus metrics.

    Args:
        method:      HTTP method, e.g. ``"GET"``.
        endpoint:    Normalised path, e.g. ``"/api/v1/items"``.
        status_code: HTTP response status code.
        duration:    Request duration in **seconds**.
    """
    sc = str(status_code)
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=sc).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    if status_code >= 400:
        error_type = "client_error" if status_code < 500 else "server_error"
        ERROR_COUNT.labels(
            method=method, endpoint=endpoint, error_type=error_type
        ).inc()


def get_metrics_text() -> bytes:
    """Return the current Prometheus metrics registry as a UTF-8 byte string.

    Returns:
        Raw ``text/plain; version=0.0.4`` exposition bytes suitable for the
        ``/metrics`` endpoint.
    """
    return generate_latest()
