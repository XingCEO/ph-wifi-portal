from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import AccessGrant, AdView, get_db
from models.schemas import (
    ErrorResponse,
    GrantAccessRequest,
    GrantAccessResponse,
    PortalSessionData,
)
from services.omada import OmadaClient, OmadaError, get_omada_client
from services.redis_service import RedisService, get_redis

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post(
    "/api/grant-access",
    response_model=GrantAccessResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def grant_access(
    request: Request,
    body: GrantAccessRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> GrantAccessResponse:
    log = logger.bind(
        action="grant_access",
        session_id=body.session_id,
        request_id=getattr(request.state, "request_id", None),
    )

    redis_svc = RedisService(redis)

    # 1. Atomically consume session
    session_raw = await redis_svc.consume_session(body.session_id)
    if session_raw is None:
        log.warning("session_not_found_or_expired")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session not found or already used")

    try:
        session = PortalSessionData(**session_raw)
    except Exception as exc:
        log.error("session_parse_error", error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session data") from exc

    log = log.bind(client_mac=session.client_mac, hotspot_id=session.hotspot_id)

    # 2. Anti-spam check
    is_allowed = await redis_svc.check_anti_spam(session.client_mac, settings.anti_spam_window_seconds)
    if not is_allowed:
        log.warning("anti_spam_blocked")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many access requests. Please wait before trying again.")

    # 3. Call Omada to grant access
    omada: OmadaClient = get_omada_client()
    try:
        await omada.grant_access(
            client_mac=session.client_mac,
            ap_mac=session.ap_mac,
            ssid_name=session.ssid_name,
            radio_id=session.radio_id,
            site=session.site,
            duration_seconds=settings.session_duration_seconds,
            traffic_mb=0,
        )
    except OmadaError as exc:
        log.error("omada_grant_failed", error=str(exc))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to grant network access. Please try again.") from exc

    # 4. Record AdView + AccessGrant
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(seconds=settings.session_duration_seconds)

    try:
        ad_view = AdView(
            client_mac=session.client_mac,
            hotspot_id=session.hotspot_id if session.hotspot_id > 0 else 1,
            ad_network="adcash" if settings.adcash_zone_key else "direct",
            advertiser_id=None,
            estimated_revenue_usd=0,
            viewed_at=now,
        )
        db.add(ad_view)

        if session.hotspot_id > 0:
            access_grant = AccessGrant(
                client_mac=session.client_mac,
                hotspot_id=session.hotspot_id,
                granted_at=now,
                expires_at=expires_at,
                revoked=False,
            )
            db.add(access_grant)

        await db.commit()
        log.info("access_grant_recorded", expires_at=expires_at.isoformat())
    except Exception as exc:
        log.error("db_record_failed", error=str(exc))
        await db.rollback()

    # 5. Record anti-spam
    await redis_svc.record_anti_spam(session.client_mac, settings.anti_spam_window_seconds)

    # 6. Increment active users
    if session.hotspot_id > 0:
        await redis_svc.increment_active_users(session.hotspot_id, ttl=settings.session_duration_seconds)

    log.info("access_granted", redirect_url=session.redirect_url)

    return GrantAccessResponse(
        status="granted",
        redirect_url=session.redirect_url,
        expires_at=expires_at,
    )
