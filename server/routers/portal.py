from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import re, logging, asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_db, Visit
from services.redis_service import get_redis, create_portal_session
import redis.asyncio as aioredis
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="../frontend/templates")
logger = logging.getLogger(__name__)
MAC_PATTERN = re.compile(r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')

@router.get("/portal", response_class=HTMLResponse)
async def portal_page(
    request: Request,
    clientMac: str = Query(...),
    apMac: str = Query(...),
    ssidName: str = Query(...),
    site: str = Query(...),
    radioId: int = Query(0),
    redirectUrl: str = Query("https://google.com"),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    # Validate MAC
    if not MAC_PATTERN.match(clientMac):
        return HTMLResponse("<h1>Invalid request</h1>", status_code=400)

    # Create session
    session_data = {
        "clientMac": clientMac.lower(),
        "apMac": apMac.lower(),
        "ssidName": ssidName,
        "site": site,
        "radioId": radioId,
        "redirectUrl": redirectUrl
    }
    session_id = await create_portal_session(redis, session_data)

    # Log visit async (don't block response)
    asyncio.create_task(_log_visit(db, clientMac, request))

    return templates.TemplateResponse("portal.html", {
        "request": request,
        "session_id": session_id,
        "redirect_url": redirectUrl,
        "ssid_name": ssidName,
        "ad_duration": 30
    })

async def _log_visit(db: AsyncSession, client_mac: str, request: Request):
    try:
        visit = Visit(
            client_mac=client_mac.lower(),
            hotspot_id=1,  # Default hotspot
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:500]
        )
        db.add(visit)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log visit: {e}")
