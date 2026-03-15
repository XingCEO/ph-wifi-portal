from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


VALID_CLIENT_MAC = "AA:BB:CC:11:22:33"
VALID_AP_MAC = "AA:BB:CC:DD:EE:FF"


def _make_portal_url(
    client_mac: str = VALID_CLIENT_MAC,
    ap_mac: str = VALID_AP_MAC,
    ssid: str = "TestWiFi",
    site: str = "test-site",
    radio_id: int = 0,
    redirect_url: str = "https://google.com",
) -> str:
    return (
        f"/portal"
        f"?clientMac={client_mac}"
        f"&apMac={ap_mac}"
        f"&ssidName={ssid}"
        f"&site={site}"
        f"&radioId={radio_id}"
        f"&redirectUrl={redirect_url}"
    )


@pytest.mark.asyncio
async def test_portal_valid_request_returns_200_html(
    client: AsyncClient,
    mock_redis: MagicMock,
) -> None:
    """Normal request to /portal returns 200 with HTML content."""
    mock_redis.setex = AsyncMock(return_value=True)

    response = await client.get(_make_portal_url())

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "WiFi" in response.text or "portal" in response.text.lower()


@pytest.mark.asyncio
async def test_portal_missing_required_params_returns_422(
    client: AsyncClient,
) -> None:
    """Missing required query parameters returns 422."""
    response = await client.get("/portal")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_portal_missing_client_mac_returns_422(
    client: AsyncClient,
) -> None:
    """Missing clientMac returns 422."""
    response = await client.get(
        "/portal?apMac=AA:BB:CC:DD:EE:FF&ssidName=Test&site=s"
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_portal_invalid_client_mac_returns_400(
    client: AsyncClient,
) -> None:
    """Invalid MAC format returns 400."""
    url = _make_portal_url(client_mac="INVALID-MAC")
    response = await client.get(url)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_portal_invalid_ap_mac_returns_400(
    client: AsyncClient,
) -> None:
    """Invalid AP MAC format returns 400."""
    url = _make_portal_url(ap_mac="not-a-mac")
    response = await client.get(url)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_portal_session_created_in_redis(
    client: AsyncClient,
    mock_redis: MagicMock,
) -> None:
    """After valid portal request, a session is created in Redis via setex."""
    mock_redis.setex = AsyncMock(return_value=True)

    response = await client.get(_make_portal_url())

    assert response.status_code == 200
    # Verify setex was called (session creation)
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    # First arg is key (starts with portal_session:)
    key_arg = call_args[0][0] if call_args[0] else call_args[1].get("name", "")
    assert "portal_session:" in str(key_arg)


@pytest.mark.asyncio
async def test_portal_session_data_contains_mac(
    client: AsyncClient,
    mock_redis: MagicMock,
) -> None:
    """Session data stored in Redis contains client MAC."""
    captured_data: list[Any] = []

    async def capture_setex(key: str, ttl: int, value: str) -> bool:
        captured_data.append(json.loads(value))
        return True

    mock_redis.setex = AsyncMock(side_effect=capture_setex)

    await client.get(_make_portal_url(client_mac="AA:BB:CC:11:22:33"))

    assert len(captured_data) == 1
    assert captured_data[0]["client_mac"] == "AA:BB:CC:11:22:33"


@pytest.mark.asyncio
async def test_portal_with_known_hotspot(
    client: AsyncClient,
    mock_redis: MagicMock,
    sample_hotspot: Any,
) -> None:
    """When AP MAC matches a known hotspot, response includes hotspot info."""
    mock_redis.setex = AsyncMock(return_value=True)

    response = await client.get(
        _make_portal_url(ap_mac="AA:BB:CC:DD:EE:FF")
    )

    assert response.status_code == 200
    assert "Test Hotspot" in response.text


@pytest.mark.asyncio
async def test_portal_unknown_hotspot_still_returns_200(
    client: AsyncClient,
    mock_redis: MagicMock,
) -> None:
    """Unknown AP MAC still returns 200 (graceful degradation)."""
    mock_redis.setex = AsyncMock(return_value=True)

    response = await client.get(
        _make_portal_url(ap_mac="00:11:22:33:44:55")
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_portal_response_contains_session_id(
    client: AsyncClient,
    mock_redis: MagicMock,
) -> None:
    """Portal HTML contains the session_id for JavaScript use."""
    session_ids: list[str] = []

    async def capture_setex(key: str, ttl: int, value: str) -> bool:
        # key format: portal_session:{uuid}
        parts = key.split(":")
        if len(parts) == 2:
            session_ids.append(parts[1])
        return True

    mock_redis.setex = AsyncMock(side_effect=capture_setex)

    response = await client.get(_make_portal_url())

    assert response.status_code == 200
    if session_ids:
        assert session_ids[0] in response.text


@pytest.mark.asyncio
async def test_portal_unsafe_redirect_url_sanitized(
    client: AsyncClient,
    mock_redis: MagicMock,
) -> None:
    """Non-http redirect URL gets replaced with safe default."""
    mock_redis.setex = AsyncMock(return_value=True)

    response = await client.get(
        _make_portal_url(redirect_url="javascript:alert(1)")
    )

    assert response.status_code == 200
    assert "javascript:" not in response.text
