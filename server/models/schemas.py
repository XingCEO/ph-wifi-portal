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
