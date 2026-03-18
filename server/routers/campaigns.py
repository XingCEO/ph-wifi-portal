from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import AdView, Campaign, DirectAdvertiser, get_db
from routers.admin import record_audit, verify_basic_auth

router = APIRouter(prefix="/admin")
logger = structlog.get_logger(__name__)


# ── Pydantic schemas ─────────────────────────────────────────────────────


class CampaignCreate(BaseModel):
    advertiser_id: int
    name: str = Field(..., min_length=1, max_length=255)
    objective: str = Field(default="brand_awareness", max_length=50)
    ad_format: str = Field(default="video", max_length=20)
    cpv_php: Decimal = Field(default=Decimal("3.00"))
    listing_fee_php: Decimal = Field(default=Decimal("2000.00"))
    promotion_budget_php: Decimal = Field(default=Decimal("0.00"))
    creative_url: str | None = None
    landing_page_url: str | None = None
    target_sites: list[int] | None = None
    target_hours: list[int] | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    objective: str | None = Field(default=None, max_length=50)
    ad_format: str | None = Field(default=None, max_length=20)
    cpv_php: Decimal | None = None
    listing_fee_php: Decimal | None = None
    promotion_budget_php: Decimal | None = None
    creative_url: str | None = None
    landing_page_url: str | None = None
    target_sites: list[int] | None = None
    target_hours: list[int] | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = Field(default=None, max_length=20)


class CampaignResponse(BaseModel):
    id: int
    advertiser_id: int
    advertiser_name: str | None = None
    name: str
    objective: str
    ad_format: str
    creative_url: str | None
    landing_page_url: str | None
    cpv_php: Decimal
    listing_fee_php: Decimal
    promotion_budget_php: Decimal
    budget_consumed_php: Decimal
    status: str
    target_sites: list[int] | None
    target_hours: list[int] | None
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignReportResponse(BaseModel):
    campaign_id: int
    campaign_name: str
    advertiser_name: str | None
    total_views: int
    verified_views: int
    budget_consumed: Decimal
    budget_remaining: Decimal
    cpv: Decimal
    estimated_completion_date: datetime | None


# ── Valid status transitions ─────────────────────────────────────────────

VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"review", "active"},
    "review": {"approved", "rejected"},
    "approved": {"active"},
    "active": {"paused", "completed"},
    "paused": {"active", "completed"},
    "rejected": {"draft"},
    "completed": set(),
}


# ── Helpers ──────────────────────────────────────────────────────────────


def _campaign_to_response(campaign: Campaign, advertiser_name: str | None = None) -> CampaignResponse:
    return CampaignResponse(
        id=campaign.id,
        advertiser_id=campaign.advertiser_id,
        advertiser_name=advertiser_name,
        name=campaign.name,
        objective=campaign.objective,
        ad_format=campaign.ad_format,
        creative_url=campaign.creative_url,
        landing_page_url=campaign.landing_page_url,
        cpv_php=campaign.cpv_php,
        listing_fee_php=campaign.listing_fee_php,
        promotion_budget_php=campaign.promotion_budget_php,
        budget_consumed_php=campaign.budget_consumed_php,
        status=campaign.status,
        target_sites=campaign.target_sites,
        target_hours=campaign.target_hours,
        starts_at=campaign.starts_at,
        ends_at=campaign.ends_at,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("/api/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    request: Request,
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    verify_basic_auth(request)

    # Verify advertiser exists
    adv_result = await db.execute(
        select(DirectAdvertiser).where(DirectAdvertiser.id == body.advertiser_id)
    )
    advertiser = adv_result.scalar_one_or_none()
    if not advertiser:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advertiser not found")

    now = datetime.now(tz=timezone.utc)
    campaign = Campaign(
        advertiser_id=body.advertiser_id,
        name=body.name,
        objective=body.objective,
        ad_format=body.ad_format,
        cpv_php=body.cpv_php,
        listing_fee_php=body.listing_fee_php,
        promotion_budget_php=body.promotion_budget_php,
        creative_url=body.creative_url,
        landing_page_url=body.landing_page_url,
        target_sites=body.target_sites,
        target_hours=body.target_hours,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        created_at=now,
        updated_at=now,
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    await record_audit(db, request, "create_campaign", "campaign", str(campaign.id), {"name": campaign.name})
    await db.commit()
    logger.info("campaign_created", campaign_id=campaign.id, advertiser_id=body.advertiser_id)
    return _campaign_to_response(campaign, advertiser_name=advertiser.name)


@router.get("/api/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> list[CampaignResponse]:
    verify_basic_auth(request)

    q = (
        select(Campaign, DirectAdvertiser.name.label("advertiser_name"))
        .join(DirectAdvertiser, Campaign.advertiser_id == DirectAdvertiser.id, isouter=True)
        .order_by(Campaign.id.desc())
    )
    if status_filter:
        q = q.where(Campaign.status == status_filter)

    result = await db.execute(q)
    rows = result.all()
    return [_campaign_to_response(row.Campaign, advertiser_name=row.advertiser_name) for row in rows]


@router.get("/api/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)

    result = await db.execute(
        select(Campaign, DirectAdvertiser.name.label("advertiser_name"))
        .join(DirectAdvertiser, Campaign.advertiser_id == DirectAdvertiser.id, isouter=True)
        .where(Campaign.id == campaign_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    campaign = row.Campaign

    # Aggregate ad view stats for this campaign
    views_result = await db.execute(
        select(
            func.count(AdView.id).label("total_views"),
            func.count(AdView.id).filter(AdView.is_verified == True).label("verified_views"),  # noqa: E712
        ).where(AdView.campaign_id == campaign_id)
    )
    stats = views_result.one()

    resp = _campaign_to_response(campaign, advertiser_name=row.advertiser_name).model_dump(mode="json")
    resp["total_views"] = stats.total_views or 0
    resp["verified_views"] = stats.verified_views or 0
    return resp


@router.patch("/api/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    request: Request,
    campaign_id: int,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    verify_basic_auth(request)

    result = await db.execute(
        select(Campaign, DirectAdvertiser.name.label("advertiser_name"))
        .join(DirectAdvertiser, Campaign.advertiser_id == DirectAdvertiser.id, isouter=True)
        .where(Campaign.id == campaign_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    campaign = row.Campaign
    update_data = body.model_dump(exclude_unset=True)

    # Validate status transition if status is being changed
    if "status" in update_data:
        new_status = update_data["status"]
        allowed = VALID_STATUS_TRANSITIONS.get(campaign.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{campaign.status}' to '{new_status}'. "
                       f"Allowed: {sorted(allowed) if allowed else 'none'}",
            )

    for field, value in update_data.items():
        setattr(campaign, field, value)
    campaign.updated_at = datetime.now(tz=timezone.utc)

    await db.flush()
    await db.refresh(campaign)
    await record_audit(db, request, "update_campaign", "campaign", str(campaign_id), update_data)
    await db.commit()
    logger.info("campaign_updated", campaign_id=campaign_id, fields=list(update_data.keys()))
    return _campaign_to_response(campaign, advertiser_name=row.advertiser_name)


@router.get("/api/campaigns/{campaign_id}/report", response_model=CampaignReportResponse)
async def campaign_report(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
) -> CampaignReportResponse:
    verify_basic_auth(request)

    result = await db.execute(
        select(Campaign, DirectAdvertiser.name.label("advertiser_name"))
        .join(DirectAdvertiser, Campaign.advertiser_id == DirectAdvertiser.id, isouter=True)
        .where(Campaign.id == campaign_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    campaign = row.Campaign

    # Ad view stats
    views_result = await db.execute(
        select(
            func.count(AdView.id).label("total_views"),
            func.count(AdView.id).filter(AdView.is_verified == True).label("verified_views"),  # noqa: E712
        ).where(AdView.campaign_id == campaign_id)
    )
    stats = views_result.one()
    total_views = stats.total_views or 0
    verified_views = stats.verified_views or 0

    budget_consumed = campaign.budget_consumed_php
    budget_remaining = campaign.promotion_budget_php - budget_consumed

    # Estimate completion date based on burn rate
    estimated_completion: datetime | None = None
    if campaign.status == "active" and budget_remaining > 0 and campaign.starts_at:
        now = datetime.now(tz=timezone.utc)
        elapsed = (now - campaign.starts_at).total_seconds()
        if elapsed > 0 and budget_consumed > 0:
            burn_rate_per_second = budget_consumed / Decimal(str(elapsed))
            remaining_seconds = budget_remaining / burn_rate_per_second
            estimated_completion = now + timedelta(seconds=float(remaining_seconds))
        elif campaign.ends_at:
            estimated_completion = campaign.ends_at

    return CampaignReportResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        advertiser_name=row.advertiser_name,
        total_views=total_views,
        verified_views=verified_views,
        budget_consumed=budget_consumed,
        budget_remaining=budget_remaining,
        cpv=campaign.cpv_php,
        estimated_completion_date=estimated_completion,
    )
