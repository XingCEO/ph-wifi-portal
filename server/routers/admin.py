from __future__ import annotations

import base64
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import AccessGrant, AdView, DirectAdvertiser, Hotspot, Visit, get_db
from models.schemas import (
    DirectAdvertiserCreate,
    DirectAdvertiserResponse,
    HotspotCreate,
    HotspotResponse,
    RevenueResponse,
    StatsResponse,
    HotspotStats,
)
from services.omada import OmadaError, get_omada_client
from services.redis_service import RedisService, get_redis

router = APIRouter(prefix="/admin")
logger = structlog.get_logger(__name__)


def verify_basic_auth(request: Request) -> None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    if not (
        secrets.compare_digest(username, settings.admin_username)
        and secrets.compare_digest(password, settings.admin_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )


DASHBOARD_HTML = """<!DOCTYPE html>
<html><head><title>WiFi Admin</title></head>
<body><h1>WiFi Portal Admin Dashboard</h1>
<div id="stats"></div>
<script>
fetch("/admin/api/stats").then(r=>r.json()).then(d=>{
  document.getElementById("stats").innerHTML = JSON.stringify(d,null,2).replace(/\n/g,"<br>");
});
</script></body></html>"""


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    verify_basic_auth(request)
    return HTMLResponse(content=DASHBOARD_HTML, status_code=200)


@router.get("/api/stats", response_model=StatsResponse)
async def get_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> StatsResponse:
    verify_basic_auth(request)
    today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    visits_result = await db.execute(select(func.count(Visit.id)).where(Visit.visited_at >= today_start))
    total_visits: int = visits_result.scalar_one() or 0

    adviews_result = await db.execute(select(func.count(AdView.id)).where(AdView.viewed_at >= today_start))
    total_ad_views: int = adviews_result.scalar_one() or 0

    revenue_result = await db.execute(select(func.sum(AdView.estimated_revenue_usd)).where(AdView.viewed_at >= today_start))
    total_revenue_usd: Decimal = revenue_result.scalar_one() or Decimal("0.0000")

    grants_result = await db.execute(select(func.count(AccessGrant.id)).where(AccessGrant.granted_at >= today_start))
    total_access_grants: int = grants_result.scalar_one() or 0

    hotspots_result = await db.execute(select(Hotspot).where(Hotspot.is_active == True))
    hotspots = hotspots_result.scalars().all()

    redis_svc = RedisService(redis)
    hotspot_stats: list[HotspotStats] = []
    active_users_total = 0

    for hotspot in hotspots:
        hv = await db.execute(select(func.count(Visit.id)).where(Visit.hotspot_id == hotspot.id, Visit.visited_at >= today_start))
        hav = await db.execute(select(func.count(AdView.id)).where(AdView.hotspot_id == hotspot.id, AdView.viewed_at >= today_start))
        hr = await db.execute(select(func.sum(AdView.estimated_revenue_usd)).where(AdView.hotspot_id == hotspot.id, AdView.viewed_at >= today_start))
        active = await redis_svc.get_active_users_count(hotspot.id)
        active_users_total += active
        hotspot_stats.append(HotspotStats(
            hotspot_id=hotspot.id,
            hotspot_name=hotspot.name,
            visits_today=hv.scalar_one() or 0,
            ad_views_today=hav.scalar_one() or 0,
            revenue_today_usd=hr.scalar_one() or Decimal("0.0000"),
            active_users=active,
        ))

    return StatsResponse(
        date=today_start.strftime("%Y-%m-%d"),
        total_visits=total_visits,
        total_ad_views=total_ad_views,
        total_revenue_usd=total_revenue_usd,
        total_access_grants=total_access_grants,
        active_users_total=active_users_total,
        hotspots=hotspot_stats,
    )


@router.get("/api/hotspots", response_model=list[HotspotResponse])
async def list_hotspots(request: Request, db: AsyncSession = Depends(get_db)) -> list[HotspotResponse]:
    verify_basic_auth(request)
    result = await db.execute(select(Hotspot))
    return [HotspotResponse.model_validate(h) for h in result.scalars().all()]


@router.post("/api/hotspots", response_model=HotspotResponse, status_code=201)
async def create_hotspot(request: Request, body: HotspotCreate, db: AsyncSession = Depends(get_db)) -> HotspotResponse:
    verify_basic_auth(request)
    existing = await db.execute(select(Hotspot).where((Hotspot.name == body.name) | (Hotspot.ap_mac == body.ap_mac)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hotspot with this name or AP MAC already exists")
    now = datetime.now(tz=timezone.utc)
    hotspot = Hotspot(name=body.name, location=body.location, ap_mac=body.ap_mac, site_name=body.site_name,
                      latitude=body.latitude, longitude=body.longitude, is_active=body.is_active, created_at=now, updated_at=now)
    db.add(hotspot)
    await db.flush()
    await db.refresh(hotspot)
    await db.commit()
    logger.info("hotspot_created", hotspot_id=hotspot.id)
    return HotspotResponse.model_validate(hotspot)


@router.get("/api/revenue", response_model=RevenueResponse)
async def get_revenue(
    request: Request,
    month: str = Query(default="", description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
) -> RevenueResponse:
    verify_basic_auth(request)
    now = datetime.now(tz=timezone.utc)
    period = month if month else now.strftime("%Y-%m")
    try:
        year_s, month_s = period.split("-")
        period_start = datetime(int(year_s), int(month_s), 1, tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    if period_start.month == 12:
        period_end = datetime(period_start.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        period_end = datetime(period_start.year, period_start.month + 1, 1, tzinfo=timezone.utc)

    adcash_r = await db.execute(select(func.sum(AdView.estimated_revenue_usd)).where(AdView.viewed_at >= period_start, AdView.viewed_at < period_end, AdView.ad_network == "adcash"))
    direct_r = await db.execute(select(func.sum(DirectAdvertiser.monthly_fee_php)).where(DirectAdvertiser.is_active == True, DirectAdvertiser.starts_at < period_end))
    total_v = await db.execute(select(func.count(AdView.id)).where(AdView.viewed_at >= period_start, AdView.viewed_at < period_end))

    hotspots_result = await db.execute(select(Hotspot))
    breakdown: list[dict[str, Any]] = []
    for h in hotspots_result.scalars().all():
        hr = await db.execute(select(func.sum(AdView.estimated_revenue_usd)).where(AdView.hotspot_id == h.id, AdView.viewed_at >= period_start, AdView.viewed_at < period_end))
        hv = await db.execute(select(func.count(AdView.id)).where(AdView.hotspot_id == h.id, AdView.viewed_at >= period_start, AdView.viewed_at < period_end))
        breakdown.append({"hotspot_id": h.id, "hotspot_name": h.name, "revenue_usd": str(hr.scalar_one() or Decimal("0.0000")), "ad_views": hv.scalar_one() or 0})

    return RevenueResponse(
        period=period,
        adcash_revenue_usd=adcash_r.scalar_one() or Decimal("0.0000"),
        direct_revenue_php=direct_r.scalar_one() or Decimal("0.00"),
        total_ad_views=total_v.scalar_one() or 0,
        breakdown_by_hotspot=breakdown,
    )


@router.get("/api/live")
async def get_live_users(request: Request, redis: Redis = Depends(get_redis), db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    verify_basic_auth(request)
    hotspots_result = await db.execute(select(Hotspot).where(Hotspot.is_active == True))
    hotspots = hotspots_result.scalars().all()
    redis_svc = RedisService(redis)
    live_data: list[dict[str, Any]] = []
    total = 0
    for hotspot in hotspots:
        count = await redis_svc.get_active_users_count(hotspot.id)
        total += count
        live_data.append({"hotspot_id": hotspot.id, "hotspot_name": hotspot.name, "active_users": count})
    omada_data: list[dict[str, Any]] = []
    try:
        omada = get_omada_client()
        for hotspot in hotspots:
            clients = await omada.get_online_clients(hotspot.site_name)
            omada_data.extend(clients)
    except (OmadaError, RuntimeError):
        pass
    return {"total_active_users": total, "hotspots": live_data, "omada_clients": len(omada_data), "message": f"{total} active user(s) across {len(hotspots)} hotspot(s)"}
