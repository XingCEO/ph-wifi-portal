from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_db, AdView, AccessGrant
from models.schemas import GrantAccessRequest, GrantAccessResponse, ErrorResponse
from services.redis_service import get_redis, consume_session, check_anti_spam, record_anti_spam
from services.omada import omada_client
import redis.asyncio as aioredis
import logging
from datetime import datetime, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/grant-access", response_model=GrantAccessResponse)
async def grant_access(
    request: Request,
    body: GrantAccessRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    # 1. Consume session (atomic, prevents replay)
    session = await consume_session(redis, body.session_id)
    if not session:
        raise HTTPException(status_code=400, detail="Invalid or expired session")

    client_mac = session["clientMac"]

    # 2. Anti-spam check
    if not await check_anti_spam(redis, client_mac):
        raise HTTPException(status_code=429, detail="Please wait before requesting again")

    # 3. Grant access via OC200
    success = await omada_client.grant_access(
        client_mac=client_mac,
        ap_mac=session["apMac"],
        ssid_name=session["ssidName"],
        radio_id=session["radioId"],
        site=session["site"],
        time_seconds=3600
    )

    if not success:
        raise HTTPException(status_code=503, detail="Network controller unavailable")

    # 4. Record anti-spam
    await record_anti_spam(redis, client_mac)

    # 5. Log to DB
    expires_at = datetime.utcnow() + timedelta(hours=1)
    try:
        ad_view = AdView(client_mac=client_mac, hotspot_id=1)
        grant = AccessGrant(client_mac=client_mac, hotspot_id=1, expires_at=expires_at)
        db.add(ad_view)
        db.add(grant)
        await db.commit()
    except Exception as e:
        logger.error(f"DB log failed: {e}")

    return GrantAccessResponse(
        status="granted",
        redirect_url=session["redirectUrl"],
        expires_at=expires_at,
        message="Access granted for 1 hour"
    )
