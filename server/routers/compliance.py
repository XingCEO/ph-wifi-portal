from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import AccessGrant, AdminAuditLog, AdView, Visit, get_db
from routers.admin import verify_basic_auth
from services.data_retention import run_data_retention_cleanup

router = APIRouter(prefix="/admin/api/compliance")
logger = structlog.get_logger(__name__)


@router.get("/retention")
async def get_retention_policy(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return current retention policy settings and row counts per table."""
    verify_basic_auth(request)

    tables = [
        ("visits", Visit, settings.retention_connection_logs_days),
        ("ad_views", AdView, settings.retention_ad_data_days),
        ("access_grants", AccessGrant, settings.retention_connection_logs_days),
        ("admin_audit_log", AdminAuditLog, settings.retention_security_records_days),
    ]

    table_info = []
    for table_name, model, retention_days in tables:
        count_result = await db.execute(
            select(func.count()).select_from(model)
        )
        row_count = count_result.scalar() or 0
        table_info.append({
            "table": table_name,
            "retention_days": retention_days,
            "row_count": row_count,
        })

    return {
        "policy": "AKD-POL-004",
        "tables": table_info,
    }


@router.post("/retention/cleanup")
async def trigger_cleanup(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger manual data retention cleanup. Returns deleted counts per table."""
    verify_basic_auth(request)

    logger.info("manual_retention_cleanup_triggered", ip=request.client.host if request.client else "unknown")
    deleted_counts = await run_data_retention_cleanup(db)

    return {
        "status": "completed",
        "deleted": deleted_counts,
        "total_deleted": sum(deleted_counts.values()),
    }


@router.get("/dpo")
async def get_dpo_contact(request: Request) -> dict[str, Any]:
    """Return Data Protection Officer contact info (AKD-POL-004)."""
    verify_basic_auth(request)

    return {
        "dpo_email": settings.dpo_email,
        "policy_reference": "AKD-POL-004",
    }
