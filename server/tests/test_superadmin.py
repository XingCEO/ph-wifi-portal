"""Tests for SuperAdmin API"""
from __future__ import annotations

import base64

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

ADMIN_CREDS = base64.b64encode(b"admin:testpass123").decode()
HEADERS = {"Authorization": f"Basic {ADMIN_CREDS}"}
BAD_HEADERS = {"Authorization": "Basic " + base64.b64encode(b"admin:wrongpass").decode()}


# ─── Stats ────────────────────────────────────────────────────────────────────

async def test_platform_stats(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/stats", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "total_saas_users" in data
    assert "total_organizations" in data
    assert "total_hotspots" in data
    assert "total_revenue_usd" in data


async def test_platform_stats_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/stats")
    assert resp.status_code == 401


async def test_platform_stats_bad_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/stats", headers=BAD_HEADERS)
    assert resp.status_code == 401


# ─── Users ────────────────────────────────────────────────────────────────────

async def _register_user(client: AsyncClient, suffix: str) -> dict:
    payload = {
        "email": f"sa_user_{suffix}@test.com",
        "password": "testpass123",
        "full_name": f"SA User {suffix}",
        "org_name": f"SA Org {suffix}",
        "org_slug": f"sa-org-{suffix}",
    }
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def test_list_users(client: AsyncClient) -> None:
    await _register_user(client, "listtest")
    resp = await client.get("/api/superadmin/users", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    user = data[0]
    assert "id" in user
    assert "email" in user
    assert "is_active" in user


async def test_list_users_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/users")
    assert resp.status_code == 401


async def test_get_user_by_id(client: AsyncClient) -> None:
    reg = await _register_user(client, "getbyid")
    user_id = reg["user_id"]
    resp = await client.get(f"/api/superadmin/users/{user_id}", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == user_id
    assert "email" in data


async def test_get_user_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/users/999999", headers=HEADERS)
    assert resp.status_code == 404


async def test_update_user_deactivate(client: AsyncClient) -> None:
    reg = await _register_user(client, "deactivate")
    user_id = reg["user_id"]
    resp = await client.patch(
        f"/api/superadmin/users/{user_id}",
        json={"is_active": False},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_update_user_bad_auth(client: AsyncClient) -> None:
    resp = await client.patch(
        "/api/superadmin/users/1",
        json={"is_active": False},
        headers=BAD_HEADERS,
    )
    assert resp.status_code == 401


# ─── Organizations ────────────────────────────────────────────────────────────

async def test_list_organizations(client: AsyncClient) -> None:
    await _register_user(client, "org1")
    resp = await client.get("/api/superadmin/organizations", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        org = data[0]
        assert "id" in org
        assert "name" in org
        assert "slug" in org


async def test_list_organizations_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/organizations")
    assert resp.status_code == 401


# ─── Hotspots ─────────────────────────────────────────────────────────────────

async def test_list_all_hotspots(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/hotspots", headers=HEADERS)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_hotspots_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/hotspots")
    assert resp.status_code == 401


# ─── Revenue ──────────────────────────────────────────────────────────────────

async def test_revenue_report_monthly(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/revenue?period=monthly&limit=3", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 3


async def test_revenue_report_daily(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/revenue?period=daily&limit=7", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_revenue_report_invalid_period(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/revenue?period=yearly", headers=HEADERS)
    assert resp.status_code == 422


# ─── Plans ────────────────────────────────────────────────────────────────────

async def test_list_plans(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/plans", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 4  # free, starter, pro, enterprise
    plan_names = {p["name"] for p in data}
    assert "free" in plan_names
    assert "pro" in plan_names


async def test_create_plan(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/superadmin/plans",
        json={
            "name": "custom",
            "monthly_fee_usd": "49.99",
            "revenue_share_pct": "82",
            "max_hotspots": 20,
            "description": "Custom plan",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "custom"


async def test_create_plan_no_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/superadmin/plans",
        json={"name": "hack", "monthly_fee_usd": "0", "revenue_share_pct": "100", "max_hotspots": 1},
    )
    assert resp.status_code == 401


async def test_search_users(client: AsyncClient) -> None:
    await _register_user(client, "searchme")
    resp = await client.get("/api/superadmin/users?search=searchme", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert any("searchme" in u["email"] for u in data)


# ─── New endpoints: ads stats, ads daily, sites, activity ─────────────────────

async def test_ads_stats(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/ads/stats", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "adcash_connected" in data
    assert "total_ad_views" in data
    assert "avg_cpm_usd" in data
    assert "monthly_revenue_usd" in data
    assert "top_sites" in data
    assert isinstance(data["top_sites"], list)


async def test_ads_stats_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/ads/stats")
    assert resp.status_code == 401


async def test_ads_daily(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/ads/daily?days=7", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 7
    for entry in data:
        assert "date" in entry
        assert "revenue_usd" in entry
        assert "ad_views" in entry


async def test_ads_daily_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/ads/daily")
    assert resp.status_code == 401


async def test_list_sites(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/sites", headers=HEADERS)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_sites_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/sites")
    assert resp.status_code == 401


async def test_toggle_site_not_found(client: AsyncClient) -> None:
    resp = await client.patch(
        "/api/superadmin/sites/999999",
        json={"is_active": False},
        headers=HEADERS,
    )
    assert resp.status_code == 404


async def test_activity_log(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/activity", headers=HEADERS)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_activity_log_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/superadmin/activity")
    assert resp.status_code == 401
