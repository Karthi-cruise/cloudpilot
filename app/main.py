"""
CloudPilot Application Entrypoint.

Self-Healing Cloud-Native Reliability Platform.
Integrates FastAPI, Prometheus instrumentation, SLO tracking,
chaos engineering hooks, and AI incident diagnosis.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST

from app.metrics import get_metrics_text
from app.middleware import MetricsMiddleware, StructuredLoggingMiddleware
from app.routers import dashboard, health, incidents, items, simulate, slo_router
from app.routers.items import _populate_sample_items
from app.routers.simulate import failure_state
from app.slo import slo_tracker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager: handles startup and shutdown tasks."""
    # Startup
    _populate_sample_items()
    # Pre-record baseline requests into SLO tracker to show healthy state immediately
    for _ in range(50):
        slo_tracker.record_request(is_error=False, latency_ms=15.0)

    yield

    # Shutdown
    simulate.reset_simulation()


app = FastAPI(
    title="CloudPilot API",
    description=(
        "Self-Healing Cloud-Native Reliability Platform. "
        "Provides microservices API, SRE error budget tracking, "
        "failure injection simulation, and automated recovery measurement."
    ),
    version=os.getenv("VERSION", "1.0.0"),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Cross-Origin Resource Sharing (CORS)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Chaos & SLO Request Interceptor Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def chaos_and_slo_interceptor(request: Request, call_next):
    """
    Applies active failure simulations (latency, error rate injection)
    and feeds request outcomes into the SLO tracker.
    """
    path = request.url.path

    # Bypass simulation and SLO tracking for internal/monitoring endpoints
    if path in ("/metrics", "/live", "/ready") or path.startswith("/api/v1/simulate"):
        return await call_next(request)

    # 1. Apply Latency Injection
    if failure_state.active and failure_state.failure_type == "latency":
        delay_seconds = failure_state.latency_ms / 1000.0
        await asyncio.sleep(delay_seconds)

    # 2. Apply Error Rate Injection
    if failure_state.active and failure_state.failure_type == "error_rate":
        if random.randint(1, 100) <= failure_state.error_rate_percent:
            # Artificially return HTTP 500
            slo_tracker.record_request(is_error=True, latency_ms=25.0)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Simulated internal server error (CloudPilot Chaos Engine)",
                    "failure_type": "error_rate",
                },
            )

    start = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0
        is_error = response.status_code >= 500
        slo_tracker.record_request(is_error=is_error, latency_ms=duration_ms)
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000.0
        slo_tracker.record_request(is_error=True, latency_ms=duration_ms)
        raise exc


# Add standard Prometheus and structured logging middlewares
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    StructuredLoggingMiddleware,
    pod_name=os.getenv("POD_NAME", "cloudpilot-local"),
)


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Format HTTP exceptions cleanly."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(items.router)
app.include_router(slo_router.router)
app.include_router(incidents.router)
app.include_router(simulate.router)
app.include_router(dashboard.router)


# ---------------------------------------------------------------------------
# Root and Prometheus Metrics Endpoints
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    """Redirect root path to visual SRE operations dashboard."""
    return RedirectResponse(url="/dashboard")


@app.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Exposes Prometheus text-format metrics for scraping.",
    response_class=PlainTextResponse,
)
async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=get_metrics_text(), media_type=CONTENT_TYPE_LATEST)
