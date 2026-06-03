"""
tests/test_health.py
────────────────────
Unit tests for the health check endpoints.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_health_check(client: AsyncClient) -> None:
    """Test GET /health returns 200 and version info."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data


async def test_readiness_check(client: AsyncClient) -> None:
    """Test GET /health/ready returns database connection status."""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["database"] == "ok"
