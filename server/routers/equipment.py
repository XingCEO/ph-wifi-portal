from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Equipment, get_db
from routers.admin import record_audit, verify_basic_auth

router = APIRouter(prefix="/admin")
logger = structlog.get_logger(__name__)


# ── Pydantic Schemas ─────────────────────────────────────────────────────


class EquipmentCreate(BaseModel):
    item_type: str
    model: str | None = None
    serial_number: str | None = None
    hotspot_id: int | None = None
    organization_id: int | None = None
    condition: str = "good"
    original_cost_php: Decimal = Decimal("0.00")
    installed_at: datetime | None = None


class EquipmentUpdate(BaseModel):
    condition: str | None = None
    hotspot_id: int | None = Field(default=None)
    organization_id: int | None = Field(default=None)
    installed_at: datetime | None = None


class EquipmentResponse(BaseModel):
    id: int
    item_type: str
    model: str | None
    serial_number: str | None
    hotspot_id: int | None
    organization_id: int | None
    condition: str
    original_cost_php: Decimal
    installed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("/api/equipment", response_model=EquipmentResponse, status_code=201)
async def create_equipment(
    request: Request, body: EquipmentCreate, db: AsyncSession = Depends(get_db),
) -> EquipmentResponse:
    verify_basic_auth(request)
    # Check serial_number uniqueness if provided
    if body.serial_number:
        existing = await db.execute(
            select(Equipment).where(Equipment.serial_number == body.serial_number)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Equipment with this serial number already exists",
            )
    now = datetime.now(tz=timezone.utc)
    equip = Equipment(
        item_type=body.item_type,
        model=body.model,
        serial_number=body.serial_number,
        hotspot_id=body.hotspot_id,
        organization_id=body.organization_id,
        condition=body.condition,
        original_cost_php=body.original_cost_php,
        installed_at=body.installed_at,
        created_at=now,
    )
    db.add(equip)
    await db.flush()
    await db.refresh(equip)
    await record_audit(db, request, "create_equipment", "equipment", str(equip.id), {
        "item_type": equip.item_type, "serial_number": equip.serial_number,
    })
    await db.commit()
    logger.info("equipment_created", equipment_id=equip.id)
    return EquipmentResponse.model_validate(equip)


@router.get("/api/equipment", response_model=list[EquipmentResponse])
async def list_equipment(
    request: Request,
    hotspot_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[EquipmentResponse]:
    verify_basic_auth(request)
    q = select(Equipment).order_by(Equipment.id.desc())
    if hotspot_id is not None:
        q = q.where(Equipment.hotspot_id == hotspot_id)
    result = await db.execute(q)
    return [EquipmentResponse.model_validate(e) for e in result.scalars().all()]


@router.get("/api/equipment/{equip_id}")
async def get_equipment(
    request: Request, equip_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    result = await db.execute(select(Equipment).where(Equipment.id == equip_id))
    equip = result.scalar_one_or_none()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # VPA-005 Art.4.5 — straight-line depreciation over 36 months
    now = datetime.now(tz=timezone.utc)
    installed = equip.installed_at or equip.created_at
    # Handle timezone-naive datetimes from SQLite (tests)
    if installed.tzinfo is None:
        installed = installed.replace(tzinfo=timezone.utc)
    months_elapsed = (now.year - installed.year) * 12 + (now.month - installed.month)
    if months_elapsed < 0:
        months_elapsed = 0
    depreciation_factor = max(Decimal("0"), Decimal("1") - Decimal(str(months_elapsed)) / Decimal("36"))
    current_value_php = (equip.original_cost_php * depreciation_factor).quantize(Decimal("0.01"))

    data = EquipmentResponse.model_validate(equip).model_dump(mode="json")
    data["months_elapsed"] = months_elapsed
    data["depreciation_factor"] = str(depreciation_factor.quantize(Decimal("0.0001")))
    data["current_value_php"] = str(current_value_php)
    return data


@router.patch("/api/equipment/{equip_id}", response_model=EquipmentResponse)
async def update_equipment(
    request: Request, equip_id: int, body: EquipmentUpdate, db: AsyncSession = Depends(get_db),
) -> EquipmentResponse:
    verify_basic_auth(request)
    result = await db.execute(select(Equipment).where(Equipment.id == equip_id))
    equip = result.scalar_one_or_none()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found")
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(equip, field, value)
    await db.flush()
    await db.refresh(equip)
    await record_audit(db, request, "update_equipment", "equipment", str(equip_id), update_data)
    await db.commit()
    logger.info("equipment_updated", equipment_id=equip_id, fields=list(update_data.keys()))
    return EquipmentResponse.model_validate(equip)


@router.delete("/api/equipment/{equip_id}")
async def delete_equipment(
    request: Request, equip_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    verify_basic_auth(request)
    result = await db.execute(select(Equipment).where(Equipment.id == equip_id))
    equip = result.scalar_one_or_none()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found")
    equip.condition = "removed"
    await record_audit(db, request, "delete_equipment", "equipment", str(equip_id), {
        "item_type": equip.item_type, "serial_number": equip.serial_number,
    })
    await db.commit()
    logger.info("equipment_removed", equipment_id=equip_id)
    return {"status": "removed"}
