"""
CloudPilot Pydantic v2 data models.

Defines all request/response schemas used across the application.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Item models
# ---------------------------------------------------------------------------


class Item(BaseModel):
    """Represents a managed cloud resource item."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    name: str = Field(..., min_length=1, max_length=128, description="Item name")
    description: str = Field(default="", description="Human-readable description")
    price: float = Field(..., ge=0.0, description="Cost in USD")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp (UTC)"
    )
    tags: list[str] = Field(default_factory=list, description="Classification tags")

    model_config = {"json_schema_extra": {"example": {"name": "m5.xlarge EC2", "description": "General purpose instance", "price": 0.192, "tags": ["compute", "aws"]}}}


class ItemCreate(BaseModel):
    """Payload for creating a new item."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="")
    price: float = Field(..., ge=0.0)
    tags: list[str] = Field(default_factory=list)


class ItemUpdate(BaseModel):
    """Payload for a full item update (all fields optional for PATCH semantics)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    tags: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Incident models
# ---------------------------------------------------------------------------


class Incident(BaseModel):
    """Represents a reliability incident with SLO impact tracking."""

    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=256)
    severity: Literal["P1", "P2", "P3", "P4"] = Field(
        ..., description="Incident priority tier"
    )
    status: Literal["open", "investigating", "resolved"] = Field(default="open")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    # Timing SLO metrics
    detection_time_seconds: Optional[float] = Field(
        default=None, description="Seconds from start to detection"
    )
    recovery_time_seconds: Optional[float] = Field(
        default=None, description="Seconds from start to resolution (MTTR)"
    )
    slo_impact_percent: Optional[float] = Field(
        default=None, description="Estimated availability impact percentage"
    )
    # AI-generated fields (populated by the AI summary endpoint)
    ai_summary: Optional[str] = None
    ai_root_cause: Optional[str] = None
    ai_remediation: Optional[str] = None


class IncidentCreate(BaseModel):
    """Payload for opening a new incident."""

    title: str = Field(..., min_length=1, max_length=256)
    severity: Literal["P1", "P2", "P3", "P4"]


# ---------------------------------------------------------------------------
# SLO models
# ---------------------------------------------------------------------------


class SLOStatus(BaseModel):
    """SLO health snapshot for a given time window."""

    window: str = Field(..., description="Observation window, e.g. '1h', '24h'")
    availability_percent: float = Field(
        ..., ge=0.0, le=100.0, description="Measured availability in the window"
    )
    error_budget_remaining_percent: float = Field(
        ..., description="Remaining error budget as % of total monthly budget"
    )
    error_budget_consumed_minutes: float = Field(
        ..., ge=0.0, description="Error budget consumed in minutes"
    )
    requests_total: int = Field(..., ge=0)
    errors_total: int = Field(..., ge=0)
    p99_latency_ms: float = Field(..., ge=0.0, description="99th percentile latency")
    slo_target_percent: float = Field(
        ..., description="Configured SLO availability target"
    )
    is_burning_fast: bool = Field(
        ..., description="True when burn rate > 14.4× (1-hour alert)"
    )
    burn_rate: float = Field(..., ge=0.0, description="Current error burn rate")


# ---------------------------------------------------------------------------
# Health models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Kubernetes health-check response."""

    status: Literal["ok", "degraded"] = "ok"
    version: str
    uptime_seconds: float
    pod_name: str


# ---------------------------------------------------------------------------
# Simulation models
# ---------------------------------------------------------------------------


class SimulateRequest(BaseModel):
    """Request payload for triggering a failure simulation."""

    failure_type: Literal["latency", "error_rate", "cpu_stress", "healthy"] = Field(
        ..., description="Type of failure to simulate"
    )
    duration_seconds: int = Field(
        default=30, ge=0, le=3600, description="How long the simulation runs"
    )
    error_rate_percent: int = Field(
        default=50, ge=0, le=100, description="Percentage of requests that will 500"
    )
    latency_ms: int = Field(
        default=5000, ge=0, le=30000, description="Extra latency injected per request"
    )


class SimulateResponse(BaseModel):
    """Response confirming a simulation has been started."""

    message: str
    failure_type: str
    duration_seconds: int
    started_at: datetime


# ---------------------------------------------------------------------------
# Cost models
# ---------------------------------------------------------------------------


class CostEstimate(BaseModel):
    """Cloud cost estimate for a workload configuration."""

    cpu_cores_requested: float = Field(..., ge=0.0)
    memory_gb_requested: float = Field(..., ge=0.0)
    replicas: int = Field(..., ge=1)
    estimated_hourly_usd: float = Field(..., ge=0.0)
    estimated_monthly_usd: float = Field(..., ge=0.0)
    utilization_efficiency_percent: float = Field(..., ge=0.0, le=100.0)
