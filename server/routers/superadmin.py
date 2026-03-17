"""Super Admin API — 全平台管理後台"""
from __future__ import annotations

import base64
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import (
    AccessGrant,
    AdView,
    Hotspot,
    Organization,
    RevenueSplit,
    SaasUser,
    Subscription,
    get_db,
)

router = APIRouter(prefix="/api/superadmin", tags=["superadmin"])
logger = structlog.get_logger(__name__)


# ─── Auth ─────────────────────────────────────────────────────────────────────

def verify_superadmin_auth(request: Request) -> None:
    """Basic Auth with admin_username / admin_password from settings."""
    client_ip = request.client.host if request.client else "unknown"
    if not settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin password not configured",
            headers={"WWW-Authenticate": "Basic realm=SuperAdmin"},
        )
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic realm=SuperAdmin"},
        )
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    valid_user = secrets.compare_digest(username, settings.admin_username)
    valid_pass = secrets.compare_digest(password, settings.admin_password)
    if not (valid_user and valid_pass):
        logger.warning("superadmin_auth_failed", ip=client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SuperAdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    organization_id: int | None
    org_name: str | None
    org_slug: str | None
    plan: str | None
    created_at: datetime


class SuperAdminUserUpdate(BaseModel):
    is_active: bool | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, pattern=r"^(owner|member|admin)$")


class SuperAdminOrgResponse(BaseModel):
    id: int
    name: str
    slug: str
    contact_email: str
    is_active: bool
    user_count: int
    hotspot_count: int
    plan: str | None
    total_revenue_usd: Decimal
    created_at: datetime


class SuperAdminHotspotResponse(BaseModel):
    id: int
    name: str
    location: str
    ap_mac: str
    is_active: bool
    org_id: int | None
    org_name: str | None
    connections_30d: int
    revenue_30d_usd: Decimal
    created_at: datetime


class PlatformStatsResponse(BaseModel):
    total_saas_users: int
    total_organizations: int
    total_hotspots: int
    active_hotspots: int
    total_connections_all_time: int
    total_revenue_usd: Decimal
    monthly_revenue_usd: Decimal
    new_users_this_month: int
    new_orgs_this_month: int


class RevenueReportEntry(BaseModel):
    period: str
    total_revenue_usd: Decimal
    partner_payout_usd: Decimal
    platform_revenue_usd: Decimal
    ad_views_count: int
    connection_count: int


class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    monthly_fee_usd: Decimal = Field(..., ge=Decimal("0"))
    revenue_share_pct: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    max_hotspots: int = Field(..., ge=1, le=1000)
    description: str | None = None


class PlanResponse(BaseModel):
    name: str
    monthly_fee_usd: Decimal
    revenue_share_pct: Decimal
    max_hotspots: int
    description: str | None
    active_subscribers: int


# Built-in plans (not stored in DB, managed here)
PLANS = {
    "free": PlanCreate(name="free", monthly_fee_usd=Decimal("0"), revenue_share_pct=Decimal("70"), max_hotspots=1, description="Free tier — 1 hotspot, 70% revenue share"),
    "starter": PlanCreate(name="starter", monthly_fee_usd=Decimal("9.99"), revenue_share_pct=Decimal("75"), max_hotspots=3, description="Starter — 3 hotspots, 75% revenue share"),
    "pro": PlanCreate(name="pro", monthly_fee_usd=Decimal("29.99"), revenue_share_pct=Decimal("80"), max_hotspots=10, description="Pro — 10 hotspots, 80% revenue share"),
    "enterprise": PlanCreate(name="enterprise", monthly_fee_usd=Decimal("99.99"), revenue_share_pct=Decimal("85"), max_hotspots=100, description="Enterprise — 100 hotspots, 85% revenue share"),
}


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PlatformStatsResponse:
    verify_superadmin_auth(request)

    now = datetime.now(tz=timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Totals
    total_users = (await db.execute(select(func.count(SaasUser.id)))).scalar() or 0
    total_orgs = (await db.execute(select(func.count(Organization.id)))).scalar() or 0
    total_hotspots = (await db.execute(select(func.count(Hotspot.id)))).scalar() or 0
    active_hotspots = (await db.execute(
        select(func.count(Hotspot.id)).where(Hotspot.is_active == True)  # noqa: E712
    )).scalar() or 0
    total_conns = (await db.execute(select(func.count(AccessGrant.id)))).scalar() or 0

    # Revenue
    total_rev_row = await db.execute(
        select(func.coalesce(func.sum(AdView.estimated_revenue_usd), 0))
    )
    total_revenue = Decimal(str(total_rev_row.scalar() or 0))

    monthly_rev_row = await db.execute(
        select(func.coalesce(func.sum(AdView.estimated_revenue_usd), 0)).where(
            AdView.viewed_at >= month_start
        )
    )
    monthly_revenue = Decimal(str(monthly_rev_row.scalar() or 0))

    # New this month
    new_users = (await db.execute(
        select(func.count(SaasUser.id)).where(SaasUser.created_at >= month_start)
    )).scalar() or 0
    new_orgs = (await db.execute(
        select(func.count(Organization.id)).where(Organization.created_at >= month_start)
    )).scalar() or 0

    return PlatformStatsResponse(
        total_saas_users=total_users,
        total_organizations=total_orgs,
        total_hotspots=total_hotspots,
        active_hotspots=active_hotspots,
        total_connections_all_time=total_conns,
        total_revenue_usd=total_revenue,
        monthly_revenue_usd=monthly_revenue,
        new_users_this_month=new_users,
        new_orgs_this_month=new_orgs,
    )


@router.get("/users", response_model=list[SuperAdminUserResponse])
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    db: AsyncSession = Depends(get_db),
) -> list[SuperAdminUserResponse]:
    verify_superadmin_auth(request)

    q = select(SaasUser, Organization).outerjoin(Organization, SaasUser.organization_id == Organization.id)

    if search:
        q = q.where(
            SaasUser.email.ilike(f"%{search}%") | SaasUser.full_name.ilike(f"%{search}%")
        )

    q = q.order_by(SaasUser.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    rows = result.all()

    users = []
    for user, org in rows:
        # Get subscription plan
        plan = None
        if user.organization_id:
            sub_res = await db.execute(
                select(Subscription).where(
                    Subscription.organization_id == user.organization_id,
                    Subscription.status == "active",
                ).order_by(Subscription.starts_at.desc()).limit(1)
            )
            sub = sub_res.scalar_one_or_none()
            plan = sub.plan if sub else None

        users.append(SuperAdminUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            organization_id=user.organization_id,
            org_name=org.name if org else None,
            org_slug=org.slug if org else None,
            plan=plan,
            created_at=user.created_at,
        ))
    return users


@router.get("/users/{user_id}", response_model=SuperAdminUserResponse)
async def get_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuperAdminUserResponse:
    verify_superadmin_auth(request)

    result = await db.execute(
        select(SaasUser, Organization).outerjoin(Organization, SaasUser.organization_id == Organization.id)
        .where(SaasUser.id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    user, org = row
    plan = None
    if user.organization_id:
        sub_res = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == user.organization_id,
                Subscription.status == "active",
            ).order_by(Subscription.starts_at.desc()).limit(1)
        )
        sub = sub_res.scalar_one_or_none()
        plan = sub.plan if sub else None

    return SuperAdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        organization_id=user.organization_id,
        org_name=org.name if org else None,
        org_slug=org.slug if org else None,
        plan=plan,
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}", response_model=SuperAdminUserResponse)
async def update_user(
    user_id: int,
    body: SuperAdminUserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuperAdminUserResponse:
    verify_superadmin_auth(request)

    result = await db.execute(select(SaasUser).where(SaasUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role

    await db.commit()
    await db.refresh(user)
    logger.info("superadmin_user_updated", user_id=user_id)

    org = None
    if user.organization_id:
        org_res = await db.execute(select(Organization).where(Organization.id == user.organization_id))
        org = org_res.scalar_one_or_none()

    plan = None
    if user.organization_id:
        sub_res = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == user.organization_id,
                Subscription.status == "active",
            ).order_by(Subscription.starts_at.desc()).limit(1)
        )
        sub = sub_res.scalar_one_or_none()
        plan = sub.plan if sub else None

    return SuperAdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        organization_id=user.organization_id,
        org_name=org.name if org else None,
        org_slug=org.slug if org else None,
        plan=plan,
        created_at=user.created_at,
    )


@router.get("/organizations", response_model=list[SuperAdminOrgResponse])
async def list_organizations(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[SuperAdminOrgResponse]:
    verify_superadmin_auth(request)

    q = select(Organization).order_by(Organization.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    orgs = result.scalars().all()

    responses = []
    for org in orgs:
        user_count = (await db.execute(
            select(func.count(SaasUser.id)).where(SaasUser.organization_id == org.id)
        )).scalar() or 0

        hotspot_count = (await db.execute(
            select(func.count(Hotspot.id)).where(Hotspot.org_id == org.id)
        )).scalar() or 0

        total_rev = (await db.execute(
            select(func.coalesce(func.sum(RevenueSplit.total_revenue_usd), 0)).where(
                RevenueSplit.organization_id == org.id
            )
        )).scalar() or Decimal("0")

        sub_res = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == org.id,
                Subscription.status == "active",
            ).order_by(Subscription.starts_at.desc()).limit(1)
        )
        sub = sub_res.scalar_one_or_none()

        responses.append(SuperAdminOrgResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            contact_email=org.contact_email,
            is_active=org.is_active,
            user_count=user_count,
            hotspot_count=hotspot_count,
            plan=sub.plan if sub else None,
            total_revenue_usd=Decimal(str(total_rev)),
            created_at=org.created_at,
        ))
    return responses


@router.get("/hotspots", response_model=list[SuperAdminHotspotResponse])
async def list_all_hotspots(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    db: AsyncSession = Depends(get_db),
) -> list[SuperAdminHotspotResponse]:
    verify_superadmin_auth(request)

    q = select(Hotspot, Organization).outerjoin(Organization, Hotspot.org_id == Organization.id)
    if search:
        q = q.where(Hotspot.name.ilike(f"%{search}%") | Hotspot.location.ilike(f"%{search}%"))
    q = q.order_by(Hotspot.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(q)
    rows = result.all()

    since = datetime.now(tz=timezone.utc) - timedelta(days=30)
    responses = []
    for hs, org in rows:
        conn_count = (await db.execute(
            select(func.count(AccessGrant.id)).where(
                AccessGrant.hotspot_id == hs.id,
                AccessGrant.granted_at >= since,
            )
        )).scalar() or 0

        rev_row = await db.execute(
            select(func.coalesce(func.sum(AdView.estimated_revenue_usd), 0)).where(
                AdView.hotspot_id == hs.id,
                AdView.viewed_at >= since,
            )
        )
        revenue = Decimal(str(rev_row.scalar() or 0))

        responses.append(SuperAdminHotspotResponse(
            id=hs.id,
            name=hs.name,
            location=hs.location,
            ap_mac=hs.ap_mac,
            is_active=hs.is_active,
            org_id=hs.org_id,
            org_name=org.name if org else None,
            connections_30d=conn_count,
            revenue_30d_usd=revenue,
            created_at=hs.created_at,
        ))
    return responses


@router.get("/revenue", response_model=list[RevenueReportEntry])
async def get_revenue_report(
    request: Request,
    period: str = Query("monthly", pattern=r"^(daily|weekly|monthly)$"),
    limit: int = Query(12, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> list[RevenueReportEntry]:
    verify_superadmin_auth(request)

    now = datetime.now(tz=timezone.utc)
    results = []

    for i in range(limit):
        if period == "daily":
            period_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
            label = period_start.strftime("%Y-%m-%d")
        elif period == "weekly":
            period_start = (now - timedelta(weeks=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(weeks=1)
            label = f"Week of {period_start.strftime('%Y-%m-%d')}"
        else:  # monthly
            month_offset = (now.month - 1 - i) % 12
            year_offset = (now.month - 1 - i) // 12
            year = now.year - year_offset
            month = month_offset + 1
            if year <= 0:
                break
            import calendar
            period_start = datetime(year, month, 1, tzinfo=timezone.utc)
            days_in_month = calendar.monthrange(year, month)[1]
            period_end = datetime(year, month, days_in_month, 23, 59, 59, tzinfo=timezone.utc)
            label = period_start.strftime("%Y-%m")

        rev_row = await db.execute(
            select(func.coalesce(func.sum(AdView.estimated_revenue_usd), 0)).where(
                AdView.viewed_at >= period_start,
                AdView.viewed_at < period_end,
            )
        )
        total_rev = Decimal(str(rev_row.scalar() or 0))

        ad_views_count = (await db.execute(
            select(func.count(AdView.id)).where(
                AdView.viewed_at >= period_start,
                AdView.viewed_at < period_end,
            )
        )).scalar() or 0

        conn_count = (await db.execute(
            select(func.count(AccessGrant.id)).where(
                AccessGrant.granted_at >= period_start,
                AccessGrant.granted_at < period_end,
            )
        )).scalar() or 0

        # Platform keeps 30% on average
        platform_rev = (total_rev * Decimal("30") / 100).quantize(Decimal("0.0001"))
        partner_payout = total_rev - platform_rev

        results.append(RevenueReportEntry(
            period=label,
            total_revenue_usd=total_rev,
            partner_payout_usd=partner_payout,
            platform_revenue_usd=platform_rev,
            ad_views_count=ad_views_count,
            connection_count=conn_count,
        ))

    return results


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[PlanResponse]:
    verify_superadmin_auth(request)

    responses = []
    for plan_name, plan in PLANS.items():
        subscriber_count = (await db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.plan == plan_name,
                Subscription.status == "active",
            )
        )).scalar() or 0

        responses.append(PlanResponse(
            name=plan.name,
            monthly_fee_usd=plan.monthly_fee_usd,
            revenue_share_pct=plan.revenue_share_pct,
            max_hotspots=plan.max_hotspots,
            description=plan.description,
            active_subscribers=subscriber_count,
        ))
    return responses


@router.post("/plans", response_model=PlanResponse, status_code=201)
async def create_or_update_plan(
    body: PlanCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """Upsert a plan definition (in-memory for this implementation)."""
    verify_superadmin_auth(request)

    PLANS[body.name] = body
    logger.info("superadmin_plan_upserted", plan=body.name)

    subscriber_count = (await db.execute(
        select(func.count(Subscription.id)).where(
            Subscription.plan == body.name,
            Subscription.status == "active",
        )
    )).scalar() or 0

    return PlanResponse(
        name=body.name,
        monthly_fee_usd=body.monthly_fee_usd,
        revenue_share_pct=body.revenue_share_pct,
        max_hotspots=body.max_hotspots,
        description=body.description,
        active_subscribers=subscriber_count,
    )
