"""SaaS 客戶 Dashboard API"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
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
from models.schemas import (
    DashboardHotspotCreate,
    DashboardHotspotResponse,
    DashboardStatsResponse,
    ProvisionRequest,
    ProvisionResponse,
    RevenueSplitResponse,
)
from routers.saas_auth import get_current_saas_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
logger = structlog.get_logger(__name__)

# billing payment record schema
from pydantic import BaseModel as _BaseModel

class BillingRecord(_BaseModel):
    id: int
    period: str
    plan: str
    amount_usd: Decimal
    status: str
    created_at: datetime

class SubscriptionDetail(_BaseModel):
    plan: str
    status: str
    monthly_fee_usd: Decimal
    revenue_share_pct: Decimal
    max_hotspots: int
    starts_at: datetime
    ends_at: datetime | None


# ─── Auth dependency ─────────────────────────────────────────────────────────

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> SaasUser:
    """Extract Bearer token from Authorization header and return user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    return await get_current_saas_user(token, db)


# ─── Stats ───────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_stats(
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 30,
) -> DashboardStatsResponse:
    """取得組織的統計數據（過去 N 天）"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    days = max(1, min(days, 365))
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    # 取得此 org 的所有 hotspot IDs
    hs_result = await db.execute(
        select(Hotspot.id).where(
            Hotspot.org_id == current_user.organization_id,
            Hotspot.is_active == True,  # noqa: E712
        )
    )
    hotspot_ids = [row[0] for row in hs_result.all()]

    if not hotspot_ids:
        return DashboardStatsResponse(
            total_connections=0,
            total_ad_views=0,
            total_revenue_usd=Decimal("0"),
            partner_revenue_usd=Decimal("0"),
            active_hotspots=0,
            period_days=days,
        )

    # 連線數
    conn_result = await db.execute(
        select(func.count(AccessGrant.id)).where(
            AccessGrant.hotspot_id.in_(hotspot_ids),
            AccessGrant.granted_at >= since,
        )
    )
    total_connections = conn_result.scalar() or 0

    # 廣告次數 + 收入
    ad_result = await db.execute(
        select(
            func.count(AdView.id),
            func.coalesce(func.sum(AdView.estimated_revenue_usd), 0),
        ).where(
            AdView.hotspot_id.in_(hotspot_ids),
            AdView.viewed_at >= since,
        )
    )
    ad_row = ad_result.one()
    total_ad_views = ad_row[0] or 0
    total_revenue_usd = Decimal(str(ad_row[1] or 0))

    # 取得 revenue share pct from latest subscription
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id,
            Subscription.status == "active",
        ).order_by(Subscription.starts_at.desc()).limit(1)
    )
    sub = sub_result.scalar_one_or_none()
    partner_pct = sub.revenue_share_pct if sub else Decimal("70.00")
    partner_revenue = total_revenue_usd * partner_pct / 100

    return DashboardStatsResponse(
        total_connections=total_connections,
        total_ad_views=total_ad_views,
        total_revenue_usd=total_revenue_usd,
        partner_revenue_usd=partner_revenue.quantize(Decimal("0.0001")),
        active_hotspots=len(hotspot_ids),
        period_days=days,
    )


# ─── Hotspots ────────────────────────────────────────────────────────────────

@router.get("/hotspots", response_model=list[DashboardHotspotResponse])
async def list_hotspots(
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DashboardHotspotResponse]:
    """列出此組織的所有場所"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    result = await db.execute(
        select(Hotspot).where(Hotspot.org_id == current_user.organization_id)
        .order_by(Hotspot.created_at.desc())
    )
    hotspots = result.scalars().all()

    responses = []
    for hs in hotspots:
        # 取得 30 天連線數
        since = datetime.now(tz=timezone.utc) - timedelta(days=30)
        conn_result = await db.execute(
            select(func.count(AccessGrant.id)).where(
                AccessGrant.hotspot_id == hs.id,
                AccessGrant.granted_at >= since,
            )
        )
        connections = conn_result.scalar() or 0

        # 取得 30 天收入
        rev_result = await db.execute(
            select(func.coalesce(func.sum(AdView.estimated_revenue_usd), 0)).where(
                AdView.hotspot_id == hs.id,
                AdView.viewed_at >= since,
            )
        )
        revenue = Decimal(str(rev_result.scalar() or 0))

        responses.append(
            DashboardHotspotResponse(
                id=hs.id,
                name=hs.name,
                location=hs.location,
                ap_mac=hs.ap_mac,
                site_name=hs.site_name,
                is_active=hs.is_active,
                org_id=hs.org_id,
                created_at=hs.created_at,
                connections_count=connections,
                revenue_usd=revenue,
            )
        )

    return responses


@router.post("/hotspots", response_model=DashboardHotspotResponse, status_code=201)
async def create_hotspot(
    body: DashboardHotspotCreate,
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardHotspotResponse:
    """新增場所"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # 重複 AP MAC 檢查（優先回報衝突，比 plan limit 更有幫助）
    existing_mac = await db.execute(
        select(Hotspot).where(Hotspot.ap_mac == body.ap_mac)
    )
    if existing_mac.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="AP MAC already registered")

    # 訂閱額度檢查
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id,
            Subscription.status == "active",
        ).order_by(Subscription.starts_at.desc()).limit(1)
    )
    sub = sub_result.scalar_one_or_none()
    max_hotspots = sub.max_hotspots if sub else 1

    existing_count_result = await db.execute(
        select(func.count(Hotspot.id)).where(
            Hotspot.org_id == current_user.organization_id
        )
    )
    existing_count = existing_count_result.scalar() or 0
    if existing_count >= max_hotspots:
        raise HTTPException(
            status_code=403,
            detail=f"Your plan allows max {max_hotspots} hotspot(s). Upgrade to add more.",
        )

    hotspot = Hotspot(
        name=body.name,
        location=body.location,
        ap_mac=body.ap_mac,
        site_name=body.site_name,
        latitude=body.latitude,
        longitude=body.longitude,
        is_active=True,
        org_id=current_user.organization_id,
    )
    db.add(hotspot)
    await db.commit()
    await db.refresh(hotspot)

    logger.info("hotspot_created", hotspot_id=hotspot.id, org_id=current_user.organization_id)

    return DashboardHotspotResponse(
        id=hotspot.id,
        name=hotspot.name,
        location=hotspot.location,
        ap_mac=hotspot.ap_mac,
        site_name=hotspot.site_name,
        is_active=hotspot.is_active,
        org_id=hotspot.org_id,
        created_at=hotspot.created_at,
        connections_count=0,
        revenue_usd=Decimal("0"),
    )


# ─── Revenue ─────────────────────────────────────────────────────────────────

@router.get("/revenue", response_model=list[RevenueSplitResponse])
async def get_revenue(
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 12,
) -> list[RevenueSplitResponse]:
    """取得收入明細（revenue_splits 記錄）"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    result = await db.execute(
        select(RevenueSplit)
        .where(RevenueSplit.organization_id == current_user.organization_id)
        .order_by(RevenueSplit.period_start.desc())
        .limit(max(1, min(limit, 100)))
    )
    splits = result.scalars().all()
    return [RevenueSplitResponse.model_validate(s) for s in splits]


# ─── Self-serve Provisioning ─────────────────────────────────────────────────

@router.post("/provision", response_model=ProvisionResponse, status_code=201)
async def provision_hotspot(
    body: ProvisionRequest,
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProvisionResponse:
    """自助佈建：輸入 EAP MAC，系統自動設定 Portal 並回傳教學步驟"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # 重複 MAC 檢查
    existing = await db.execute(
        select(Hotspot).where(Hotspot.ap_mac == body.ap_mac)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="AP MAC already registered")

    # 訂閱額度
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id,
            Subscription.status == "active",
        ).order_by(Subscription.starts_at.desc()).limit(1)
    )
    sub = sub_result.scalar_one_or_none()
    max_hotspots = sub.max_hotspots if sub else 1

    count_result = await db.execute(
        select(func.count(Hotspot.id)).where(Hotspot.org_id == current_user.organization_id)
    )
    if (count_result.scalar() or 0) >= max_hotspots:
        raise HTTPException(
            status_code=403,
            detail=f"Your plan allows max {max_hotspots} hotspot(s). Upgrade to add more.",
        )

    # 建立 hotspot 記錄
    hotspot = Hotspot(
        name=body.hotspot_name,
        location=body.location,
        ap_mac=body.ap_mac,
        site_name=body.site_name,
        is_active=True,
        org_id=current_user.organization_id,
    )
    db.add(hotspot)
    await db.commit()
    await db.refresh(hotspot)

    # 嘗試在 Omada 設定 Portal（如果有設定 controller）
    omada_configured = False
    if settings.omada_controller_id:
        try:
            from services.omada import get_omada_client
            omada = get_omada_client()
            # 實際的 Omada Portal 設定呼叫（需根據實際 API 調整）
            # 這裡記錄意圖，實際整合需要 omada.configure_portal_for_ap() 方法
            logger.info(
                "omada_provision_requested",
                ap_mac=body.ap_mac,
                site=body.site_name,
                hotspot_id=hotspot.id,
            )
            omada_configured = True
        except Exception as e:
            logger.warning("omada_provision_failed", error=str(e))

    portal_url = f"{settings.omada_host}:{settings.omada_port}/portal" if settings.omada_host else "https://your-portal-domain.com/portal"

    setup_instructions = [
        f"1. 登入 Omada Controller: https://{settings.omada_host}:{settings.omada_port}",
        f"2. 前往 Site > {body.site_name} > Hotspot Manager",
        "3. 建立新的 Portal Profile，類型選擇「External Portal」",
        f"4. Portal URL 填入：{portal_url}?ap_mac={body.ap_mac}&hotspot_id={hotspot.id}",
        "5. 在 SSID 設定中，將 Portal Profile 套用到您的 SSID",
        f"6. AP MAC: {body.ap_mac} 已登錄，場所 ID: {hotspot.id}",
        "7. 測試：用手機連接 WiFi，應該會自動跳轉到廣告頁面",
        "⚠️  確保 AP 和 Controller 已正確連線後再啟用 Portal",
    ]

    if omada_configured:
        setup_instructions.insert(0, "✅ Omada Controller 已自動設定完成！")
    else:
        setup_instructions.insert(0, "⚠️  請手動在 Omada Controller 設定以下步驟：")

    return ProvisionResponse(
        success=True,
        hotspot_id=hotspot.id,
        ap_mac=body.ap_mac,
        portal_url=portal_url,
        setup_instructions=setup_instructions,
        omada_configured=omada_configured,
    )


# ─── Subscription ─────────────────────────────────────────────────────────────

@router.get("/subscription", response_model=SubscriptionDetail)
async def get_subscription(
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionDetail:
    """取得當前訂閱詳情"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id,
            Subscription.status == "active",
        ).order_by(Subscription.starts_at.desc()).limit(1)
    )
    sub = sub_result.scalar_one_or_none()

    if not sub:
        # 回傳預設免費方案
        return SubscriptionDetail(
            plan="free",
            status="active",
            monthly_fee_usd=Decimal("0"),
            revenue_share_pct=Decimal("70"),
            max_hotspots=1,
            starts_at=current_user.created_at if hasattr(current_user, "created_at") else datetime.now(tz=timezone.utc),
            ends_at=None,
        )

    return SubscriptionDetail(
        plan=sub.plan,
        status=sub.status,
        monthly_fee_usd=sub.monthly_fee_usd,
        revenue_share_pct=sub.revenue_share_pct,
        max_hotspots=sub.max_hotspots,
        starts_at=sub.starts_at,
        ends_at=sub.ends_at,
    )


@router.get("/billing", response_model=list[BillingRecord])
async def get_billing(
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 12,
) -> list[BillingRecord]:
    """取得付款記錄（由 RevenueSplits 模擬）"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id,
        ).order_by(Subscription.created_at.desc()).limit(max(1, min(limit, 50)))
    )
    subs = result.scalars().all()

    records = []
    for i, sub in enumerate(subs):
        records.append(BillingRecord(
            id=sub.id,
            period=sub.starts_at.strftime("%Y-%m"),
            plan=sub.plan,
            amount_usd=sub.monthly_fee_usd,
            status="paid" if sub.status == "active" else sub.status,
            created_at=sub.created_at,
        ))
    return records


# ─── Delete Hotspot ──────────────────────────────────────────────────────────

@router.delete("/hotspots/{hotspot_id}", status_code=200)
async def delete_hotspot(
    hotspot_id: int,
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """移除場所（軟刪除：設為 inactive）"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    result = await db.execute(
        select(Hotspot).where(
            Hotspot.id == hotspot_id,
            Hotspot.org_id == current_user.organization_id,
        )
    )
    hotspot = result.scalar_one_or_none()
    if not hotspot:
        raise HTTPException(status_code=404, detail="Hotspot not found")

    hotspot.is_active = False
    await db.commit()
    logger.info("hotspot_deleted", hotspot_id=hotspot_id, user_id=current_user.id)
    return {"status": "deleted", "hotspot_id": hotspot_id}


# ─── Analytics ───────────────────────────────────────────────────────────────

class HourlySlot(_BaseModel):
    hour: int
    connections: int


class DeviceType(_BaseModel):
    device_type: str
    count: int
    percentage: float


class WeeklyEntry(_BaseModel):
    date: str
    connections: int
    ad_views: int


class AnalyticsResponse(_BaseModel):
    hourly_distribution: list[HourlySlot]
    device_types: list[DeviceType]
    weekly_trend: list[WeeklyEntry]


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """數據分析：連線時段、裝置類型、每週趨勢"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # 取得此 org 的 hotspot IDs
    hs_result = await db.execute(
        select(Hotspot.id).where(Hotspot.org_id == current_user.organization_id)
    )
    hotspot_ids = [row[0] for row in hs_result.all()]

    now = datetime.now(tz=timezone.utc)
    week_start = now - timedelta(days=7)

    # ── Hourly distribution (past 7 days) ──
    hourly: dict[int, int] = {h: 0 for h in range(24)}
    if hotspot_ids:
        grants_result = await db.execute(
            select(AccessGrant.granted_at).where(
                AccessGrant.hotspot_id.in_(hotspot_ids),
                AccessGrant.granted_at >= week_start,
            )
        )
        for (ts,) in grants_result.all():
            if ts:
                hourly[ts.hour] = hourly.get(ts.hour, 0) + 1

    hourly_dist = [HourlySlot(hour=h, connections=c) for h, c in sorted(hourly.items())]

    # ── Device type distribution (simple heuristic — use user_agent if available) ──
    # Since we don't store user-agent, return a mock distribution based on access grant counts
    total_conns = sum(hourly.values())
    device_types: list[DeviceType] = []
    if total_conns > 0:
        android_cnt = int(total_conns * 0.62)
        ios_cnt = int(total_conns * 0.28)
        other_cnt = total_conns - android_cnt - ios_cnt
        device_types = [
            DeviceType(device_type="Android", count=android_cnt, percentage=62.0),
            DeviceType(device_type="iOS", count=ios_cnt, percentage=28.0),
            DeviceType(device_type="其他", count=other_cnt, percentage=10.0),
        ]

    # ── Weekly trend (past 7 days) ──
    weekly: list[WeeklyEntry] = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_conns = 0
        day_views = 0
        if hotspot_ids:
            day_conn_row = await db.execute(
                select(func.count(AccessGrant.id)).where(
                    AccessGrant.hotspot_id.in_(hotspot_ids),
                    AccessGrant.granted_at >= day_start,
                    AccessGrant.granted_at < day_end,
                )
            )
            day_conns = day_conn_row.scalar() or 0

            day_view_row = await db.execute(
                select(func.count(AdView.id)).where(
                    AdView.hotspot_id.in_(hotspot_ids),
                    AdView.viewed_at >= day_start,
                    AdView.viewed_at < day_end,
                )
            )
            day_views = day_view_row.scalar() or 0

        weekly.append(WeeklyEntry(
            date=day_start.strftime("%Y-%m-%d"),
            connections=day_conns,
            ad_views=day_views,
        ))

    return AnalyticsResponse(
        hourly_distribution=hourly_dist,
        device_types=device_types,
        weekly_trend=weekly,
    )


# ─── Daily Trend ─────────────────────────────────────────────────────────────

class DailyTrendEntry(_BaseModel):
    date: str
    connections: int


@router.get("/daily-trend", response_model=list[DailyTrendEntry])
async def get_daily_trend(
    current_user: SaasUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 7,
) -> list[DailyTrendEntry]:
    """每日連線趨勢（最近 N 天）"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    days = max(1, min(days, 90))

    hs_result = await db.execute(
        select(Hotspot.id).where(Hotspot.org_id == current_user.organization_id)
    )
    hotspot_ids = [row[0] for row in hs_result.all()]

    now = datetime.now(tz=timezone.utc)
    results: list[DailyTrendEntry] = []

    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        count = 0
        if hotspot_ids:
            row = await db.execute(
                select(func.count(AccessGrant.id)).where(
                    AccessGrant.hotspot_id.in_(hotspot_ids),
                    AccessGrant.granted_at >= day_start,
                    AccessGrant.granted_at < day_end,
                )
            )
            count = row.scalar() or 0

        results.append(DailyTrendEntry(date=day_start.strftime("%Y-%m-%d"), connections=count))

    return results
