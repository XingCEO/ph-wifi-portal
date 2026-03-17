"""SaaS Multi-Tenant Schema: organizations, saas_users, subscriptions, revenue_splits, hotspots.org_id

Revision ID: 003
Revises: 002
Create Date: 2026-03-17 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # saas_users
    op.create_table(
        "saas_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="owner"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_saas_users_email", "saas_users", ["email"])
    op.create_index("ix_saas_users_org_id", "saas_users", ["organization_id"])

    # subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("monthly_fee_usd", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("revenue_share_pct", sa.Numeric(5, 2), nullable=False, server_default="70.00"),
        sa.Column("max_hotspots", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_org_id", "subscriptions", ["organization_id"])

    # revenue_splits
    op.create_table(
        "revenue_splits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("hotspot_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_revenue_usd", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
        sa.Column("platform_pct", sa.Numeric(5, 2), nullable=False, server_default="30.00"),
        sa.Column("partner_pct", sa.Numeric(5, 2), nullable=False, server_default="70.00"),
        sa.Column("platform_amount_usd", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
        sa.Column("partner_amount_usd", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
        sa.Column("ad_views_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_revenue_splits_org_id", "revenue_splits", ["organization_id"])
    op.create_index("ix_revenue_splits_period", "revenue_splits", ["period_start", "period_end"])

    # Add org_id column to hotspots
    op.add_column("hotspots", sa.Column("org_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_hotspots_org_id", "hotspots", "organizations", ["org_id"], ["id"])
    op.create_index("ix_hotspots_org_id", "hotspots", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_hotspots_org_id", "hotspots")
    op.drop_constraint("fk_hotspots_org_id", "hotspots", type_="foreignkey")
    op.drop_column("hotspots", "org_id")
    op.drop_table("revenue_splits")
    op.drop_table("subscriptions")
    op.drop_table("saas_users")
    op.drop_table("organizations")
