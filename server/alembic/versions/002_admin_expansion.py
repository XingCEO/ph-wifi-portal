"""Admin expansion: blocked_devices + admin_audit_log

Revision ID: 002
Revises: 001
Create Date: 2026-03-15 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── blocked_devices ──────────────────────────────────────────────────
    op.create_table(
        "blocked_devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_mac", sa.String(length=17), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("blocked_by", sa.String(length=255), nullable=True),
        sa.Column(
            "blocked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_mac"),
    )
    op.create_index("ix_blocked_devices_client_mac", "blocked_devices", ["client_mac"])
    op.create_index("ix_blocked_devices_expires_at", "blocked_devices", ["expires_at"])

    # ─── admin_audit_log ──────────────────────────────────────────────────
    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_user", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_admin_user", "admin_audit_log", ["admin_user"])
    op.create_index("ix_audit_log_action", "admin_audit_log", ["action"])
    op.create_index("ix_audit_log_created_at", "admin_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("admin_audit_log")
    op.drop_table("blocked_devices")
