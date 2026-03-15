from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from models.database import get_db, Visit, AdView, AccessGrant, Hotspot
from datetime import datetime, date
import secrets, os, logging

router = APIRouter()
security = HTTPBasic()
templates = Jinja2Templates(directory="../frontend/templates")
logger = logging.getLogger(__name__)

ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "changeme")

def verify_admin(creds: HTTPBasicCredentials = Depends(security)):
    ok = secrets.compare_digest(creds.username, ADMIN_USER) and \
         secrets.compare_digest(creds.password, ADMIN_PASS)
    if not ok:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return creds.username

@router.get("/admin/", response_class=HTMLResponse)
async def dashboard(request: Request, _=Depends(verify_admin)):
    return templates.TemplateResponse("admin/index.html", {"request": request})

@router.get("/admin/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db), _=Depends(verify_admin)):
    today = date.today()

    visits_q = await db.execute(
        select(func.count(Visit.id)).where(
            cast(Visit.visited_at, Date) == today
        )
    )
    ad_views_q = await db.execute(
        select(func.count(AdView.id)).where(
            cast(AdView.viewed_at, Date) == today
        )
    )
    revenue_q = await db.execute(
        select(func.sum(AdView.estimated_revenue_usd)).where(
            cast(AdView.viewed_at, Date) == today
        )
    )

    return {
        "date": today.isoformat(),
        "total_visits": visits_q.scalar() or 0,
        "total_ad_views": ad_views_q.scalar() or 0,
        "estimated_revenue_usd": float(revenue_q.scalar() or 0),
    }

@router.get("/admin/api/hotspots")
async def list_hotspots(db: AsyncSession = Depends(get_db), _=Depends(verify_admin)):
    result = await db.execute(select(Hotspot).where(Hotspot.is_active == True))
    hotspots = result.scalars().all()
    return [{"id": h.id, "name": h.name, "location": h.location, "ap_mac": h.ap_mac} for h in hotspots]
