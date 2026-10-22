"""
CloudPilot ASGI middleware.

Provides:
- ``MetricsMiddleware``: Records Prometheus metrics for every HTTP request.
- ``StructuredLoggingMiddleware``: Emits JSON access logs with request IDs.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.metrics import ACTIVE_REQUESTS, track_request

logger = logging.getLogger("cloudpilot.access")


# ---------------------------------------------------------------------------
# Metrics middleware
# ---------------------------------------------------------------------------


class MetricsMiddleware(BaseHTTPMiddleware):
    """Prometheus instrumentation middleware.

    Tracks ``REQUEST_COUNT``, ``REQUEST_LATENCY``, ``ERROR_COUNT``, and
    ``ACTIVE_REQUESTS`` for every incoming request.  The ``/metrics`` path is
    intentionally skipped to avoid recursively tracking self-scrape calls.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and record Prometheus observations."""
        # Do not track the /metrics scrape endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        ACTIVE_REQUESTS.inc()
        start_time = time.perf_counter()
        method = request.method
        # Normalise path so dynamic segments don't create unbounded label sets
        endpoint = self._normalise_path(request.url.path)

        status_code = 500  # default in case of unhandled exception
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:  # noqa: BLE001
            # Let the global exception handler deal with the actual response;
            # we just need to capture the status code for metrics.
            logger.exception("Unhandled exception in request pipeline: %s", exc)
            raise
        finally:
            duration = time.perf_counter() - start_time
            ACTIVE_REQUESTS.dec()
            track_request(method, endpoint, status_code, duration)

    @staticmethod
    def _normalise_path(path: str) -> str:
        """Replace UUID path segments with ``{id}`` to limit label cardinality."""
        parts = path.split("/")
        normalised: list[str] = []
        for part in parts:
            # Detect UUID-like segments (8-4-4-4-12 hex chars)
            try:
                uuid.UUID(part)
                normalised.append("{id}")
            except ValueError:
                normalised.append(part)
        return "/".join(normalised)


# ---------------------------------------------------------------------------
# Structured logging middleware
# ---------------------------------------------------------------------------


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """JSON access-log middleware.

    Emits one log line per request containing:
    ``timestamp``, ``method``, ``path``, ``status_code``, ``duration_ms``,
    ``request_id``, and ``pod_name``.

    A ``X-Request-ID`` header is also injected into every response so that
    callers can correlate logs with their own traces.
    """

    def __init__(self, app: ASGIApp, pod_name: str = "cloudpilot") -> None:
        super().__init__(app)
        self._pod_name = pod_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Assign a request-ID, call the handler, and emit a structured log."""
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Attach the request-ID so downstream handlers can use it
        request.state.request_id = request_id

        response: Response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1_000

        # Inject the request-ID into the response headers for client correlation
        response.headers["X-Request-ID"] = request_id

        log_record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 3),
            "pod_name": self._pod_name,
            "user_agent": request.headers.get("user-agent", ""),
        }
        logger.info(json.dumps(log_record))

        return response
