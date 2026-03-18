from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Invoice, get_db
from routers.admin import record_audit, verify_basic_auth

router = APIRouter(prefix="/admin")
logger = structlog.get_logger(__name__)

VALID_INVOICE_TYPES = {"monthly_fee", "listing_fee", "promotion_budget", "revenue_share"}
VALID_STATUSES = {"pending", "paid", "overdue", "cancelled"}


# ── Pydantic Schemas ─────────────────────────────────────────────────────


class InvoiceCreate(BaseModel):
    organization_id: int | None = None
    advertiser_id: int | None = None
    invoice_type: str
    amount_php: Decimal
    due_date: datetime | None = None
    notes: str | None = None


class InvoiceStatusUpdate(BaseModel):
    status: str
    notes: str | None = None


class InvoiceResponse(BaseModel):
    id: int
    organization_id: int | None
    advertiser_id: int | None
    invoice_type: str
    amount_php: Decimal
    status: str
    due_date: datetime | None
    paid_at: datetime | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("/api/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    request: Request, body: InvoiceCreate, db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    verify_basic_auth(request)
    if body.invoice_type not in VALID_INVOICE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid invoice_type. Must be one of: {', '.join(sorted(VALID_INVOICE_TYPES))}",
        )
    now = datetime.now(tz=timezone.utc)
    invoice = Invoice(
        organization_id=body.organization_id,
        advertiser_id=body.advertiser_id,
        invoice_type=body.invoice_type,
        amount_php=body.amount_php,
        status="pending",
        due_date=body.due_date,
        notes=body.notes,
        created_at=now,
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)
    await record_audit(db, request, "create_invoice", "invoice", str(invoice.id), {
        "type": invoice.invoice_type, "amount_php": str(invoice.amount_php),
    })
    await db.commit()
    logger.info("invoice_created", invoice_id=invoice.id)
    return InvoiceResponse.model_validate(invoice)


@router.get("/api/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    request: Request,
    organization_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    type_filter: str | None = Query(default=None, alias="type"),
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceResponse]:
    verify_basic_auth(request)
    q = select(Invoice).order_by(Invoice.id.desc())
    if organization_id is not None:
        q = q.where(Invoice.organization_id == organization_id)
    if status_filter is not None:
        q = q.where(Invoice.status == status_filter)
    if type_filter is not None:
        q = q.where(Invoice.invoice_type == type_filter)
    result = await db.execute(q)
    return [InvoiceResponse.model_validate(inv) for inv in result.scalars().all()]


@router.patch("/api/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice_status(
    request: Request, invoice_id: int, body: InvoiceStatusUpdate, db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    verify_basic_auth(request)
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    old_status = invoice.status
    invoice.status = body.status
    if body.notes is not None:
        invoice.notes = body.notes
    # Auto-set paid_at when marking as paid
    if body.status == "paid" and invoice.paid_at is None:
        invoice.paid_at = datetime.now(tz=timezone.utc)
    await db.flush()
    await db.refresh(invoice)
    await record_audit(db, request, "update_invoice", "invoice", str(invoice_id), {
        "old_status": old_status, "new_status": body.status,
    })
    await db.commit()
    logger.info("invoice_updated", invoice_id=invoice_id, old_status=old_status, new_status=body.status)
    return InvoiceResponse.model_validate(invoice)


@router.get("/api/invoices/summary")
async def invoices_summary(
    request: Request,
    month: str = Query(default="", description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    now = datetime.now(tz=timezone.utc)
    period = month if month else now.strftime("%Y-%m")
    try:
        year_s, month_s = period.split("-")
        period_start = datetime(int(year_s), int(month_s), 1, tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    if period_start.month == 12:
        period_end = datetime(period_start.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        period_end = datetime(period_start.year, period_start.month + 1, 1, tzinfo=timezone.utc)

    base_filter = [Invoice.created_at >= period_start, Invoice.created_at < period_end]

    total_billed_r = await db.execute(
        select(func.sum(Invoice.amount_php)).where(*base_filter)
    )
    total_paid_r = await db.execute(
        select(func.sum(Invoice.amount_php)).where(*base_filter, Invoice.status == "paid")
    )
    total_outstanding_r = await db.execute(
        select(func.sum(Invoice.amount_php)).where(*base_filter, Invoice.status.in_(["pending", "overdue"]))
    )
    count_r = await db.execute(
        select(func.count(Invoice.id)).where(*base_filter)
    )
    # Breakdown by type
    by_type_r = await db.execute(
        select(
            Invoice.invoice_type,
            func.count(Invoice.id).label("count"),
            func.sum(Invoice.amount_php).label("total"),
        )
        .where(*base_filter)
        .group_by(Invoice.invoice_type)
    )

    return {
        "period": period,
        "total_invoices": count_r.scalar_one() or 0,
        "total_billed_php": str(total_billed_r.scalar_one() or Decimal("0.00")),
        "total_paid_php": str(total_paid_r.scalar_one() or Decimal("0.00")),
        "total_outstanding_php": str(total_outstanding_r.scalar_one() or Decimal("0.00")),
        "by_type": [
            {"type": row.invoice_type, "count": row.count, "total_php": str(row.total or Decimal("0.00"))}
            for row in by_type_r.all()
        ],
    }
