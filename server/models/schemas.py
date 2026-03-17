from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HotspotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=500)
    ap_mac: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")
    site_name: str = Field(..., min_length=1, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool = True


class HotspotUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    ap_mac: str | None = Field(default=None, pattern=r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")
    site_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool | None = None


class HotspotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    location: str
    ap_mac: str
    site_name: str
    latitude: float | None
    longitude: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class VisitCreate(BaseModel):
    client_mac: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")
    hotspot_id: int
    ip_address: str | None = None
    user_agent: str | None = None


class VisitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_mac: str
    hotspot_id: int
    ip_address: str | None
    user_agent: str | None
    visited_at: datetime


class AdViewCreate(BaseModel):
    client_mac: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")
    hotspot_id: int
    ad_network: str = Field(..., pattern=r"^(adcash|direct)$")
    advertiser_id: int | None = None
    estimated_revenue_usd: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))


class AdViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_mac: str
    hotspot_id: int
    ad_network: str
    advertiser_id: int | None
    estimated_revenue_usd: Decimal
    viewed_at: datetime


class DirectAdvertiserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    contact: str | None = None
    banner_url: str = Field(..., min_length=1)
    click_url: str = Field(..., min_length=1)
    monthly_fee_php: Decimal = Field(..., ge=Decimal("0"))
    hotspot_ids: list[int] = Field(default_factory=list)
    is_active: bool = True
    starts_at: datetime
    ends_at: datetime | None = None


class DirectAdvertiserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    contact: str | None
    banner_url: str
    click_url: str
    monthly_fee_php: Decimal
    hotspot_ids: Any
    is_active: bool
    starts_at: datetime
    ends_at: datetime | None


class GrantAccessRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)


class GrantAccessResponse(BaseModel):
    status: str
    redirect_url: str
    expires_at: datetime


class HotspotStats(BaseModel):
    hotspot_id: int
    hotspot_name: str
    visits_today: int
    ad_views_today: int
    revenue_today_usd: Decimal
    active_users: int


class StatsResponse(BaseModel):
    date: str
    total_visits: int
    total_ad_views: int
    total_revenue_usd: Decimal
    total_access_grants: int
    active_users_total: int
    hotspots: list[HotspotStats]


class RevenueResponse(BaseModel):
    period: str
    adcash_revenue_usd: Decimal
    direct_revenue_php: Decimal
    total_ad_views: int
    breakdown_by_hotspot: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: str | None = None
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    redis: str


class BlockedDeviceCreate(BaseModel):
    client_mac: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")
    reason: str | None = None
    expires_at: datetime | None = None


class BlockedDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_mac: str
    reason: str | None
    blocked_by: str | None
    blocked_at: datetime
    expires_at: datetime | None
    is_active: bool


class DirectAdvertiserUpdate(BaseModel):
    name: str | None = None
    contact: str | None = None
    banner_url: str | None = None
    click_url: str | None = None
    monthly_fee_php: Decimal | None = None
    hotspot_ids: list[int] | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    admin_user: str
    action: str
    target_type: str | None
    target_id: str | None
    details: Any | None
    ip_address: str | None
    created_at: datetime


class SystemSettingsResponse(BaseModel):
    ad_duration_seconds: int
    session_duration_seconds: int
    anti_spam_window_seconds: int
    omada_host: str
    environment: str
    app_name: str


class SystemSettingsUpdate(BaseModel):
    ad_duration_seconds: int | None = None
    session_duration_seconds: int | None = None
    anti_spam_window_seconds: int | None = None


# ─── SaaS Schemas ────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    contact_email: str = Field(..., min_length=1, max_length=255)
    contact_phone: str | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    contact_email: str
    contact_phone: str | None
    is_active: bool
    created_at: datetime


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    org_name: str = Field(..., min_length=1, max_length=255)
    org_slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v.lower().strip()


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours
    user_id: int
    email: str
    full_name: str
    org_id: int | None
    org_name: str | None


class SaasUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    organization_id: int | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime


class DashboardStatsResponse(BaseModel):
    total_connections: int
    total_ad_views: int
    total_revenue_usd: Decimal
    partner_revenue_usd: Decimal
    active_hotspots: int
    period_days: int


class DashboardHotspotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=500)
    ap_mac: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")
    site_name: str = Field(..., min_length=1, max_length=255)
    latitude: float | None = None
    longitude: float | None = None


class DashboardHotspotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    location: str
    ap_mac: str
    site_name: str
    is_active: bool
    org_id: int | None
    created_at: datetime
    connections_count: int = 0
    revenue_usd: Decimal = Decimal("0.0000")


class RevenueSplitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hotspot_id: int | None
    period_start: datetime
    period_end: datetime
    total_revenue_usd: Decimal
    partner_pct: Decimal
    partner_amount_usd: Decimal
    ad_views_count: int
    status: str
    created_at: datetime


class ProvisionRequest(BaseModel):
    ap_mac: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")
    hotspot_name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=500)
    site_name: str = Field(default="Default", min_length=1, max_length=255)


class ProvisionResponse(BaseModel):
    success: bool
    hotspot_id: int
    ap_mac: str
    portal_url: str
    setup_instructions: list[str]
    omada_configured: bool


class PortalSessionData(BaseModel):
    client_mac: str
    ap_mac: str
    ssid_name: str
    site: str
    radio_id: int
    redirect_url: str
    hotspot_id: int
    created_at: str

    @field_validator("client_mac", "ap_mac")
    @classmethod
    def validate_mac(cls, v: str) -> str:
        if not re.match(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$", v):
            raise ValueError(f"Invalid MAC address: {v}")
        return v
