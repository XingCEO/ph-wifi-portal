"""Tests for SaaS Dashboard API"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _register_and_token(client: AsyncClient, suffix: str = "") -> str:
    """Helper: register a user and return the access token."""
    payload = {
        "email": f"dashboard{suffix}@test.com",
        "password": "dashpass123",
        "full_name": f"Dashboard User {suffix}",
        "org_name": f"Dash Org {suffix}",
        "org_slug": f"dash-org{suffix}",
    }
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


@pytest.mark.anyio
async def test_stats_no_hotspots(client: AsyncClient) -> None:
    token = await _register_and_token(client, "-stats")
    resp = await client.get(
        "/api/dashboard/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_connections"] == 0
    assert data["active_hotspots"] == 0
    assert data["period_days"] == 30


@pytest.mark.anyio
async def test_list_hotspots_empty(client: AsyncClient) -> None:
    token = await _register_and_token(client, "-lisths")
    resp = await client.get(
        "/api/dashboard/hotspots",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_create_hotspot(client: AsyncClient) -> None:
    token = await _register_and_token(client, "-createhs")
    payload = {
        "name": "My Test Hotspot",
        "location": "Manila, Philippines",
        "ap_mac": "AA:BB:CC:11:22:33",
        "site_name": "Default",
    }
    resp = await client.post(
        "/api/dashboard/hotspots",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "My Test Hotspot"
    assert data["ap_mac"] == "AA:BB:CC:11:22:33"
    assert data["connections_count"] == 0


@pytest.mark.anyio
async def test_create_duplicate_mac(client: AsyncClient) -> None:
    token = await _register_and_token(client, "-duphs")
    payload = {
        "name": "Dup HS",
        "location": "Somewhere",
        "ap_mac": "DD:EE:FF:11:22:33",
        "site_name": "Default",
    }
    await client.post(
        "/api/dashboard/hotspots",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    # Second create with same MAC should fail
    resp = await client.post(
        "/api/dashboard/hotspots",
        json={**payload, "name": "Different name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_create_hotspot_exceeds_plan(client: AsyncClient) -> None:
    token = await _register_and_token(client, "-exceed")
    # Free plan allows max 1 hotspot
    await client.post(
        "/api/dashboard/hotspots",
        json={"name": "HS1", "location": "loc1", "ap_mac": "11:22:33:44:55:66", "site_name": "s"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/api/dashboard/hotspots",
        json={"name": "HS2", "location": "loc2", "ap_mac": "AA:22:33:44:55:66", "site_name": "s"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_dashboard_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/dashboard/stats")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_revenue_empty(client: AsyncClient) -> None:
    token = await _register_and_token(client, "-rev")
    resp = await client.get(
        "/api/dashboard/revenue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_provision_hotspot(client: AsyncClient) -> None:
    token = await _register_and_token(client, "-prov")
    payload = {
        "ap_mac": "CC:DD:EE:11:22:33",
        "hotspot_name": "Provision Test",
        "location": "Cebu City",
        "site_name": "Default",
    }
    resp = await client.post(
        "/api/dashboard/provision",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["success"] is True
    assert data["ap_mac"] == "CC:DD:EE:11:22:33"
    assert len(data["setup_instructions"]) > 0
    assert "hotspot_id" in data


# ─── New endpoints: analytics & daily-trend ───────────────────────────────────

@pytest.mark.anyio
async def test_analytics_no_hotspots(client: AsyncClient) -> None:
    token = await _register_and_token(client, "-analytics")
    resp = await client.get(
        "/api/dashboard/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "hourly_distribution" in data
    assert "device_types" in data
    assert "weekly_trend" in data
    assert len(data["hourly_distribution"]) == 24
    assert len(data["weekly_trend"]) == 7


@pytest.mark.anyio
async def test_analytics_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/dashboard/analytics")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_daily_trend(client: AsyncClient) -> None:
    token = await _register_and_token(client, "-trend")
    resp = await client.get(
        "/api/dashboard/daily-trend?days=7",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 7
    for entry in data:
        assert "date" in entry
        assert "connections" in entry


@pytest.mark.anyio
async def test_daily_trend_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/dashboard/daily-trend")
    assert resp.status_code == 401
