"""
Shared pytest fixtures and test configuration for CloudPilot.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.incidents import incidents_db
from app.routers.items import _populate_sample_items, items_db
from app.routers.simulate import reset_simulation
from app.slo import slo_tracker


@pytest.fixture(autouse=True)
def reset_state():
    """Ensure clean in-memory state before every test."""
    items_db.clear()
    _populate_sample_items()
    incidents_db.clear()
    reset_simulation()
    # Reset SLO tracker entries
    slo_tracker._store.clear()
    for _ in range(20):
        slo_tracker.record_request(is_error=False, latency_ms=10.0)
    yield
    reset_simulation()


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client for FastAPI."""
    with TestClient(app) as test_client:
        yield test_client
