#!/usr/bin/env python3
"""
CloudPilot SLO Calculator — Standalone CLI tool

Queries Prometheus for real SLO data or simulates realistic values when
Prometheus is not reachable. Supports availability, error budget, burn
rates, and P99 latency.

Usage:
  python sre/slo_calculator.py
  python sre/slo_calculator.py --window 7d --slo-target 99.9
  python sre/slo_calculator.py --report --output json
  python sre/slo_calculator.py --watch 30
  python sre/slo_calculator.py --prometheus-url http://prom.example.com:9090
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# ANSI colour helpers (no external dependency)
# ---------------------------------------------------------------------------

class _C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    GREEN  = "\033[92m"
    CYAN   = "\033[96m"
    BLUE   = "\033[94m"
    DIM    = "\033[2m"

def _colour(text: str, *codes: str) -> str:
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + _C.RESET


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------

_WINDOW_SECONDS: dict[str, int] = {
    "1h":  3600,
    "6h":  21_600,
    "24h": 86_400,
    "7d":  604_800,
    "30d": 2_592_000,
}


def _parse_window(window: str) -> int:
    """Return window in seconds; raise ValueError on bad input."""
    if window not in _WINDOW_SECONDS:
        raise ValueError(
            f"Invalid window '{window}'. Choose from: {', '.join(_WINDOW_SECONDS)}"
        )
    return _WINDOW_SECONDS[window]


# ---------------------------------------------------------------------------
# Prometheus client
# ---------------------------------------------------------------------------

class PrometheusClient:
    """Thin HTTP wrapper around the Prometheus HTTP API."""

    def __init__(self, base_url: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> dict:
        url = f"{self.base_url}{path}?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    def query(self, promql: str) -> Optional[float]:
        """
        Run an instant PromQL query and return the scalar value.
        Returns None if no data or query fails.
        """
        try:
            data = self._get("/api/v1/query", {"query": promql})
            results = data.get("data", {}).get("result", [])
            if not results:
                return None
            value = results[0].get("value", [None, None])[1]
            return float(value) if value is not None else None
        except Exception:  # noqa: BLE001
            return None

    def query_range(
        self,
        promql: str,
        start: datetime,
        end: datetime,
        step: str = "1m",
    ) -> list[dict]:
        """
        Run a range query. Returns list of {timestamp: float, value: float} dicts.
        Returns empty list on failure.
        """
        try:
            params = {
                "query": promql,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": step,
            }
            data = self._get("/api/v1/query_range", params)
            results = data.get("data", {}).get("result", [])
            if not results:
                return []
            values = results[0].get("values", [])
            return [{"timestamp": float(ts), "value": float(v)} for ts, v in values]
        except Exception:  # noqa: BLE001
            return []

    def ping(self) -> bool:
        """Return True if Prometheus is reachable."""
        try:
            self._get("/api/v1/query", {"query": "1"})
            return True
        except Exception:  # noqa: BLE001
            return False


# ---------------------------------------------------------------------------
# SLO Calculator
# ---------------------------------------------------------------------------

class SLOCalculator:
    """
    Calculates SLO metrics against a Prometheus data source.
    Falls back to simulated data when Prometheus is unreachable.
    """

    # PromQL expressions — adapted from Google SRE workbook
    _PROMQL_AVAILABILITY = (
        "100 * (1 - sum(rate(http_requests_total{{status=~'5..'}}[{window}]))"
        " / sum(rate(http_requests_total[{window}])))"
    )
    _PROMQL_ERROR_RATE = (
        "100 * sum(rate(http_requests_total{{status=~'5..'}}[{window}]))"
        " / sum(rate(http_requests_total[{window}]))"
    )
    _PROMQL_P99_LATENCY = (
        "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[{window}])) by (le)) * 1000"
    )
    _PROMQL_RPS = "sum(rate(http_requests_total[{window}]))"

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        slo_target: float = 99.5,
        window_hours: int = 24,
    ) -> None:
        self.prometheus_url = prometheus_url
        self.slo_target = slo_target
        self.window_hours = window_hours
        self.window = f"{window_hours}h" if window_hours < 168 else f"{window_hours // 24}d"
        self._prom = PrometheusClient(prometheus_url)
        self._live = self._prom.ping()
        if not self._live:
            print(
                _colour(
                    f"⚠  Prometheus not reachable at {prometheus_url}. "
                    "Running in simulation mode with representative data.",
                    _C.YELLOW,
                ),
                file=sys.stderr,
            )

    # ------------------------------------------------------------------
    # Core metrics
    # ------------------------------------------------------------------

    def calculate_availability(self) -> float:
        """Return availability percentage over the configured window."""
        if self._live:
            val = self._prom.query(
                self._PROMQL_AVAILABILITY.format(window=self.window)
            )
            if val is not None:
                return round(val, 4)

        # Simulation: stable near-SLO availability with small jitter
        import random
        random.seed(int(time.time() / 3600))  # Stable within an hour
        base = self.slo_target - random.uniform(-0.3, 0.15)
        return round(max(0.0, min(100.0, base)), 4)

    def calculate_error_budget(self) -> dict:
        """
        Return error budget breakdown.

        Keys:
          remaining_minutes   – budget minutes still available
          consumed_minutes    – budget minutes already spent
          remaining_percent   – budget remaining as percentage of total budget
          total_budget_minutes– total error budget for the window
          burn_rate_1h        – current 1-hour burn rate multiplier
          on_track            – True if budget is not exhausted
        """
        availability = self.calculate_availability()
        error_percent = 100.0 - availability
        slo_error_percent = 100.0 - self.slo_target

        window_minutes = self.window_hours * 60
        total_budget_minutes = window_minutes * (slo_error_percent / 100.0)
        consumed_minutes = window_minutes * (error_percent / 100.0)
        remaining_minutes = max(0.0, total_budget_minutes - consumed_minutes)
        remaining_percent = (
            (remaining_minutes / total_budget_minutes * 100.0)
            if total_budget_minutes > 0
            else 0.0
        )

        burn_rate_1h = self.calculate_burn_rates().get("1h", 0.0)

        return {
            "remaining_minutes": round(remaining_minutes, 2),
            "consumed_minutes": round(consumed_minutes, 2),
            "total_budget_minutes": round(total_budget_minutes, 2),
            "remaining_percent": round(remaining_percent, 2),
            "burn_rate_1h": round(burn_rate_1h, 3),
            "on_track": remaining_percent > 0,
        }

    def calculate_burn_rates(self) -> dict[str, float]:
        """
        Calculate SLO burn rates for 1h, 6h, and 24h windows.
        Burn rate = actual error rate / allowed error rate.
        A burn rate of 1.0 means error budget will be exhausted exactly on schedule.
        """
        allowed_error = 100.0 - self.slo_target  # e.g. 0.5 for 99.5%

        burn_rates: dict[str, float] = {}
        for label, window in [("1h", "1h"), ("6h", "6h"), ("24h", "24h")]:
            if self._live:
                val = self._prom.query(
                    self._PROMQL_ERROR_RATE.format(window=window)
                )
            else:
                # Simulate realistic burn rates
                import random
                random.seed(int(time.time() / 3600) + hash(label))
                base_error = max(0.0, (100.0 - self.slo_target + random.uniform(-0.2, 0.4)))
                val = base_error

            if val is not None and allowed_error > 0:
                burn_rates[label] = round(val / allowed_error, 3)
            else:
                burn_rates[label] = 0.0

        return burn_rates

    def calculate_p99_latency(self) -> float:
        """Return P99 request latency in milliseconds."""
        if self._live:
            val = self._prom.query(
                self._PROMQL_P99_LATENCY.format(window=self.window)
            )
            if val is not None:
                return round(val, 1)

        # Simulate: normally distributed around 120ms
        import random
        random.seed(int(time.time() / 3600))
        return round(max(10.0, random.gauss(120.0, 40.0)), 1)

    def calculate_rps(self) -> float:
        """Return current requests per second."""
        if self._live:
            val = self._prom.query(self._PROMQL_RPS.format(window="1m"))
            if val is not None:
                return round(val, 2)

        import random
        random.seed(int(time.time() / 60))
        return round(random.uniform(80, 350), 2)

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def generate_report(self) -> dict:
        """Collect all SLO metrics into a single report dict."""
        availability = self.calculate_availability()
        error_budget = self.calculate_error_budget()
        burn_rates = self.calculate_burn_rates()
        p99 = self.calculate_p99_latency()
        rps = self.calculate_rps()

        error_percent = round(100.0 - availability, 4)
        slo_met = availability >= self.slo_target

        # Derive status from 1h burn rate
        br1h = burn_rates.get("1h", 0)
        if br1h >= 14.4:    # Will exhaust 30-day budget in 2 hours
            alert_level = "CRITICAL"
        elif br1h >= 6.0:   # Will exhaust 30-day budget in 5 hours
            alert_level = "WARNING"
        elif br1h >= 3.0:
            alert_level = "ELEVATED"
        else:
            alert_level = "NORMAL"

        return {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "window": self.window,
            "prometheus_url": self.prometheus_url,
            "prometheus_live": self._live,
            "slo_target_percent": self.slo_target,
            "availability_percent": availability,
            "error_rate_percent": error_percent,
            "slo_met": slo_met,
            "alert_level": alert_level,
            "error_budget": error_budget,
            "burn_rates": burn_rates,
            "p99_latency_ms": p99,
            "requests_per_second": rps,
            "latency_slo_met": p99 <= 500.0,
        }

    def generate_multi_window_report(self) -> dict:
        """Generate reports for all standard windows."""
        windows = [1, 6, 24, 168, 720]  # hours
        reports = {}
        for h in windows:
            label = f"{h}h" if h < 24 else (f"{h // 24}d" if h < 720 else "30d")
            calc = SLOCalculator(
                prometheus_url=self.prometheus_url,
                slo_target=self.slo_target,
                window_hours=h,
            )
            reports[label] = calc.generate_report()
        return reports

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def print_report(self, report: dict, title: Optional[str] = None) -> None:
        """Print a formatted, colourised SLO report to stdout."""
        w = 62
        sep = "─" * w

        avail = report["availability_percent"]
        slo_met = report["slo_met"]
        alert = report["alert_level"]
        eb = report["error_budget"]
        br = report["burn_rates"]
        p99 = report["p99_latency_ms"]

        avail_colour = _C.GREEN if slo_met else _C.RED
        alert_colour = {
            "NORMAL": _C.GREEN,
            "ELEVATED": _C.BLUE,
            "WARNING": _C.YELLOW,
            "CRITICAL": _C.RED,
        }.get(alert, _C.RESET)
        budget_colour = _C.GREEN if eb["remaining_percent"] > 20 else (
            _C.YELLOW if eb["remaining_percent"] > 0 else _C.RED
        )

        def row(label: str, value: str, colour: str = _C.RESET) -> None:
            label_w = 30
            print(f"  {_colour(label.ljust(label_w), _C.DIM)}{_colour(value, colour)}")

        print()
        hdr = title or f"CloudPilot SLO Report — window: {report['window']}"
        print(_colour(f"  {hdr}", _C.BOLD, _C.CYAN))
        print(_colour(f"  {sep}", _C.DIM))

        row("Generated At", report["generated_at"])
        row("Prometheus", report["prometheus_url"] + (" ✓" if report["prometheus_live"] else " ✗ (simulated)"))
        print()

        row("SLO Target", f"{report['slo_target_percent']}%")
        row("Availability", f"{avail:.4f}%  {'✓ SLO MET' if slo_met else '✗ SLO BREACHED'}", avail_colour)
        row("Error Rate", f"{report['error_rate_percent']:.4f}%")
        row("Alert Level", alert, alert_colour)
        print()

        row("P99 Latency", f"{p99:.1f} ms  {'✓' if report['latency_slo_met'] else '✗ >500ms'}")
        row("Requests/sec", str(report["requests_per_second"]))
        print()

        print(_colour(f"  {'Error Budget':}", _C.BOLD))
        row("  Total Budget", f"{eb['total_budget_minutes']:.1f} min")
        row("  Consumed", f"{eb['consumed_minutes']:.1f} min")
        row("  Remaining", f"{eb['remaining_minutes']:.1f} min ({eb['remaining_percent']:.1f}%)", budget_colour)
        print()

        print(_colour("  Burn Rates", _C.BOLD))
        for label, rate in br.items():
            br_colour = _C.RED if rate >= 14.4 else (_C.YELLOW if rate >= 6 else _C.GREEN)
            indicator = " 🔥" if rate >= 14.4 else (" ⚠" if rate >= 6 else "  ")
            row(f"  {label} burn rate", f"{rate:.3f}×{indicator}", br_colour)

        print(_colour(f"  {sep}", _C.DIM))
        print()


def print_multi_window_report(reports: dict, slo_target: float) -> None:
    """Print a compact summary table for all windows."""
    print()
    print(_colour("  CloudPilot SLO — Multi-Window Summary", _C.BOLD, _C.CYAN))
    print()

    col_w = [8, 14, 14, 12, 12, 14, 12]
    headers = ["Window", "Availability", "Error Rate", "P99 (ms)", "RPS", "Burn Rate 1h", "Status"]

    header_row = "".join(h.ljust(col_w[i]) for i, h in enumerate(headers))
    print("  " + _colour(header_row, _C.BOLD))
    print("  " + "─" * sum(col_w))

    for window, r in reports.items():
        avail = r["availability_percent"]
        slo_met = avail >= slo_target
        br1h = r["burn_rates"].get("1h", 0)
        status = "✓ OK" if slo_met else "✗ BREACH"
        status_c = _C.GREEN if slo_met else _C.RED

        cells = [
            window,
            f"{avail:.4f}%",
            f"{r['error_rate_percent']:.4f}%",
            f"{r['p99_latency_ms']:.0f}",
            f"{r['requests_per_second']:.0f}",
            f"{br1h:.3f}×",
            status,
        ]
        row_str = "".join(c.ljust(col_w[i]) for i, c in enumerate(cells[:-1]))
        row_str += _colour(cells[-1], status_c)
        print("  " + row_str)

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slo_calculator",
        description="CloudPilot SLO Calculator — query Prometheus for SLO metrics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--prometheus-url",
        default="http://localhost:9090",
        metavar="URL",
        help="Prometheus base URL (default: http://localhost:9090)",
    )
    parser.add_argument(
        "--window",
        default="24h",
        choices=list(_WINDOW_SECONDS.keys()),
        help="Lookback window (default: 24h)",
    )
    parser.add_argument(
        "--slo-target",
        type=float,
        default=99.5,
        metavar="PERCENT",
        help="SLO target percentage (default: 99.5)",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a multi-window report (1h, 6h, 24h, 7d, 30d)",
    )
    parser.add_argument(
        "--watch",
        type=int,
        metavar="SECONDS",
        help="Continuously refresh every N seconds (Ctrl-C to exit)",
    )
    return parser


def _run(args: argparse.Namespace) -> None:
    window_hours = _WINDOW_SECONDS[args.window] // 3600

    calc = SLOCalculator(
        prometheus_url=args.prometheus_url,
        slo_target=args.slo_target,
        window_hours=window_hours,
    )

    if args.report:
        multi = calc.generate_multi_window_report()
        if args.output == "json":
            print(json.dumps(multi, indent=2))
        else:
            print_multi_window_report(multi, args.slo_target)
            # Also print detailed report for primary window
            calc.print_report(multi.get(args.window, multi[list(multi)[2]]))
    else:
        report = calc.generate_report()
        if args.output == "json":
            print(json.dumps(report, indent=2))
        else:
            calc.print_report(report)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                # Clear screen (ANSI)
                if sys.stdout.isatty():
                    print("\033[2J\033[H", end="")
                _run(args)
                print(_colour(f"  Auto-refresh every {args.watch}s — Ctrl-C to exit", _C.DIM))
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n  Exiting watch mode.")
    else:
        _run(args)


if __name__ == "__main__":
    main()
