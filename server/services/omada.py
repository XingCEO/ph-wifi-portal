from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from config import settings

logger = structlog.get_logger(__name__)

_OMADA_LOGIN_PATH = "/api/v2/hotspot/login"
_OMADA_AUTH_PATH = "/api/v2/hotspot/extPortal/auth"
_OMADA_CLIENTS_PATH = "/api/v2/hotspot/extPortal/onlineClients"


class OmadaError(Exception):
    def __init__(self, message: str, error_code: int | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code


class OmadaClient:
    def __init__(self) -> None:
        self._base_url = (
            f"https://{settings.omada_host}:{settings.omada_port}"
            f"/{settings.omada_controller_id}"
        )
        self._session_id: str | None = None
        self._csrf_token: str | None = None
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def __aenter__(self) -> "OmadaClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    async def close(self) -> None:
        await self._client.aclose()

    async def _login(self) -> None:
        log = logger.bind(action="omada_login", host=settings.omada_host)
        try:
            resp = await self._client.post(
                f"{self._base_url}{_OMADA_LOGIN_PATH}",
                json={"username": settings.omada_operator, "password": settings.omada_password},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("errorCode", -1) != 0:
                raise OmadaError(f"Login failed: {data.get('msg', 'unknown')}", error_code=data.get("errorCode"))
            result = data.get("result", {})
            self._session_id = result.get("token") or resp.cookies.get("TPOMADA_SESSIONID")
            self._csrf_token = result.get("token")
            log.info("omada_login_success")
        except httpx.TimeoutException as exc:
            log.error("omada_login_timeout", error=str(exc))
            raise OmadaError("Omada login timed out") from exc
        except httpx.RequestError as exc:
            log.error("omada_login_connection_error", error=str(exc))
            raise OmadaError(f"Omada connection error: {exc}") from exc

    async def _ensure_authenticated(self) -> None:
        async with self._lock:
            if not self._session_id or not self._csrf_token:
                await self._login()

    def _auth_headers(self) -> dict[str, str]:
        return {"Csrf-Token": self._csrf_token or ""}

    def _auth_cookies(self) -> dict[str, str]:
        return {"TPOMADA_SESSIONID": self._session_id or ""}

    async def _request_with_retry(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        await self._ensure_authenticated()
        for attempt in range(2):
            try:
                resp = await self._client.request(
                    method,
                    f"{self._base_url}{path}",
                    headers=self._auth_headers(),
                    cookies=self._auth_cookies(),
                    **kwargs,
                )
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
                if data.get("errorCode") == -1006 and attempt == 0:
                    logger.info("omada_session_expired_retry")
                    async with self._lock:
                        self._session_id = None
                        self._csrf_token = None
                    await self._login()
                    continue
                if data.get("errorCode", 0) != 0:
                    raise OmadaError(f"Omada API error: {data.get('msg', 'unknown')}", error_code=data.get("errorCode"))
                return data
            except httpx.TimeoutException as exc:
                raise OmadaError("Omada request timed out") from exc
            except httpx.RequestError as exc:
                raise OmadaError(f"Omada connection error: {exc}") from exc
        raise OmadaError("Omada authentication failed after retry")

    async def grant_access(self, *, client_mac: str, ap_mac: str, ssid_name: str, radio_id: int,
                           site: str, duration_seconds: int, traffic_mb: int = 0) -> dict[str, Any]:
        log = logger.bind(action="omada_grant_access", client_mac=client_mac, ap_mac=ap_mac, site=site)
        try:
            result = await self._request_with_retry(
                "POST", _OMADA_AUTH_PATH,
                json={"clientMac": client_mac, "apMac": ap_mac, "ssidName": ssid_name,
                      "radioId": radio_id, "site": site, "time": duration_seconds, "traffic": traffic_mb},
            )
            log.info("omada_grant_access_success")
            return result.get("result", {})
        except OmadaError:
            log.error("omada_grant_access_failed")
            raise

    async def revoke_access(self, *, client_mac: str, site: str) -> None:
        log = logger.bind(action="omada_revoke_access", client_mac=client_mac, site=site)
        try:
            await self._request_with_retry("DELETE", f"{_OMADA_AUTH_PATH}/{client_mac}", params={"site": site})
            log.info("omada_revoke_access_success")
        except OmadaError:
            log.error("omada_revoke_access_failed")
            raise

    async def get_online_clients(self, site: str) -> list[dict[str, Any]]:
        log = logger.bind(action="omada_get_online_clients", site=site)
        try:
            result = await self._request_with_retry("GET", _OMADA_CLIENTS_PATH, params={"site": site})
            clients: list[dict[str, Any]] = result.get("result", {}).get("data", [])
            log.info("omada_get_online_clients_success", count=len(clients))
            return clients
        except OmadaError:
            log.error("omada_get_online_clients_failed")
            raise


omada_client: OmadaClient | None = None


def get_omada_client() -> OmadaClient:
    if omada_client is None:
        raise RuntimeError("OmadaClient not initialized")
    return omada_client
