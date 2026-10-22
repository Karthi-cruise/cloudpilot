"""
Failure simulation router.

Allows chaos experiments to artificially induce latency, error rates,
or CPU stress to validate the self-healing and alerting loop.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.metrics import CURRENT_FAILURE_MODE, SIMULATED_FAILURES
from app.models import SimulateRequest, SimulateResponse

router = APIRouter(prefix="/api/v1/simulate", tags=["Failure Simulation"])


@dataclass
class FailureState:
    """Represents currently active failure simulation state."""

    active: bool = False
    failure_type: str = "healthy"
    duration_seconds: int = 0
    error_rate_percent: int = 50
    latency_ms: int = 5000
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    _task: Optional[asyncio.Task] = None


# Module-level singleton state
failure_state = FailureState()


async def _auto_stop_simulation(delay: int) -> None:
    """Background task to automatically reset failure state after duration."""
    try:
        await asyncio.sleep(delay)
        reset_simulation()
    except asyncio.CancelledError:
        pass


def reset_simulation() -> None:
    """Reset failure state back to healthy."""
    global failure_state
    if failure_state.failure_type != "healthy":
        CURRENT_FAILURE_MODE.labels(failure_type=failure_state.failure_type).set(0)

    if failure_state._task and not failure_state._task.done():
        failure_state._task.cancel()

    failure_state.active = False
    failure_state.failure_type = "healthy"
    failure_state.duration_seconds = 0
    failure_state.started_at = None
    failure_state.expires_at = None
    failure_state._task = None
    CURRENT_FAILURE_MODE.labels(failure_type="healthy").set(1)


@router.post(
    "",
    response_model=SimulateResponse,
    summary="Trigger a failure simulation",
    description="Starts simulated latency, error rate, CPU stress, or restores healthy state.",
)
async def start_simulation(payload: SimulateRequest) -> SimulateResponse:
    """Trigger a failure simulation."""
    global failure_state

    # Clear any previous timer/mode
    reset_simulation()

    if payload.failure_type == "healthy":
        return SimulateResponse(
            message="System is healthy. All failure simulations cleared.",
            failure_type="healthy",
            duration_seconds=0,
            started_at=datetime.now(timezone.utc),
        )

    now = datetime.now(timezone.utc)
    failure_state.active = True
    failure_state.failure_type = payload.failure_type
    failure_state.duration_seconds = payload.duration_seconds
    failure_state.error_rate_percent = payload.error_rate_percent
    failure_state.latency_ms = payload.latency_ms
    failure_state.started_at = now

    SIMULATED_FAILURES.labels(failure_type=payload.failure_type).inc()
    CURRENT_FAILURE_MODE.labels(failure_type="healthy").set(0)
    CURRENT_FAILURE_MODE.labels(failure_type=payload.failure_type).set(1)

    # Schedule auto-reset
    failure_state._task = asyncio.create_task(
        _auto_stop_simulation(payload.duration_seconds)
    )

    # If CPU stress is requested, launch a CPU-bound worker task
    if payload.failure_type == "cpu_stress":
        asyncio.create_task(_run_cpu_stress(payload.duration_seconds))

    return SimulateResponse(
        message=f"Simulation '{payload.failure_type}' initiated for {payload.duration_seconds}s.",
        failure_type=payload.failure_type,
        duration_seconds=payload.duration_seconds,
        started_at=now,
    )


async def _run_cpu_stress(duration: int) -> None:
    """Consume CPU cycles asynchronously in short bursts to simulate high utilization."""
    end_time = time.time() + duration
    while time.time() < end_time and failure_state.active and failure_state.failure_type == "cpu_stress":
        # Tight compute loop for 50ms, then yield control
        slice_end = time.time() + 0.05
        while time.time() < slice_end:
            _ = sum(i * i for i in range(10000))
        await asyncio.sleep(0.01)


@router.get(
    "/status",
    summary="Get simulation status",
    description="Returns whether a failure simulation is currently active and its parameters.",
)
async def get_simulation_status() -> dict:
    """Return the active simulation state."""
    remaining = 0
    if failure_state.started_at and failure_state.duration_seconds:
        elapsed = (datetime.now(timezone.utc) - failure_state.started_at).total_seconds()
        remaining = max(0, int(failure_state.duration_seconds - elapsed))

    return {
        "active": failure_state.active,
        "failure_type": failure_state.failure_type,
        "duration_seconds": failure_state.duration_seconds,
        "remaining_seconds": remaining,
        "error_rate_percent": failure_state.error_rate_percent,
        "latency_ms": failure_state.latency_ms,
        "started_at": failure_state.started_at.isoformat() if failure_state.started_at else None,
    }


@router.delete(
    "",
    summary="Stop active simulation",
    description="Immediately stops any running failure simulation and returns to healthy.",
)
async def stop_simulation() -> dict:
    """Immediately stop all active failure simulations."""
    reset_simulation()
    return {"message": "All failure simulations stopped. System is healthy."}
