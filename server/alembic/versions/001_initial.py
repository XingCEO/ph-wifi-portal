"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── hotspots ─────────────────────────────────────────────────────────
    op.create_table(
        "hotspots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=False),
        sa.Column("ap_mac", sa.String(length=17), nullable=False),
        sa.Column("site_name", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("ap_mac"),
    )

    # ─── visits ───────────────────────────────────────────────────────────
    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_mac", sa.String(length=17), nullable=False),
        sa.Column("hotspot_id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "visited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visits_client_mac", "visits", ["client_mac"])
    op.create_index("ix_visits_hotspot_id", "visits", ["hotspot_id"])
    op.create_index("ix_visits_visited_at", "visits", ["visited_at"])

    # ─── direct_advertisers ───────────────────────────────────────────────
    op.create_table(
        "direct_advertisers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact", sa.String(length=255), nullable=True),
        sa.Column("banner_url", sa.Text(), nullable=False),
        sa.Column("click_url", sa.Text(), nullable=False),
        sa.Column(
            "monthly_fee_php", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column("hotspot_ids", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "starts_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ─── ad_views ─────────────────────────────────────────────────────────
    op.create_table(
        "ad_views",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_mac", sa.String(length=17), nullable=False),
        sa.Column("hotspot_id", sa.Integer(), nullable=False),
        sa.Column("ad_network", sa.String(length=50), nullable=False),
        sa.Column("advertiser_id", sa.Integer(), nullable=True),
        sa.Column(
            "estimated_revenue_usd",
            sa.Numeric(precision=10, scale=4),
            nullable=False,
            server_default="0.0000",
        ),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["advertiser_id"], ["direct_advertisers.id"]),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_views_client_mac", "ad_views", ["client_mac"])
    op.create_index("ix_ad_views_hotspot_id", "ad_views", ["hotspot_id"])
    op.create_index("ix_ad_views_viewed_at", "ad_views", ["viewed_at"])

    # ─── access_grants ────────────────────────────────────────────────────
    op.create_table(
        "access_grants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_mac", sa.String(length=17), nullable=False),
        sa.Column("hotspot_id", sa.Integer(), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_grants_client_mac", "access_grants", ["client_mac"])
    op.create_index("ix_access_grants_expires_at", "access_grants", ["expires_at"])


def downgrade() -> None:
    op.drop_table("access_grants")
    op.drop_table("ad_views")
    op.drop_table("direct_advertisers")
    op.drop_table("visits")
    op.drop_table("hotspots")
