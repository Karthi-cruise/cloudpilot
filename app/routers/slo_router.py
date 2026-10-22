"""
SLO dashboard router.

Exposes the SLO engine's metrics via REST endpoints so that Grafana,
on-call engineers, and the CloudPilot UI can query live SLO health.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.models import SLOStatus
from app.slo import SLOConfig, slo_tracker

router = APIRouter(prefix="/api/v1/slo", tags=["SLO"])

_VALID_WINDOWS = list(SLOConfig.WINDOWS.keys())  # ["1h", "24h", "7d", "30d"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SLOStatus,
    summary="Current SLO status (1-hour window)",
    description="Returns SLO health metrics for the default 1-hour sliding window.",
)
async def get_slo_status() -> SLOStatus:
    """Return SLO status using the default 1-hour window.

    Returns:
        :class:`SLOStatus` for the last 60 minutes of traffic.
    """
    return slo_tracker.get_slo_status("1h")


@router.get(
    "/burn-rate",
    summary="Current SLO burn rate",
    description=(
        "Returns the error burn rate for 1-hour and 6-hour windows and "
        "whether fast-burn or slow-burn alerts are firing."
    ),
)
async def get_burn_rate() -> dict[str, Any]:
    """Return burn-rate data for the 1-hour and 6-hour windows.

    A **fast burn** (>14.4×) triggers a P1 page; a **slow burn** (>6×)
    opens a ticket.

    Returns:
        Dictionary with ``fast_burn``, ``slow_burn``, ``burn_rate_1h``,
        and ``burn_rate_6h``.
    """
    return {
        "fast_burn": slo_tracker.is_fast_burn(),
        "slow_burn": slo_tracker.is_slow_burn(),
        "burn_rate_1h": round(slo_tracker.calculate_burn_rate(1), 4),
        "burn_rate_6h": round(slo_tracker.calculate_burn_rate(6), 4),
    }


@router.get(
    "/error-budget",
    summary="Error budget status",
    description="Returns remaining error budget in minutes and as a percentage.",
)
async def get_error_budget() -> dict[str, float]:
    """Return the current state of the monthly error budget.

    Returns:
        Dictionary with ``remaining_minutes``, ``consumed_minutes``, and
        ``remaining_percent``.
    """
    remaining = slo_tracker.get_error_budget_remaining_minutes()
    consumed = SLOConfig.ERROR_BUDGET_MONTHLY_MINUTES - remaining
    remaining_pct = (remaining / SLOConfig.ERROR_BUDGET_MONTHLY_MINUTES) * 100

    return {
        "remaining_minutes": round(remaining, 4),
        "consumed_minutes": round(max(0.0, consumed), 4),
        "remaining_percent": round(remaining_pct, 4),
        "total_budget_minutes": SLOConfig.ERROR_BUDGET_MONTHLY_MINUTES,
    }


@router.get(
    "/report",
    response_model=list[SLOStatus],
    summary="Full SLO report — all windows",
    description="Returns SLO status for all four observation windows: 1h, 24h, 7d, 30d.",
)
async def get_slo_report() -> list[SLOStatus]:
    """Return a complete SLO report for all supported windows.

    Returns:
        List of :class:`SLOStatus` — one entry per window.
    """
    return [slo_tracker.get_slo_status(w) for w in _VALID_WINDOWS]


@router.get(
    "/{window}",
    response_model=SLOStatus,
    summary="SLO status for a specific window",
    description="Returns SLO health metrics for the given window (1h | 24h | 7d | 30d).",
)
async def get_slo_status_window(window: str) -> SLOStatus:
    """Return SLO status for the requested time window.

    Args:
        window: One of ``1h``, ``24h``, ``7d``, ``30d``.

    Returns:
        :class:`SLOStatus` for the requested window.

    Raises:
        HTTPException: 400 if *window* is not recognised.
    """
    if window not in _VALID_WINDOWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown window '{window}'. "
                f"Valid options: {_VALID_WINDOWS}"
            ),
        )
    return slo_tracker.get_slo_status(window)
