from pydantic import BaseModel, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional
import re

class GrantAccessRequest(BaseModel):
    session_id: str

class GrantAccessResponse(BaseModel):
    status: str
    redirect_url: str
    expires_at: datetime
    message: str

class HotspotCreate(BaseModel):
    name: str
    location: str
    ap_mac: str
    site_name: str

    @field_validator("ap_mac")
    @classmethod
    def validate_mac(cls, v: str) -> str:
        pattern = r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid MAC address format")
        return v.lower()

class HotspotResponse(BaseModel):
    id: int
    name: str
    location: str
    ap_mac: str
    site_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class DailyStats(BaseModel):
    date: str
    total_visits: int
    total_ad_views: int
    total_access_grants: int
    estimated_revenue_usd: float
    active_hotspots: int

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: Optional[str] = None
