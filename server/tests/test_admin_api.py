from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import (
    AccessGrant, AdView, AdminAuditLog, BlockedDevice,
    DirectAdvertiser, Hotspot, Visit,
)


def _auth_headers() -> dict[str, str]:
    creds = base64.b64encode(b"admin:testpass123").decode()
    return {"Authorization": f"Basic {creds}"}


AUTH = _auth_headers()


# ─── Helpers ────────────────────────────────────────────────────────────


async def _create_hotspot(session: AsyncSession) -> Hotspot:
    now = datetime.now(tz=timezone.utc)
    h = Hotspot(
        name="Test HS", location="Loc", ap_mac="AA:BB:CC:DD:EE:FF",
        site_name="test", is_active=True, created_at=now, updated_at=now,
    )
    session.add(h)
    await session.commit()
    await session.refresh(h)
    return h


async def _create_advertiser(session: AsyncSession) -> DirectAdvertiser:
    now = datetime.now(tz=timezone.utc)
    a = DirectAdvertiser(
        name="Adv1", contact="test@test.com", banner_url="https://b.com/b.png",
        click_url="https://b.com", monthly_fee_php=5000, hotspot_ids=[],
        is_active=True, starts_at=now,
    )
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


# ─── Advertiser CRUD ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_advertisers_empty(client: AsyncClient) -> None:
    r = await client.get("/admin/api/advertisers", headers=AUTH)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_advertiser(client: AsyncClient) -> None:
    now = datetime.now(tz=timezone.utc).isoformat()
    r = await client.post("/admin/api/advertisers", headers={**AUTH, "Content-Type": "application/json"}, json={
        "name": "TestAdv", "banner_url": "https://x.com/b.png", "click_url": "https://x.com",
        "monthly_fee_php": 3000, "starts_at": now,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "TestAdv"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_update_advertiser(client: AsyncClient, test_session: AsyncSession) -> None:
    adv = await _create_advertiser(test_session)
    r = await client.patch(f"/admin/api/advertisers/{adv.id}", headers={**AUTH, "Content-Type": "application/json"},
                           json={"name": "Updated"})
    assert r.status_code == 200
    assert r.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_advertiser(client: AsyncClient, test_session: AsyncSession) -> None:
    adv = await _create_advertiser(test_session)
    r = await client.delete(f"/admin/api/advertisers/{adv.id}", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "deactivated"


# ─── Device Block/Unblock ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_block_device(client: AsyncClient) -> None:
    r = await client.post("/admin/api/devices/block", headers={**AUTH, "Content-Type": "application/json"},
                          json={"client_mac": "11:22:33:44:55:66", "reason": "spam"})
    assert r.status_code == 201
    data = r.json()
    assert data["client_mac"] == "11:22:33:44:55:66"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_block_device_duplicate(client: AsyncClient) -> None:
    await client.post("/admin/api/devices/block", headers={**AUTH, "Content-Type": "application/json"},
                      json={"client_mac": "22:33:44:55:66:77"})
    r = await client.post("/admin/api/devices/block", headers={**AUTH, "Content-Type": "application/json"},
                          json={"client_mac": "22:33:44:55:66:77"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_unblock_device(client: AsyncClient) -> None:
    r1 = await client.post("/admin/api/devices/block", headers={**AUTH, "Content-Type": "application/json"},
                           json={"client_mac": "33:44:55:66:77:88"})
    block_id = r1.json()["id"]
    r = await client.delete(f"/admin/api/devices/block/{block_id}", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "unblocked"


@pytest.mark.asyncio
async def test_list_blocked_devices(client: AsyncClient) -> None:
    r = await client.get("/admin/api/devices/blocked", headers=AUTH)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ─── Device History ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_device_history(client: AsyncClient, test_session: AsyncSession) -> None:
    h = await _create_hotspot(test_session)
    now = datetime.now(tz=timezone.utc)
    test_session.add(Visit(client_mac="AA:BB:CC:11:22:33", hotspot_id=h.id, visited_at=now))
    await test_session.commit()
    r = await client.get("/admin/api/devices/AA:BB:CC:11:22:33/history", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert data["mac"] == "AA:BB:CC:11:22:33"
    assert len(data["visits"]) >= 1


# ─── Sessions ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_active_sessions(client: AsyncClient) -> None:
    r = await client.get("/admin/api/sessions/active", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_revoke_session(
    client: AsyncClient, test_session: AsyncSession, mock_omada: MagicMock,
) -> None:
    h = await _create_hotspot(test_session)
    now = datetime.now(tz=timezone.utc)
    grant = AccessGrant(
        client_mac="AA:BB:CC:11:22:33", hotspot_id=h.id,
        granted_at=now, expires_at=now + timedelta(hours=1), revoked=False,
    )
    test_session.add(grant)
    await test_session.commit()
    await test_session.refresh(grant)
    mock_omada.revoke_access = AsyncMock(return_value=None)
    r = await client.post(f"/admin/api/sessions/{grant.id}/revoke", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_revoke_session_not_found(client: AsyncClient) -> None:
    r = await client.post("/admin/api/sessions/9999/revoke", headers=AUTH)
    assert r.status_code == 404


# ─── Audit Log ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_log_created_on_action(client: AsyncClient) -> None:
    # Creating a blocked device should create an audit entry
    await client.post("/admin/api/devices/block", headers={**AUTH, "Content-Type": "application/json"},
                      json={"client_mac": "44:55:66:77:88:99"})
    r = await client.get("/admin/api/audit-log", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    actions = [item["action"] for item in data["items"]]
    assert "block_device" in actions


# ─── CSV Export ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_visits_csv(client: AsyncClient) -> None:
    r = await client.get("/admin/api/export/visits", headers=AUTH)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_export_revenue_csv(client: AsyncClient) -> None:
    r = await client.get("/admin/api/export/revenue", headers=AUTH)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_export_devices_csv(client: AsyncClient) -> None:
    r = await client.get("/admin/api/export/devices", headers=AUTH)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


# ─── Settings ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_settings(client: AsyncClient) -> None:
    r = await client.get("/admin/api/settings", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert "ad_duration_seconds" in data
    assert "session_duration_seconds" in data


@pytest.mark.asyncio
async def test_update_settings(client: AsyncClient) -> None:
    r = await client.patch("/admin/api/settings", headers={**AUTH, "Content-Type": "application/json"},
                           json={"ad_duration_seconds": 45})
    assert r.status_code == 200
    assert r.json()["changes"]["ad_duration_seconds"] == 45


@pytest.mark.asyncio
async def test_test_omada_connection(client: AsyncClient, mock_omada: MagicMock) -> None:
    mock_omada.get_online_clients = AsyncMock(return_value=[])
    r = await client.post("/admin/api/settings/test-omada", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] in ("ok", "error")


# ─── Hotspot Delete + Detail ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_hotspot(client: AsyncClient, test_session: AsyncSession) -> None:
    h = await _create_hotspot(test_session)
    r = await client.delete(f"/admin/api/hotspots/{h.id}", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_hotspot_detail(client: AsyncClient, test_session: AsyncSession) -> None:
    h = await _create_hotspot(test_session)
    r = await client.get(f"/admin/api/hotspots/{h.id}/detail", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert "visits_today" in data
    assert "top_devices" in data


# ─── Revenue Daily ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revenue_daily(client: AsyncClient) -> None:
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    r = await client.get(f"/admin/api/revenue/daily?start={today}&end={today}", headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert "days" in data
    assert "cpm" in data
