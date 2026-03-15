from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.omada import OmadaClient, OmadaError


def _make_response(
    status_code: int = 200,
    body: dict[str, Any] | None = None,
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = body or {"errorCode": 0, "result": {}}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    resp.cookies = MagicMock()
    resp.cookies.get = MagicMock(return_value="test-session-id")
    return resp


@pytest.fixture
def omada_client() -> OmadaClient:
    return OmadaClient()


# ─── Login tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(omada_client: OmadaClient) -> None:
    """Successful login stores session_id and csrf_token."""
    login_response = _make_response(
        body={
            "errorCode": 0,
            "result": {"token": "test-csrf-token"},
        }
    )
    login_response.cookies.get = MagicMock(return_value="test-session-id")

    with patch.object(omada_client._client, "post", return_value=login_response):
        await omada_client._login()

    assert omada_client._csrf_token == "test-csrf-token"


@pytest.mark.asyncio
async def test_login_api_error_raises_omada_error(omada_client: OmadaClient) -> None:
    """Login with errorCode != 0 raises OmadaError."""
    error_response = _make_response(
        body={"errorCode": -1000, "msg": "Invalid credentials"}
    )

    with patch.object(omada_client._client, "post", return_value=error_response):
        with pytest.raises(OmadaError, match="Login failed"):
            await omada_client._login()


@pytest.mark.asyncio
async def test_login_timeout_raises_omada_error(omada_client: OmadaClient) -> None:
    """Login timeout raises OmadaError."""
    with patch.object(
        omada_client._client,
        "post",
        side_effect=httpx.TimeoutException("timeout"),
    ):
        with pytest.raises(OmadaError, match="timed out"):
            await omada_client._login()


@pytest.mark.asyncio
async def test_login_connection_error_raises_omada_error(
    omada_client: OmadaClient,
) -> None:
    """Connection error raises OmadaError."""
    with patch.object(
        omada_client._client,
        "post",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        with pytest.raises(OmadaError, match="connection error"):
            await omada_client._login()


# ─── Grant access tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_grant_access_success(omada_client: OmadaClient) -> None:
    """grant_access returns result dict on success."""
    login_resp = _make_response(
        body={"errorCode": 0, "result": {"token": "csrf"}}
    )
    auth_resp = _make_response(
        body={"errorCode": 0, "result": {"status": "authorized"}}
    )

    with (
        patch.object(omada_client._client, "post", return_value=login_resp),
    ):
        await omada_client._login()

    with patch.object(omada_client._client, "request", return_value=auth_resp):
        result = await omada_client.grant_access(
            client_mac="AA:BB:CC:11:22:33",
            ap_mac="AA:BB:CC:DD:EE:FF",
            ssid_name="TestWiFi",
            radio_id=0,
            site="test-site",
            duration_seconds=3600,
        )

    assert result == {"status": "authorized"}


@pytest.mark.asyncio
async def test_grant_access_session_expired_retries(omada_client: OmadaClient) -> None:
    """When session is expired (errorCode -1006), client re-logins and retries."""
    expired_resp = _make_response(
        body={"errorCode": -1006, "msg": "Session expired"}
    )
    login_resp = _make_response(
        body={"errorCode": 0, "result": {"token": "new-csrf"}}
    )
    success_resp = _make_response(
        body={"errorCode": 0, "result": {"status": "authorized"}}
    )

    # Pre-populate session to skip initial login
    omada_client._session_id = "old-session"
    omada_client._csrf_token = "old-csrf"

    call_count = 0

    async def mock_request(*args: Any, **kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return expired_resp
        return success_resp

    async def mock_post(*args: Any, **kwargs: Any) -> MagicMock:
        return login_resp

    with (
        patch.object(omada_client._client, "request", side_effect=mock_request),
        patch.object(omada_client._client, "post", side_effect=mock_post),
    ):
        result = await omada_client.grant_access(
            client_mac="AA:BB:CC:11:22:33",
            ap_mac="AA:BB:CC:DD:EE:FF",
            ssid_name="TestWiFi",
            radio_id=0,
            site="test-site",
            duration_seconds=3600,
        )

    assert result == {"status": "authorized"}
    assert call_count == 2  # first attempt + retry


@pytest.mark.asyncio
async def test_grant_access_omada_api_error_raises(omada_client: OmadaClient) -> None:
    """Non-session API errors raise OmadaError."""
    omada_client._session_id = "session"
    omada_client._csrf_token = "csrf"

    error_resp = _make_response(
        body={"errorCode": -9999, "msg": "Unknown error"}
    )

    with patch.object(omada_client._client, "request", return_value=error_resp):
        with pytest.raises(OmadaError):
            await omada_client.grant_access(
                client_mac="AA:BB:CC:11:22:33",
                ap_mac="AA:BB:CC:DD:EE:FF",
                ssid_name="TestWiFi",
                radio_id=0,
                site="test-site",
                duration_seconds=3600,
            )


@pytest.mark.asyncio
async def test_grant_access_timeout_raises_omada_error(
    omada_client: OmadaClient,
) -> None:
    """Timeout during grant_access raises OmadaError."""
    omada_client._session_id = "session"
    omada_client._csrf_token = "csrf"

    with patch.object(
        omada_client._client,
        "request",
        side_effect=httpx.TimeoutException("timeout"),
    ):
        with pytest.raises(OmadaError, match="timed out"):
            await omada_client.grant_access(
                client_mac="AA:BB:CC:11:22:33",
                ap_mac="AA:BB:CC:DD:EE:FF",
                ssid_name="TestWiFi",
                radio_id=0,
                site="test-site",
                duration_seconds=3600,
            )


# ─── Get online clients tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_online_clients_returns_list(omada_client: OmadaClient) -> None:
    """get_online_clients returns list of client dicts."""
    omada_client._session_id = "session"
    omada_client._csrf_token = "csrf"

    clients = [
        {"mac": "AA:BB:CC:11:22:33", "ip": "192.168.1.100"},
        {"mac": "DD:EE:FF:44:55:66", "ip": "192.168.1.101"},
    ]
    resp = _make_response(
        body={"errorCode": 0, "result": {"data": clients}}
    )

    with patch.object(omada_client._client, "request", return_value=resp):
        result = await omada_client.get_online_clients("test-site")

    assert len(result) == 2
    assert result[0]["mac"] == "AA:BB:CC:11:22:33"


@pytest.mark.asyncio
async def test_get_online_clients_empty(omada_client: OmadaClient) -> None:
    """get_online_clients returns empty list when no clients."""
    omada_client._session_id = "session"
    omada_client._csrf_token = "csrf"

    resp = _make_response(
        body={"errorCode": 0, "result": {"data": []}}
    )

    with patch.object(omada_client._client, "request", return_value=resp):
        result = await omada_client.get_online_clients("empty-site")

    assert result == []


# ─── Context manager tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_omada_client_context_manager() -> None:
    """OmadaClient works as async context manager."""
    async with OmadaClient() as oc:
        assert oc is not None
