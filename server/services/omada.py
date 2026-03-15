import httpx
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class OmadaClient:
    def __init__(self):
        self.host = os.getenv("OMADA_HOST", "192.168.1.1")
        self.port = int(os.getenv("OMADA_PORT", "8043"))
        self.controller_id = os.getenv("OMADA_CONTROLLER_ID", "")
        self.operator = os.getenv("OMADA_OPERATOR", "admin")
        self.password = os.getenv("OMADA_PASSWORD", "")
        self.base_url = f"https://{self.host}:{self.port}/{self.controller_id}"
        self._csrf_token: Optional[str] = None
        self._session_cookie: Optional[str] = None

    async def _login(self) -> bool:
        try:
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v2/hotspot/login",
                    json={"name": self.operator, "password": self.password}
                )
                if resp.status_code == 200:
                    self._csrf_token = resp.headers.get("Csrf-Token")
                    self._session_cookie = resp.cookies.get("TPOMADA_SESSIONID")
                    logger.info("Omada login successful")
                    return True
                logger.error(f"Omada login failed: {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Omada login error: {e}")
            return False

    async def grant_access(
        self,
        client_mac: str,
        ap_mac: str,
        ssid_name: str,
        radio_id: int,
        site: str,
        time_seconds: int = 3600
    ) -> bool:
        # Try login if no token
        if not self._csrf_token:
            if not await self._login():
                return False

        payload = {
            "clientMac": client_mac,
            "apMac": ap_mac,
            "ssidName": ssid_name,
            "radioId": radio_id,
            "site": site,
            "time": time_seconds,
            "traffic": 0
        }

        try:
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v2/hotspot/extPortal/auth",
                    headers={
                        "Csrf-Token": self._csrf_token or "",
                        "Cookie": f"TPOMADA_SESSIONID={self._session_cookie}"
                    },
                    json=payload
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("errorCode") == 0:
                        logger.info(f"Access granted for {client_mac}")
                        return True
                # Token expired, retry once
                if resp.status_code in (401, 403):
                    logger.info("Token expired, re-login...")
                    if await self._login():
                        return await self.grant_access(client_mac, ap_mac, ssid_name, radio_id, site, time_seconds)
                logger.error(f"Grant access failed: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Grant access error: {e}")
            return False

omada_client = OmadaClient()
