from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from services.omada import OmadaError


def _make_session_data(
    client_mac: str = "AA:BB:CC:11:22:33",
    ap_mac: str = "AA:BB:CC:DD:EE:FF",
    hotspot_id: int = 1,
    site: str = "test-site",
) -> dict[str, Any]:
    return {
        "client_mac": client_mac,
        "ap_mac": ap_mac,
        "ssid_name": "TestWiFi",
        "site": site,
        "radio_id": 0,
        "redirect_url": "https://google.com",
        "hotspot_id": hotspot_id,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def _setup_valid_session(mock_redis: MagicMock, session_data: dict[str, Any]) -> None:
    """Configure mock_redis to return a valid session on consume."""
    pipeline_mock = MagicMock()
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)
    pipeline_mock.get = AsyncMock()
    pipeline_mock.delete = AsyncMock()
    pipeline_mock.execute = AsyncMock(
        return_value=[json.dumps(session_data), 1]
    )
    mock_redis.pipeline = MagicMock(return_value=pipeline_mock)
    mock_redis.exists = AsyncMock(return_value=0)  # anti-spam: not blocked


def _setup_empty_session(mock_redis: MagicMock) -> None:
    """Configure mock_redis to return None (session not found)."""
    pipeline_mock = MagicMock()
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)
    pipeline_mock.get = AsyncMock()
    pipeline_mock.delete = AsyncMock()
    pipeline_mock.execute = AsyncMock(return_value=[None, 0])
    mock_redis.pipeline = MagicMock(return_value=pipeline_mock)


# ─── Tests ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_grant_access_valid_session_returns_200(
    client: AsyncClient,
    mock_redis: MagicMock,
    mock_omada: MagicMock,
) -> None:
    """Valid session → Omada call succeeds → 200 with granted status."""
    session_data = _make_session_data()
    _setup_valid_session(mock_redis, session_data)
    mock_omada.grant_access = AsyncMock(return_value={"status": "success"})

    response = await client.post(
        "/api/grant-access",
        json={"session_id": "test-session-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "granted"
    assert "redirect_url" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_grant_access_redirect_url_matches_session(
    client: AsyncClient,
    mock_redis: MagicMock,
    mock_omada: MagicMock,
) -> None:
    """Redirect URL in response matches the one stored in session."""
    session_data = _make_session_data()
    session_data["redirect_url"] = "https://example.com/welcome"
    _setup_valid_session(mock_redis, session_data)
    mock_omada.grant_access = AsyncMock(return_value={})

    response = await client.post(
        "/api/grant-access",
        json={"session_id": "some-session"},
    )

    assert response.status_code == 200
    assert response.json()["redirect_url"] == "https://example.com/welcome"


@pytest.mark.asyncio
async def test_grant_access_session_not_found_returns_400(
    client: AsyncClient,
    mock_redis: MagicMock,
) -> None:
    """Non-existent session returns 400."""
    _setup_empty_session(mock_redis)

    response = await client.post(
        "/api/grant-access",
        json={"session_id": "nonexistent-session"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_grant_access_session_already_used_returns_400(
    client: AsyncClient,
    mock_redis: MagicMock,
    mock_omada: MagicMock,
) -> None:
    """Second use of same session (already consumed) returns 400."""
    session_data = _make_session_data()
    call_count = 0

    async def consume_once(*args: Any, **kwargs: Any) -> list[Any]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [json.dumps(session_data), 1]
        return [None, 0]

    pipeline_mock = MagicMock()
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)
    pipeline_mock.get = AsyncMock()
    pipeline_mock.delete = AsyncMock()
    pipeline_mock.execute = AsyncMock(side_effect=consume_once)
    mock_redis.pipeline = MagicMock(return_value=pipeline_mock)
    mock_redis.exists = AsyncMock(return_value=0)
    mock_omada.grant_access = AsyncMock(return_value={})

    # First call succeeds
    r1 = await client.post(
        "/api/grant-access",
        json={"session_id": "reuse-session"},
    )
    assert r1.status_code == 200

    # Second call fails
    r2 = await client.post(
        "/api/grant-access",
        json={"session_id": "reuse-session"},
    )
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_grant_access_anti_spam_blocked_returns_429(
    client: AsyncClient,
    mock_redis: MagicMock,
    mock_omada: MagicMock,
) -> None:
    """MAC address that's within anti-spam window returns 429."""
    session_data = _make_session_data()

    pipeline_mock = MagicMock()
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)
    pipeline_mock.get = AsyncMock()
    pipeline_mock.delete = AsyncMock()
    pipeline_mock.execute = AsyncMock(return_value=[json.dumps(session_data), 1])
    mock_redis.pipeline = MagicMock(return_value=pipeline_mock)
    # Anti-spam key exists → blocked
    mock_redis.exists = AsyncMock(return_value=1)

    response = await client.post(
        "/api/grant-access",
        json={"session_id": "spam-session"},
    )

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_grant_access_omada_failure_returns_503(
    client: AsyncClient,
    mock_redis: MagicMock,
    mock_omada: MagicMock,
) -> None:
    """OC200 API failure returns 503."""
    session_data = _make_session_data()
    _setup_valid_session(mock_redis, session_data)
    mock_omada.grant_access = AsyncMock(
        side_effect=OmadaError("Connection refused", error_code=-1)
    )

    response = await client.post(
        "/api/grant-access",
        json={"session_id": "valid-session"},
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_grant_access_missing_session_id_returns_422(
    client: AsyncClient,
) -> None:
    """Missing session_id in body returns 422."""
    response = await client.post(
        "/api/grant-access",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_grant_access_calls_omada_with_correct_params(
    client: AsyncClient,
    mock_redis: MagicMock,
    mock_omada: MagicMock,
) -> None:
    """Omada.grant_access is called with correct MAC and site."""
    session_data = _make_session_data(
        client_mac="BB:CC:DD:EE:FF:00",
        ap_mac="11:22:33:44:55:66",
        site="production-site",
    )
    _setup_valid_session(mock_redis, session_data)
    mock_omada.grant_access = AsyncMock(return_value={})

    await client.post(
        "/api/grant-access",
        json={"session_id": "check-params-session"},
    )

    mock_omada.grant_access.assert_called_once()
    call_kwargs = mock_omada.grant_access.call_args[1]
    assert call_kwargs["client_mac"] == "BB:CC:DD:EE:FF:00"
    assert call_kwargs["ap_mac"] == "11:22:33:44:55:66"
    assert call_kwargs["site"] == "production-site"


@pytest.mark.asyncio
async def test_grant_access_blocked_device_returns_403(
    client: AsyncClient,
    mock_redis: MagicMock,
    mock_omada: MagicMock,
    test_session: Any,
) -> None:
    """Blocked device is rejected with 403."""
    from models.database import BlockedDevice

    # Block the device
    device = BlockedDevice(
        client_mac="AA:BB:CC:11:22:33",
        reason="spam",
        blocked_by="admin",
        is_active=True,
    )
    test_session.add(device)
    await test_session.commit()

    session_data = _make_session_data(client_mac="AA:BB:CC:11:22:33")
    _setup_valid_session(mock_redis, session_data)
    mock_omada.grant_access = AsyncMock(return_value={})

    response = await client.post(
        "/api/grant-access",
        json={"session_id": "blocked-device-session"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_grant_access_records_anti_spam_after_success(
    client: AsyncClient,
    mock_redis: MagicMock,
    mock_omada: MagicMock,
) -> None:
    """Anti-spam is recorded after successful grant."""
    session_data = _make_session_data()
    _setup_valid_session(mock_redis, session_data)
    mock_omada.grant_access = AsyncMock(return_value={})
    mock_redis.set = AsyncMock(return_value=True)

    response = await client.post(
        "/api/grant-access",
        json={"session_id": "record-spam-session"},
    )

    assert response.status_code == 200
    # set called for anti-spam recording
    mock_redis.set.assert_called()
