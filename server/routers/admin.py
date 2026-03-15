from __future__ import annotations

import base64
import csv
import io
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import (
    AccessGrant, AdView, AdminAuditLog, BlockedDevice,
    DirectAdvertiser, Hotspot, Visit, get_db,
)
from models.schemas import (
    AuditLogResponse,
    BlockedDeviceCreate,
    BlockedDeviceResponse,
    DirectAdvertiserCreate,
    DirectAdvertiserResponse,
    DirectAdvertiserUpdate,
    HotspotCreate,
    HotspotResponse,
    HotspotUpdate,
    RevenueResponse,
    StatsResponse,
    HotspotStats,
    SystemSettingsResponse,
    SystemSettingsUpdate,
)
from services.omada import OmadaError, get_omada_client
from services.redis_service import RedisService, get_redis

router = APIRouter(prefix="/admin")
logger = structlog.get_logger(__name__)


def verify_basic_auth(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        logger.warning("admin_auth_missing", ip=client_ip, path=request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        logger.warning("admin_auth_decode_failed", ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    if not (
        secrets.compare_digest(username, settings.admin_username)
        and secrets.compare_digest(password, settings.admin_password)
    ):
        logger.warning("admin_auth_failed", ip=client_ip, username=username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )


def _extract_username(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            username, _, _ = decoded.partition(":")
            return username
        except Exception:
            pass
    return "unknown"


async def record_audit(
    db: AsyncSession,
    request: Request,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    log_entry = AdminAuditLog(
        admin_user=_extract_username(request),
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=request.client.host if request.client else None,
    )
    db.add(log_entry)
    try:
        await db.flush()
    except Exception:
        pass


ADMIN_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "frontend" / "templates" / "admin" / "dashboard.html"
_ADMIN_TEMPLATE_CACHE: str | None = None


def _load_admin_template() -> str:
    global _ADMIN_TEMPLATE_CACHE
    if _ADMIN_TEMPLATE_CACHE is None or settings.environment == "development":
        _ADMIN_TEMPLATE_CACHE = ADMIN_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _ADMIN_TEMPLATE_CACHE


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    verify_basic_auth(request)
    return HTMLResponse(content=_load_admin_template(), status_code=200)




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

    hotspots_result = await db.execute(select(Hotspot).where(Hotspot.is_active == True))  # noqa: E712
    hotspots = hotspots_result.scalars().all()

    # Batch queries with GROUP BY instead of N+1
    visits_by_hs = await db.execute(
        select(Visit.hotspot_id, func.count(Visit.id).label("cnt"))
        .where(Visit.visited_at >= today_start)
        .group_by(Visit.hotspot_id)
    )
    visits_map = {row.hotspot_id: row.cnt for row in visits_by_hs.all()}

    adviews_by_hs = await db.execute(
        select(AdView.hotspot_id, func.count(AdView.id).label("cnt"), func.sum(AdView.estimated_revenue_usd).label("rev"))
        .where(AdView.viewed_at >= today_start)
        .group_by(AdView.hotspot_id)
    )
    adviews_map: dict[int, tuple[int, Decimal]] = {}
    for row in adviews_by_hs.all():
        adviews_map[row.hotspot_id] = (row.cnt, row.rev or Decimal("0.0000"))

    redis_svc = RedisService(redis)
    hotspot_stats: list[HotspotStats] = []
    active_users_total = 0

    for hotspot in hotspots:
        active = await redis_svc.get_active_users_count(hotspot.id)
        active_users_total += active
        av_cnt, av_rev = adviews_map.get(hotspot.id, (0, Decimal("0.0000")))
        hotspot_stats.append(HotspotStats(
            hotspot_id=hotspot.id,
            hotspot_name=hotspot.name,
            visits_today=visits_map.get(hotspot.id, 0),
            ad_views_today=av_cnt,
            revenue_today_usd=av_rev,
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
    await record_audit(db, request, "create_hotspot", "hotspot", str(hotspot.id), {"name": hotspot.name})
    await db.commit()
    logger.info("hotspot_created", hotspot_id=hotspot.id)
    return HotspotResponse.model_validate(hotspot)


@router.patch("/api/hotspots/{hotspot_id}", response_model=HotspotResponse)
async def update_hotspot(
    request: Request,
    hotspot_id: int,
    body: HotspotUpdate,
    db: AsyncSession = Depends(get_db),
) -> HotspotResponse:
    verify_basic_auth(request)
    result = await db.execute(select(Hotspot).where(Hotspot.id == hotspot_id))
    hotspot = result.scalar_one_or_none()
    if hotspot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotspot not found")
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(hotspot, field, value)
    hotspot.updated_at = datetime.now(tz=timezone.utc)
    await db.flush()
    await db.refresh(hotspot)
    await record_audit(db, request, "update_hotspot", "hotspot", str(hotspot_id), update_data)
    await db.commit()
    logger.info("hotspot_updated", hotspot_id=hotspot_id, fields=list(update_data.keys()))
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

    # Batch query with GROUP BY instead of N+1
    rev_by_hs = await db.execute(
        select(
            AdView.hotspot_id,
            func.sum(AdView.estimated_revenue_usd).label("rev"),
            func.count(AdView.id).label("cnt"),
        )
        .where(AdView.viewed_at >= period_start, AdView.viewed_at < period_end)
        .group_by(AdView.hotspot_id)
    )
    rev_map = {row.hotspot_id: (row.rev or Decimal("0.0000"), row.cnt) for row in rev_by_hs.all()}

    hotspots_result = await db.execute(select(Hotspot))
    breakdown: list[dict[str, Any]] = []
    for h in hotspots_result.scalars().all():
        rev, cnt = rev_map.get(h.id, (Decimal("0.0000"), 0))
        breakdown.append({"hotspot_id": h.id, "hotspot_name": h.name, "revenue_usd": str(rev), "ad_views": cnt})

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


@router.get("/api/visits")
async def list_visits(
    request: Request,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    hotspot_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    verify_basic_auth(request)
    q = select(Visit, Hotspot.name.label("hotspot_name")).join(
        Hotspot, Visit.hotspot_id == Hotspot.id, isouter=True
    ).order_by(Visit.visited_at.desc()).limit(limit).offset(offset)
    if hotspot_id:
        q = q.where(Visit.hotspot_id == hotspot_id)
    result = await db.execute(q)
    rows = result.all()
    total_q = select(func.count(Visit.id))
    if hotspot_id:
        total_q = total_q.where(Visit.hotspot_id == hotspot_id)
    total = (await db.execute(total_q)).scalar_one()
    return {
        "total": total,
        "items": [
            {
                "id": row.Visit.id,
                "client_mac": row.Visit.client_mac,
                "hotspot_name": row.hotspot_name or "Unknown",
                "ip_address": row.Visit.ip_address,
                "user_agent": row.Visit.user_agent,
                "visited_at": row.Visit.visited_at.isoformat() if row.Visit.visited_at else None,
            }
            for row in rows
        ],
    }


@router.get("/api/security")
async def security_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    verify_basic_auth(request)
    from datetime import timedelta
    now = datetime.now(tz=timezone.utc)
    window_start = now - timedelta(hours=1)
    # 近 1 小時請求量
    recent_visits = await db.execute(
        select(func.count(Visit.id)).where(Visit.visited_at >= window_start)
    )
    # 高頻 MAC（1小時內超過 5 次）
    suspicious = await db.execute(
        select(Visit.client_mac, func.count(Visit.id).label("cnt"))
        .where(Visit.visited_at >= window_start)
        .group_by(Visit.client_mac)
        .having(func.count(Visit.id) > 5)
        .order_by(func.count(Visit.id).desc())
        .limit(20)
    )
    # 今日總量
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_visits = await db.execute(
        select(func.count(Visit.id)).where(Visit.visited_at >= today_start)
    )
    today_ads = await db.execute(
        select(func.count(AdView.id)).where(AdView.viewed_at >= today_start)
    )
    return {
        "today_requests": today_visits.scalar_one() or 0,
        "today_ad_views": today_ads.scalar_one() or 0,
        "last_hour_requests": recent_visits.scalar_one() or 0,
        "suspicious_macs": [
            {"mac": row.client_mac, "count": row.cnt}
            for row in suspicious.all()
        ],
        "rate_limit_active": True,
        "auth_method": "Basic Auth (bcrypt recommended for production)",
    }


# ── Advertiser CRUD ──────────────────────────────────────────────────────


@router.get("/api/advertisers")
async def list_advertisers(
    request: Request, db: AsyncSession = Depends(get_db),
) -> list[DirectAdvertiserResponse]:
    verify_basic_auth(request)
    result = await db.execute(select(DirectAdvertiser).order_by(DirectAdvertiser.id.desc()))
    return [DirectAdvertiserResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/api/advertisers", response_model=DirectAdvertiserResponse, status_code=201)
async def create_advertiser(
    request: Request, body: DirectAdvertiserCreate, db: AsyncSession = Depends(get_db),
) -> DirectAdvertiserResponse:
    verify_basic_auth(request)
    adv = DirectAdvertiser(**body.model_dump())
    db.add(adv)
    await db.flush()
    await db.refresh(adv)
    await record_audit(db, request, "create_advertiser", "advertiser", str(adv.id), {"name": adv.name})
    await db.commit()
    return DirectAdvertiserResponse.model_validate(adv)


@router.patch("/api/advertisers/{adv_id}", response_model=DirectAdvertiserResponse)
async def update_advertiser(
    request: Request, adv_id: int, body: DirectAdvertiserUpdate, db: AsyncSession = Depends(get_db),
) -> DirectAdvertiserResponse:
    verify_basic_auth(request)
    result = await db.execute(select(DirectAdvertiser).where(DirectAdvertiser.id == adv_id))
    adv = result.scalar_one_or_none()
    if not adv:
        raise HTTPException(status_code=404, detail="Advertiser not found")
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(adv, field, value)
    await db.flush()
    await db.refresh(adv)
    await record_audit(db, request, "update_advertiser", "advertiser", str(adv_id), update_data)
    await db.commit()
    return DirectAdvertiserResponse.model_validate(adv)


@router.delete("/api/advertisers/{adv_id}")
async def delete_advertiser(
    request: Request, adv_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    verify_basic_auth(request)
    result = await db.execute(select(DirectAdvertiser).where(DirectAdvertiser.id == adv_id))
    adv = result.scalar_one_or_none()
    if not adv:
        raise HTTPException(status_code=404, detail="Advertiser not found")
    adv.is_active = False
    await record_audit(db, request, "delete_advertiser", "advertiser", str(adv_id), {"name": adv.name})
    await db.commit()
    return {"status": "deactivated"}


# ── Device Management ────────────────────────────────────────────────────


@router.get("/api/devices/blocked")
async def list_blocked_devices(
    request: Request, db: AsyncSession = Depends(get_db),
) -> list[BlockedDeviceResponse]:
    verify_basic_auth(request)
    result = await db.execute(
        select(BlockedDevice).where(BlockedDevice.is_active == True).order_by(BlockedDevice.blocked_at.desc())  # noqa: E712
    )
    return [BlockedDeviceResponse.model_validate(d) for d in result.scalars().all()]


@router.post("/api/devices/block", response_model=BlockedDeviceResponse, status_code=201)
async def block_device(
    request: Request, body: BlockedDeviceCreate, db: AsyncSession = Depends(get_db),
) -> BlockedDeviceResponse:
    verify_basic_auth(request)
    existing = await db.execute(
        select(BlockedDevice).where(BlockedDevice.client_mac == body.client_mac, BlockedDevice.is_active == True)  # noqa: E712
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Device already blocked")
    device = BlockedDevice(
        client_mac=body.client_mac,
        reason=body.reason,
        blocked_by=_extract_username(request),
        expires_at=body.expires_at,
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)
    await record_audit(db, request, "block_device", "device", body.client_mac, {"reason": body.reason})
    await db.commit()
    return BlockedDeviceResponse.model_validate(device)


@router.delete("/api/devices/block/{block_id}")
async def unblock_device(
    request: Request, block_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    verify_basic_auth(request)
    result = await db.execute(select(BlockedDevice).where(BlockedDevice.id == block_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Blocked device not found")
    device.is_active = False
    await record_audit(db, request, "unblock_device", "device", device.client_mac)
    await db.commit()
    return {"status": "unblocked"}


@router.get("/api/devices/{mac}/history")
async def device_history(
    request: Request,
    mac: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    visits_r = await db.execute(
        select(Visit).where(Visit.client_mac == mac).order_by(Visit.visited_at.desc()).limit(50)
    )
    grants_r = await db.execute(
        select(AccessGrant).where(AccessGrant.client_mac == mac).order_by(AccessGrant.granted_at.desc()).limit(50)
    )
    ads_r = await db.execute(
        select(AdView).where(AdView.client_mac == mac).order_by(AdView.viewed_at.desc()).limit(50)
    )
    return {
        "mac": mac,
        "visits": [
            {"id": v.id, "hotspot_id": v.hotspot_id, "ip": v.ip_address, "at": v.visited_at.isoformat()}
            for v in visits_r.scalars().all()
        ],
        "grants": [
            {"id": g.id, "hotspot_id": g.hotspot_id, "granted_at": g.granted_at.isoformat(),
             "expires_at": g.expires_at.isoformat(), "revoked": g.revoked}
            for g in grants_r.scalars().all()
        ],
        "ad_views": [
            {"id": a.id, "hotspot_id": a.hotspot_id, "network": a.ad_network, "at": a.viewed_at.isoformat()}
            for a in ads_r.scalars().all()
        ],
    }


# ── Session Management ───────────────────────────────────────────────────


@router.get("/api/sessions/active")
async def list_active_sessions(
    request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    now = datetime.now(tz=timezone.utc)
    result = await db.execute(
        select(AccessGrant, Hotspot.name.label("hotspot_name"))
        .join(Hotspot, AccessGrant.hotspot_id == Hotspot.id, isouter=True)
        .where(AccessGrant.expires_at > now, AccessGrant.revoked == False)  # noqa: E712
        .order_by(AccessGrant.expires_at.asc())
    )
    rows = result.all()
    items = []
    for row in rows:
        grant = row.AccessGrant
        remaining = (grant.expires_at - now).total_seconds()
        items.append({
            "id": grant.id,
            "client_mac": grant.client_mac,
            "hotspot_name": row.hotspot_name or "Unknown",
            "hotspot_id": grant.hotspot_id,
            "granted_at": grant.granted_at.isoformat(),
            "expires_at": grant.expires_at.isoformat(),
            "remaining_seconds": max(0, int(remaining)),
        })
    avg_remaining = sum(i["remaining_seconds"] for i in items) / len(items) if items else 0
    return {"total": len(items), "avg_remaining_seconds": int(avg_remaining), "items": items}


@router.post("/api/sessions/{grant_id}/revoke")
async def revoke_session(
    request: Request, grant_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    verify_basic_auth(request)
    result = await db.execute(select(AccessGrant).where(AccessGrant.id == grant_id))
    grant = result.scalar_one_or_none()
    if not grant:
        raise HTTPException(status_code=404, detail="Session not found")
    if grant.revoked:
        raise HTTPException(status_code=400, detail="Already revoked")
    grant.revoked = True
    # Try to revoke via Omada
    try:
        hs_result = await db.execute(select(Hotspot).where(Hotspot.id == grant.hotspot_id))
        hotspot = hs_result.scalar_one_or_none()
        if hotspot:
            omada = get_omada_client()
            await omada.revoke_access(client_mac=grant.client_mac, site=hotspot.site_name)
    except (OmadaError, RuntimeError) as exc:
        logger.warning("omada_revoke_failed_on_session_revoke", error=str(exc))
    await record_audit(db, request, "revoke_session", "session", str(grant_id), {"mac": grant.client_mac})
    await db.commit()
    return {"status": "revoked"}


# ── Audit Log ────────────────────────────────────────────────────────────


@router.get("/api/audit-log")
async def list_audit_log(
    request: Request,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    action: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    q = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(limit).offset(offset)
    if action:
        q = q.where(AdminAuditLog.action == action)
    total_q = select(func.count(AdminAuditLog.id))
    if action:
        total_q = total_q.where(AdminAuditLog.action == action)
    result = await db.execute(q)
    total = (await db.execute(total_q)).scalar_one()
    return {
        "total": total,
        "items": [AuditLogResponse.model_validate(r).model_dump(mode="json") for r in result.scalars().all()],
    }


# ── Revenue Daily ────────────────────────────────────────────────────────


@router.get("/api/revenue/daily")
async def revenue_daily(
    request: Request,
    start: str = Query(default="", description="YYYY-MM-DD"),
    end: str = Query(default="", description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    now = datetime.now(tz=timezone.utc)
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc) if start else now - timedelta(days=30)
        end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1) if end else now
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    result = await db.execute(
        select(
            func.date(AdView.viewed_at).label("day"),
            func.count(AdView.id).label("views"),
            func.sum(AdView.estimated_revenue_usd).label("revenue"),
        )
        .where(AdView.viewed_at >= start_dt, AdView.viewed_at < end_dt)
        .group_by(func.date(AdView.viewed_at))
        .order_by(func.date(AdView.viewed_at))
    )
    rows = result.all()
    total_views = sum(r.views for r in rows)
    total_revenue = sum(r.revenue or Decimal("0") for r in rows)
    cpm = (total_revenue / total_views * 1000) if total_views > 0 else Decimal("0")
    return {
        "days": [{"date": str(r.day), "views": r.views, "revenue": str(r.revenue or "0")} for r in rows],
        "total_views": total_views,
        "total_revenue": str(total_revenue),
        "cpm": str(cpm.quantize(Decimal("0.0001")) if isinstance(cpm, Decimal) else cpm),
    }


# ── CSV Exports ──────────────────────────────────────────────────────────


@router.get("/api/export/visits")
async def export_visits(
    request: Request, db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    verify_basic_auth(request)
    result = await db.execute(
        select(Visit, Hotspot.name.label("hotspot_name"))
        .join(Hotspot, Visit.hotspot_id == Hotspot.id, isouter=True)
        .order_by(Visit.visited_at.desc())
        .limit(10000)
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Client MAC", "Hotspot", "IP Address", "User Agent", "Visited At"])
    for row in result.all():
        v = row.Visit
        writer.writerow([v.id, v.client_mac, row.hotspot_name, v.ip_address, v.user_agent,
                         v.visited_at.isoformat() if v.visited_at else ""])
    buf.seek(0)
    await record_audit(db, request, "export_visits")
    await db.commit()
    return StreamingResponse(buf, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=visits.csv"})


@router.get("/api/export/revenue")
async def export_revenue(
    request: Request, db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    verify_basic_auth(request)
    result = await db.execute(
        select(AdView, Hotspot.name.label("hotspot_name"))
        .join(Hotspot, AdView.hotspot_id == Hotspot.id, isouter=True)
        .order_by(AdView.viewed_at.desc())
        .limit(10000)
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Client MAC", "Hotspot", "Network", "Revenue USD", "Viewed At"])
    for row in result.all():
        a = row.AdView
        writer.writerow([a.id, a.client_mac, row.hotspot_name, a.ad_network,
                         str(a.estimated_revenue_usd), a.viewed_at.isoformat() if a.viewed_at else ""])
    buf.seek(0)
    await record_audit(db, request, "export_revenue")
    await db.commit()
    return StreamingResponse(buf, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=revenue.csv"})


@router.get("/api/export/devices")
async def export_blocked_devices(
    request: Request, db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    verify_basic_auth(request)
    result = await db.execute(select(BlockedDevice).order_by(BlockedDevice.blocked_at.desc()))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Client MAC", "Reason", "Blocked By", "Blocked At", "Expires At", "Active"])
    for d in result.scalars().all():
        writer.writerow([d.id, d.client_mac, d.reason, d.blocked_by,
                         d.blocked_at.isoformat() if d.blocked_at else "",
                         d.expires_at.isoformat() if d.expires_at else "", d.is_active])
    buf.seek(0)
    return StreamingResponse(buf, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=blocked_devices.csv"})


# ── Settings ─────────────────────────────────────────────────────────────


@router.get("/api/settings", response_model=SystemSettingsResponse)
async def get_settings(request: Request) -> SystemSettingsResponse:
    verify_basic_auth(request)
    return SystemSettingsResponse(
        ad_duration_seconds=settings.ad_duration_seconds,
        session_duration_seconds=settings.session_duration_seconds,
        anti_spam_window_seconds=settings.anti_spam_window_seconds,
        omada_host=settings.omada_host,
        environment=settings.environment,
        app_name=settings.app_name,
    )


@router.patch("/api/settings")
async def update_settings(
    request: Request, body: SystemSettingsUpdate, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    updated: dict[str, Any] = {}
    if body.ad_duration_seconds is not None:
        settings.ad_duration_seconds = body.ad_duration_seconds
        updated["ad_duration_seconds"] = body.ad_duration_seconds
    if body.session_duration_seconds is not None:
        settings.session_duration_seconds = body.session_duration_seconds
        updated["session_duration_seconds"] = body.session_duration_seconds
    if body.anti_spam_window_seconds is not None:
        settings.anti_spam_window_seconds = body.anti_spam_window_seconds
        updated["anti_spam_window_seconds"] = body.anti_spam_window_seconds
    await record_audit(db, request, "update_settings", "settings", None, updated)
    await db.commit()
    return {"status": "updated", "changes": updated}


@router.post("/api/settings/test-omada")
async def test_omada_connection(request: Request) -> dict[str, Any]:
    verify_basic_auth(request)
    try:
        omada = get_omada_client()
        await omada.get_online_clients("Default")
        return {"status": "ok", "message": "Omada connection successful"}
    except (OmadaError, RuntimeError) as exc:
        return {"status": "error", "message": str(exc)}


# ── Hotspot Delete + Detail ──────────────────────────────────────────────


@router.delete("/api/hotspots/{hotspot_id}")
async def delete_hotspot(
    request: Request, hotspot_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    verify_basic_auth(request)
    result = await db.execute(select(Hotspot).where(Hotspot.id == hotspot_id))
    hotspot = result.scalar_one_or_none()
    if not hotspot:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    await record_audit(db, request, "delete_hotspot", "hotspot", str(hotspot_id), {"name": hotspot.name})
    await db.delete(hotspot)
    await db.commit()
    return {"status": "deleted"}


@router.get("/api/hotspots/{hotspot_id}/detail")
async def hotspot_detail(
    request: Request, hotspot_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    result = await db.execute(select(Hotspot).where(Hotspot.id == hotspot_id))
    hotspot = result.scalar_one_or_none()
    if not hotspot:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    visits_today = (await db.execute(
        select(func.count(Visit.id)).where(Visit.hotspot_id == hotspot_id, Visit.visited_at >= today_start)
    )).scalar_one() or 0
    visits_week = (await db.execute(
        select(func.count(Visit.id)).where(Visit.hotspot_id == hotspot_id, Visit.visited_at >= week_ago)
    )).scalar_one() or 0
    ads_today = (await db.execute(
        select(func.count(AdView.id)).where(AdView.hotspot_id == hotspot_id, AdView.viewed_at >= today_start)
    )).scalar_one() or 0
    # Top devices
    top_devices = await db.execute(
        select(Visit.client_mac, func.count(Visit.id).label("cnt"))
        .where(Visit.hotspot_id == hotspot_id, Visit.visited_at >= week_ago)
        .group_by(Visit.client_mac)
        .order_by(func.count(Visit.id).desc())
        .limit(10)
    )
    # Daily trend
    daily = await db.execute(
        select(func.date(Visit.visited_at).label("day"), func.count(Visit.id).label("cnt"))
        .where(Visit.hotspot_id == hotspot_id, Visit.visited_at >= week_ago)
        .group_by(func.date(Visit.visited_at))
        .order_by(func.date(Visit.visited_at))
    )
    return {
        "hotspot": HotspotResponse.model_validate(hotspot).model_dump(mode="json"),
        "visits_today": visits_today,
        "visits_week": visits_week,
        "ads_today": ads_today,
        "top_devices": [{"mac": r.client_mac, "count": r.cnt} for r in top_devices.all()],
        "daily_trend": [{"date": str(r.day), "count": r.cnt} for r in daily.all()],
    }
