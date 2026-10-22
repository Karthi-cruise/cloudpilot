"""
CloudPilot SLO (Service Level Objective) engine.

Implements a sliding-window availability tracker that powers the SLO
dashboard.  Design is based on Google SRE Book burn-rate alerting.

Key constants (from SLOConfig):
    - Availability target: 99.5 %
    - Monthly error budget: 216 minutes
    - Fast-burn threshold: 14.4× in 1 h  (consumes 2 % budget → page)
    - Slow-burn threshold:  6×  in 6 h   (consumes 5 % budget → ticket)
"""

from __future__ import annotations

import statistics
from collections import deque
from datetime import datetime, timedelta
from typing import NamedTuple

from app.models import SLOStatus


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class SLOConfig:
    """Static SLO configuration constants."""

    AVAILABILITY_TARGET: float = 99.5  # percent
    LATENCY_P99_TARGET_MS: float = 200.0  # milliseconds
    ERROR_RATE_TARGET_PERCENT: float = 0.5  # percent

    # Error budget = (100 - target) / 100 * 30 days * 24 h * 60 min
    ERROR_BUDGET_MONTHLY_MINUTES: float = (
        (100 - AVAILABILITY_TARGET) / 100 * 30 * 24 * 60
    )  # = 216.0 minutes

    # Google SRE burn-rate alert thresholds
    FAST_BURN_THRESHOLD: float = 14.4  # × normal rate over 1 h
    SLOW_BURN_THRESHOLD: float = 6.0   # × normal rate over 6 h

    # Window definitions: label → hours
    WINDOWS: dict[str, int] = {
        "1h": 1,
        "24h": 24,
        "7d": 168,
        "30d": 720,
    }

    # Max entries per deque (1 entry per second worst-case, padded)
    MAX_ENTRIES: int = 720 * 3600  # 30 days of per-second data — use deque maxlen


# ---------------------------------------------------------------------------
# Data entry
# ---------------------------------------------------------------------------


class _RequestEntry(NamedTuple):
    """Single request observation stored in the sliding window."""

    timestamp: datetime
    is_error: bool
    latency_ms: float


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------


class SLOTracker:
    """In-memory sliding-window SLO tracker.

    Thread-safety note: for a production service, wrap mutations in an
    ``asyncio.Lock``; this implementation is safe for a single-threaded
    asyncio event loop.
    """

    def __init__(self) -> None:
        # Shared store — deque with a generous maxlen (≈30 days at 10 RPS)
        self._store: deque[_RequestEntry] = deque(
            maxlen=10_000_000  # ~10 M entries ≈ 30 days at ~4 RPS average
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record_request(self, is_error: bool, latency_ms: float) -> None:
        """Append a request observation to the sliding window.

        Args:
            is_error:   Whether the request resulted in an HTTP 5xx error.
            latency_ms: Response latency in milliseconds.
        """
        self._store.append(
            _RequestEntry(
                timestamp=datetime.utcnow(),
                is_error=is_error,
                latency_ms=latency_ms,
            )
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _entries_in_window(self, hours: int) -> list[_RequestEntry]:
        """Return all entries that fall within the last *hours* hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        # deque is ordered oldest→newest; walk from the right for efficiency
        result: list[_RequestEntry] = []
        for entry in reversed(self._store):
            if entry.timestamp >= cutoff:
                result.append(entry)
            else:
                break
        return result

    def _availability_from_entries(
        self, entries: list[_RequestEntry]
    ) -> float:
        """Calculate availability percentage from a list of entries."""
        if not entries:
            return 100.0
        errors = sum(1 for e in entries if e.is_error)
        return (1 - errors / len(entries)) * 100

    # ------------------------------------------------------------------
    # Read — SLO status
    # ------------------------------------------------------------------

    def get_slo_status(self, window: str = "1h") -> SLOStatus:
        """Return a full :class:`SLOStatus` snapshot for the given window.

        Args:
            window: One of ``"1h"``, ``"24h"``, ``"7d"``, ``"30d"``.

        Returns:
            :class:`SLOStatus` populated with live metrics.

        Raises:
            ValueError: If *window* is not a recognised key.
        """
        if window not in SLOConfig.WINDOWS:
            raise ValueError(
                f"Unknown SLO window '{window}'. "
                f"Valid options: {list(SLOConfig.WINDOWS)}"
            )

        hours = SLOConfig.WINDOWS[window]
        entries = self._entries_in_window(hours)

        total = len(entries)
        errors = sum(1 for e in entries if e.is_error)
        availability = self._availability_from_entries(entries)

        # Error budget consumed = downtime minutes relative to target
        # downtime_fraction = (target - actual) / 100
        # consumed_minutes = downtime_fraction * window_minutes
        window_minutes = hours * 60
        if availability < SLOConfig.AVAILABILITY_TARGET:
            downtime_fraction = (SLOConfig.AVAILABILITY_TARGET - availability) / 100
        else:
            downtime_fraction = 0.0
        consumed_minutes = downtime_fraction * window_minutes

        # Scale consumed_minutes to monthly budget for remaining %
        # remaining % = 100 - (consumed_minutes / monthly_budget * 100)
        remaining_percent = max(
            0.0,
            100.0
            - (consumed_minutes / SLOConfig.ERROR_BUDGET_MONTHLY_MINUTES * 100),
        )

        burn_rate = self.calculate_burn_rate(hours)

        return SLOStatus(
            window=window,
            availability_percent=round(availability, 4),
            error_budget_remaining_percent=round(remaining_percent, 4),
            error_budget_consumed_minutes=round(consumed_minutes, 4),
            requests_total=total,
            errors_total=errors,
            p99_latency_ms=round(self.get_p99_latency(window), 3),
            slo_target_percent=SLOConfig.AVAILABILITY_TARGET,
            is_burning_fast=self.is_fast_burn(),
            burn_rate=round(burn_rate, 4),
        )

    # ------------------------------------------------------------------
    # Read — burn rates
    # ------------------------------------------------------------------

    def calculate_burn_rate(self, window_hours: int) -> float:
        """Compute the error burn rate relative to the SLO error budget.

        A burn rate of 1.0 means errors are being produced exactly at the
        rate that would consume the full monthly budget in one month.
        A burn rate of 14.4 means the budget will be exhausted in ≈2 days.

        Args:
            window_hours: Length of the observation window in hours.

        Returns:
            Burn-rate multiplier (≥ 0.0).
        """
        entries = self._entries_in_window(window_hours)
        if not entries:
            return 0.0

        actual_error_rate = sum(1 for e in entries if e.is_error) / len(entries)
        # Allowed error rate derived from the SLO target
        allowed_error_rate = (100 - SLOConfig.AVAILABILITY_TARGET) / 100

        if allowed_error_rate == 0:
            return 0.0 if actual_error_rate == 0 else float("inf")

        return actual_error_rate / allowed_error_rate

    def is_fast_burn(self) -> bool:
        """Return ``True`` if the 1-hour burn rate exceeds 14.4× (page-level alert)."""
        return self.calculate_burn_rate(1) > SLOConfig.FAST_BURN_THRESHOLD

    def is_slow_burn(self) -> bool:
        """Return ``True`` if the 6-hour burn rate exceeds 6× (ticket-level alert)."""
        return self.calculate_burn_rate(6) > SLOConfig.SLOW_BURN_THRESHOLD

    # ------------------------------------------------------------------
    # Read — error budget
    # ------------------------------------------------------------------

    def get_error_budget_remaining_minutes(self) -> float:
        """Return the remaining monthly error budget in minutes.

        Uses the 30-day window to estimate total consumption.
        """
        entries = self._entries_in_window(720)  # 30 days
        availability = self._availability_from_entries(entries)

        if availability >= SLOConfig.AVAILABILITY_TARGET:
            return SLOConfig.ERROR_BUDGET_MONTHLY_MINUTES

        # Proportion of budget consumed in the 30-day window
        downtime_fraction = (SLOConfig.AVAILABILITY_TARGET - availability) / 100
        consumed = downtime_fraction * 720 * 60  # window minutes
        remaining = SLOConfig.ERROR_BUDGET_MONTHLY_MINUTES - consumed
        return max(0.0, remaining)

    # ------------------------------------------------------------------
    # Read — latency
    # ------------------------------------------------------------------

    def get_p99_latency(self, window: str = "1h") -> float:
        """Return the 99th-percentile latency in milliseconds for the window.

        Args:
            window: One of the recognised window keys.

        Returns:
            P99 latency in milliseconds, or ``0.0`` if no data.
        """
        hours = SLOConfig.WINDOWS.get(window, 1)
        entries = self._entries_in_window(hours)
        if not entries:
            return 0.0
        latencies = sorted(e.latency_ms for e in entries)
        idx = int(len(latencies) * 0.99)
        return latencies[min(idx, len(latencies) - 1)]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

#: Global SLO tracker shared across the entire application.
slo_tracker: SLOTracker = SLOTracker()
