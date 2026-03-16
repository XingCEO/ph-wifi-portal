from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import Hotspot, Visit, get_db, is_valid_mac
from models.schemas import PortalSessionData
from services.redis_service import RedisService, get_redis

router = APIRouter()
logger = structlog.get_logger(__name__)

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "frontend" / "templates" / "portal.html"
_TEMPLATE_CACHE: str | None = None


def _load_template() -> str:
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None:
        _TEMPLATE_CACHE = TEMPLATE_PATH.read_text(encoding="utf-8")
    return _TEMPLATE_CACHE


import html as html_mod


def _escape_html(value: Any) -> str:
    """Escape HTML special characters to prevent XSS."""
    return html_mod.escape(str(value))


def _render_template(template: str, context: dict[str, Any]) -> str:
    result = template
    for key, value in context.items():
        safe_value = _escape_html(value)
        # 支援 {{ key }} 和 {{key}} 兩種格式
        # Also support {{ key | e }} (explicit escape marker)
        result = result.replace(f"{{{{ {key} | e }}}}", safe_value)
        result = result.replace(f"{{{{ {key} }}}}", safe_value)
        result = result.replace(f"{{{{{key}}}}}", safe_value)
    return result


async def _record_visit(
    client_mac: str,
    hotspot_id: int,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    from models.database import async_session_factory
    try:
        async with async_session_factory() as session:
            visit = Visit(
                client_mac=client_mac,
                hotspot_id=hotspot_id,
                ip_address=ip_address,
                user_agent=user_agent,
                visited_at=datetime.now(tz=timezone.utc),
            )
            session.add(visit)
            await session.commit()
        logger.info("visit_recorded", client_mac=client_mac, hotspot_id=hotspot_id)
    except Exception as exc:
        logger.error("visit_record_failed", error=str(exc))


@router.get("/portal", response_class=HTMLResponse)
async def portal_page(
    request: Request,
    clientMac: str = Query(..., description="Client device MAC address"),
    apMac: str = Query(..., description="Access point MAC address"),
    ssidName: str = Query(..., description="SSID name"),
    site: str = Query(..., description="Omada site name"),
    radioId: int = Query(default=0, description="Radio ID"),
    redirectUrl: str = Query(default="https://google.com", description="Redirect URL after auth"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> HTMLResponse:
    log = logger.bind(action="portal_page", client_mac=clientMac, ap_mac=apMac, site=site)

    if not is_valid_mac(clientMac):
        log.warning("invalid_client_mac", mac=clientMac)
        raise HTTPException(status_code=400, detail="Invalid client MAC address format")
    if not is_valid_mac(apMac):
        log.warning("invalid_ap_mac", mac=apMac)
        raise HTTPException(status_code=400, detail="Invalid access point MAC address format")

    if not redirectUrl.startswith(("http://", "https://")):
        redirectUrl = "https://google.com"

    stmt = select(Hotspot).where(Hotspot.ap_mac == apMac, Hotspot.is_active == True)  # noqa: E712
    result = await db.execute(stmt)
    hotspot = result.scalar_one_or_none()

    if hotspot is None:
        hotspot_id = 0
        hotspot_name = "WiFi Hotspot"
        location = ""
    else:
        hotspot_id = hotspot.id
        hotspot_name = hotspot.name
        location = hotspot.location

    if hotspot_id > 0:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        asyncio.create_task(_record_visit(clientMac, hotspot_id, ip_address, user_agent))

    session_data = PortalSessionData(
        client_mac=clientMac,
        ap_mac=apMac,
        ssid_name=ssidName,
        site=site,
        radio_id=radioId,
        redirect_url=redirectUrl,
        hotspot_id=hotspot_id,
        created_at=datetime.now(tz=timezone.utc).isoformat(),
    )

    redis_svc = RedisService(redis)
    session_id = await redis_svc.create_portal_session(
        data=session_data.model_dump(),
        ttl=settings.session_duration_seconds,
    )

    log.info("portal_session_created", session_id=session_id, hotspot_id=hotspot_id)

    template = _load_template()
    html = _render_template(
        template,
        {
            "session_id": session_id,
            "ad_duration": settings.ad_duration_seconds,
            "redirect_url": redirectUrl,
            "hotspot_name": hotspot_name,
            "ssid_name": ssidName,
            "location": location,
            "adcash_zone_key": settings.adcash_zone_key,
            "banner_url": "null",
            "click_url": "null",
        },
    )

    return HTMLResponse(content=html, status_code=200)


THANKS_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "frontend" / "templates" / "thanks.html"
_THANKS_CACHE: str | None = None


@router.get("/thanks", response_class=HTMLResponse)
async def thanks_page() -> HTMLResponse:
    global _THANKS_CACHE
    if _THANKS_CACHE is None:
        _THANKS_CACHE = THANKS_TEMPLATE_PATH.read_text(encoding="utf-8")
    return HTMLResponse(content=_THANKS_CACHE, status_code=200)


@router.get("/")
async def homepage() -> HTMLResponse:
    """Landing page for Adcash/advertiser review."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Free WiFi Portal — Powered by Smart Ads</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#0a0a0f;color:#e0e0e8;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px}
.logo{font-size:48px;margin-bottom:16px}
h1{font-size:28px;font-weight:800;letter-spacing:-.03em;margin-bottom:8px}
h1 span{color:#00e676}
p{color:#888;font-size:15px;max-width:420px;text-align:center;line-height:1.7;margin-bottom:24px}
.stats{display:flex;gap:32px;margin-bottom:32px}
.stat{text-align:center}
.stat-num{font-size:28px;font-weight:700;color:#00e676}
.stat-label{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.badge{display:inline-block;background:rgba(0,230,118,.1);border:1px solid rgba(0,230,118,.2);color:#00e676;padding:6px 16px;border-radius:20px;font-size:12px;font-weight:600}
</style>
</head>
<body>
<div class="logo">📡</div>
<h1>Free WiFi <span>Portal</span></h1>
<p>A smart captive portal system that connects users to free WiFi in exchange for viewing relevant advertisements. Deployed across public hotspots in Southeast Asia.</p>
<div class="stats">
  <div class="stat"><div class="stat-num">30s</div><div class="stat-label">Ad Duration</div></div>
  <div class="stat"><div class="stat-num">1hr</div><div class="stat-label">Free Access</div></div>
  <div class="stat"><div class="stat-num">100%</div><div class="stat-label">Viewability</div></div>
</div>
<span class="badge">✓ Publisher Platform</span>
</body>
</html>"""
    return HTMLResponse(content=html)
