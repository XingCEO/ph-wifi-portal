"""Tests for extended auth endpoints: forgot-password, reset-password, profile, upgrade"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.anyio


async def _register(client: AsyncClient, suffix: str) -> dict:
    payload = {
        "email": f"ext_{suffix}@test.com",
        "password": "testpass123",
        "full_name": f"Ext User {suffix}",
        "org_name": f"Ext Org {suffix}",
        "org_slug": f"ext-org-{suffix.replace('_', '-')}",
    }
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ─── Forgot Password ─────────────────────────────────────────────────────────

async def test_forgot_password_existing_user(client: AsyncClient) -> None:
    await _register(client, "forgot1")
    resp = await client.post(
        "/api/auth/forgot-password",
        json={"email": "ext_forgot1@test.com"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "reset_token" in data
    assert data["reset_token"] != "no-user-found"


async def test_forgot_password_nonexistent_user(client: AsyncClient) -> None:
    # Should still return 200 (don't expose whether user exists)
    resp = await client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody_at_all@nowhere.test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reset_token"] == "no-user-found"


async def test_reset_password_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": "totally-invalid-token-xyz", "new_password": "newpass12345"},
    )
    assert resp.status_code == 400


async def test_reset_password_flow(client: AsyncClient) -> None:
    """Full flow: register → forgot (get token from mock) → reset → login"""
    from unittest.mock import AsyncMock
    from services.redis_service import get_redis

    reg = await _register(client, "resetflow")

    # Patch Redis mock to return stored token
    token_resp = await client.post(
        "/api/auth/forgot-password",
        json={"email": "ext_resetflow@test.com"},
    )
    assert token_resp.status_code == 200
    reset_token = token_resp.json()["reset_token"]
    assert reset_token != "no-user-found"

    # Manually inject the token→user_id mapping into mock Redis
    redis = get_redis()
    redis.get = AsyncMock(return_value=str(reg["user_id"]))
    redis.delete = AsyncMock(return_value=1)

    # Now reset
    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "brandnewpass999"},
    )
    assert resp.status_code == 200, resp.text

    # Restore redis mock
    redis.get = AsyncMock(return_value=None)

    # Login with new password
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "ext_resetflow@test.com", "password": "brandnewpass999"},
    )
    assert login_resp.status_code == 200


async def test_reset_password_weak_password(client: AsyncClient) -> None:
    await _register(client, "weakreset")
    token_resp = await client.post(
        "/api/auth/forgot-password",
        json={"email": "ext_weakreset@test.com"},
    )
    reset_token = token_resp.json()["reset_token"]
    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "short"},
    )
    assert resp.status_code == 422  # Pydantic validation


# ─── Profile Update ──────────────────────────────────────────────────────────

async def test_update_profile_name(client: AsyncClient) -> None:
    reg = await _register(client, "profile1")
    token = reg["access_token"]

    resp = await client.patch(
        "/api/auth/profile",
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Updated Name"


async def test_update_profile_no_auth(client: AsyncClient) -> None:
    resp = await client.patch("/api/auth/profile", json={"full_name": "Hacker"})
    assert resp.status_code == 401


async def test_update_profile_password_change(client: AsyncClient) -> None:
    reg = await _register(client, "passchange")
    token = reg["access_token"]

    resp = await client.patch(
        "/api/auth/profile",
        json={
            "current_password": "testpass123",
            "new_password": "newpassword999",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Login with new password
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "ext_passchange@test.com", "password": "newpassword999"},
    )
    assert login_resp.status_code == 200


async def test_update_profile_wrong_current_password(client: AsyncClient) -> None:
    reg = await _register(client, "wrongcurr")
    token = reg["access_token"]

    resp = await client.patch(
        "/api/auth/profile",
        json={
            "current_password": "wrongpassword",
            "new_password": "newpassword999",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_update_profile_duplicate_email(client: AsyncClient) -> None:
    reg1 = await _register(client, "dupeemail1")
    reg2 = await _register(client, "dupeemail2")
    token = reg2["access_token"]

    # Try to change to email1's address
    resp = await client.patch(
        "/api/auth/profile",
        json={"email": "ext_dupeemail1@test.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


# ─── Upgrade Subscription ────────────────────────────────────────────────────

async def test_upgrade_to_pro(client: AsyncClient) -> None:
    reg = await _register(client, "upgrade1")
    token = reg["access_token"]

    resp = await client.post(
        "/api/auth/upgrade",
        json={"plan": "pro"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["plan"] == "pro"


async def test_upgrade_invalid_plan(client: AsyncClient) -> None:
    reg = await _register(client, "upgrade2")
    token = reg["access_token"]

    resp = await client.post(
        "/api/auth/upgrade",
        json={"plan": "ultimate"},  # Invalid
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_upgrade_no_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/upgrade", json={"plan": "pro"})
    assert resp.status_code == 401


# ─── Dashboard Subscription & Billing ────────────────────────────────────────

async def test_get_subscription(client: AsyncClient) -> None:
    reg = await _register(client, "getsub")
    token = reg["access_token"]

    resp = await client.get(
        "/api/dashboard/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "plan" in data
    assert "max_hotspots" in data


async def test_get_billing(client: AsyncClient) -> None:
    reg = await _register(client, "getbill")
    token = reg["access_token"]

    resp = await client.get(
        "/api/dashboard/billing",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_delete_hotspot(client: AsyncClient) -> None:
    reg = await _register(client, "delho")
    token = reg["access_token"]

    # Create hotspot
    hs_resp = await client.post(
        "/api/dashboard/hotspots",
        json={"name": "Del HS", "location": "Somewhere", "ap_mac": "FF:EE:DD:CC:BB:AA", "site_name": "s"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert hs_resp.status_code == 201
    hs_id = hs_resp.json()["id"]

    # Delete it
    del_resp = await client.delete(
        f"/api/dashboard/hotspots/{hs_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 200


async def test_delete_hotspot_not_found(client: AsyncClient) -> None:
    reg = await _register(client, "delho2")
    token = reg["access_token"]

    resp = await client.delete(
        "/api/dashboard/hotspots/999999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_delete_hotspot_wrong_org(client: AsyncClient) -> None:
    """User cannot delete another org's hotspot"""
    reg1 = await _register(client, "delorg1")
    reg2 = await _register(client, "delorg2")

    # Create hotspot for org1
    hs_resp = await client.post(
        "/api/dashboard/hotspots",
        json={"name": "Org1 HS", "location": "loc", "ap_mac": "11:AA:BB:CC:DD:EE", "site_name": "s"},
        headers={"Authorization": f"Bearer {reg1['access_token']}"},
    )
    assert hs_resp.status_code == 201
    hs_id = hs_resp.json()["id"]

    # Try delete with org2's token
    resp = await client.delete(
        f"/api/dashboard/hotspots/{hs_id}",
        headers={"Authorization": f"Bearer {reg2['access_token']}"},
    )
    assert resp.status_code == 404
