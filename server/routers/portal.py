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


def _render_template(template: str, context: dict[str, Any]) -> str:
    result = template
    for key, value in context.items():
        # 支援 {{ key }} 和 {{key}} 兩種格式
        result = result.replace(f"{{{{ {key} }}}}", str(value))
        result = result.replace(f"{{{{{key}}}}}", str(value))
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
        raise HTTPException(status_code=400, detail=f"Invalid clientMac format: {clientMac}")
    if not is_valid_mac(apMac):
        log.warning("invalid_ap_mac", mac=apMac)
        raise HTTPException(status_code=400, detail=f"Invalid apMac format: {apMac}")

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
            "location": location,
            "adcash_zone_key": settings.adcash_zone_key,
            "banner_url": "null",
            "click_url": "null",
        },
    )

    return HTMLResponse(content=html, status_code=200)
