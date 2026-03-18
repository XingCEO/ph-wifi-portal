from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import AccessGrant, AdminAuditLog, AdView, Visit

logger = structlog.get_logger(__name__)


async def run_data_retention_cleanup(db: AsyncSession) -> dict[str, int]:
    """Delete records older than configured retention periods (AKD-POL-004 Sec.4).

    Returns a dict of {table_name: deleted_count}.
    """
    now = datetime.now(timezone.utc)
    deleted_counts: dict[str, int] = {}

    retention_rules: list[tuple[str, type, str, int]] = [
        ("visits", Visit, "visited_at", settings.retention_connection_logs_days),
        ("ad_views", AdView, "viewed_at", settings.retention_ad_data_days),
        ("access_grants", AccessGrant, "granted_at", settings.retention_connection_logs_days),
        ("admin_audit_log", AdminAuditLog, "created_at", settings.retention_security_records_days),
    ]

    for table_name, model, ts_column, retention_days in retention_rules:
        cutoff = now - timedelta(days=retention_days)
        column = getattr(model, ts_column)

        # Count rows to be deleted
        count_result = await db.execute(
            select(func.count()).select_from(model).where(column < cutoff)
        )
        count = count_result.scalar() or 0

        if count > 0:
            await db.execute(
                delete(model).where(column < cutoff)
            )
            logger.info(
                "data_retention_cleanup",
                table=table_name,
                cutoff=cutoff.isoformat(),
                retention_days=retention_days,
                deleted_count=count,
            )
        else:
            logger.debug(
                "data_retention_no_expired_records",
                table=table_name,
                cutoff=cutoff.isoformat(),
                retention_days=retention_days,
            )

        deleted_counts[table_name] = count

    await db.commit()

    total = sum(deleted_counts.values())
    logger.info("data_retention_cleanup_complete", total_deleted=total, details=deleted_counts)
    return deleted_counts
