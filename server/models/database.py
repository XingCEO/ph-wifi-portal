from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncGenerator

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import settings


class Base(DeclarativeBase):
    pass


# ─── SaaS Multi-Tenant Tables ───────────────────────────────────────────────

class Organization(Base):
    """SaaS 客戶的組織/公司"""
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    users: Mapped[list["SaasUser"]] = relationship("SaasUser", back_populates="organization")
    hotspots: Mapped[list["Hotspot"]] = relationship("Hotspot", back_populates="organization")
    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="organization")
    revenue_splits: Mapped[list["RevenueSplit"]] = relationship("RevenueSplit", back_populates="organization")

    __table_args__ = (
        Index("ix_organizations_slug", "slug"),
    )


class SaasUser(Base):
    """SaaS 平台客戶帳號"""
    __tablename__ = "saas_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="owner", nullable=False)  # owner, member, admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="users")

    __table_args__ = (
        Index("ix_saas_users_email", "email"),
        Index("ix_saas_users_org_id", "organization_id"),
    )


class Subscription(Base):
    """組織的訂閱方案"""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False)  # free, starter, pro, enterprise
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, cancelled, expired
    monthly_fee_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    revenue_share_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("70.00"))  # % 給客戶
    max_hotspots: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_subscriptions_org_id", "organization_id"),
    )


class RevenueSplit(Base):
    """廣告收入拆帳記錄"""
    __tablename__ = "revenue_splits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False)
    hotspot_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("hotspots.id"), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_revenue_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    platform_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("30.00"))
    partner_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("70.00"))
    platform_amount_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    partner_amount_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    ad_views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, paid
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="revenue_splits")

    __table_args__ = (
        Index("ix_revenue_splits_org_id", "organization_id"),
        Index("ix_revenue_splits_period", "period_start", "period_end"),
    )


# ─── Original Tables ─────────────────────────────────────────────────────────

class Hotspot(Base):
    __tablename__ = "hotspots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)
    ap_mac: Mapped[str] = mapped_column(String(17), unique=True, nullable=False)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    org_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="hotspot")
    ad_views: Mapped[list["AdView"]] = relationship("AdView", back_populates="hotspot")
    access_grants: Mapped[list["AccessGrant"]] = relationship("AccessGrant", back_populates="hotspot")
    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="hotspots")

    __table_args__ = (
        Index("ix_hotspots_org_id", "org_id"),
    )


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_mac: Mapped[str] = mapped_column(String(17), nullable=False)
    hotspot_id: Mapped[int] = mapped_column(Integer, ForeignKey("hotspots.id"), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    visited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    hotspot: Mapped["Hotspot"] = relationship("Hotspot", back_populates="visits")

    __table_args__ = (
        Index("ix_visits_client_mac", "client_mac"),
        Index("ix_visits_hotspot_id", "hotspot_id"),
        Index("ix_visits_visited_at", "visited_at"),
    )


class DirectAdvertiser(Base):
    __tablename__ = "direct_advertisers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banner_url: Mapped[str] = mapped_column(Text, nullable=False)
    click_url: Mapped[str] = mapped_column(Text, nullable=False)
    monthly_fee_php: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    hotspot_ids: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ad_views: Mapped[list["AdView"]] = relationship("AdView", back_populates="advertiser")


class AdView(Base):
    __tablename__ = "ad_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_mac: Mapped[str] = mapped_column(String(17), nullable=False)
    hotspot_id: Mapped[int] = mapped_column(Integer, ForeignKey("hotspots.id"), nullable=False)
    ad_network: Mapped[str] = mapped_column(String(50), nullable=False)
    advertiser_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("direct_advertisers.id"), nullable=True)
    estimated_revenue_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    hotspot: Mapped["Hotspot"] = relationship("Hotspot", back_populates="ad_views")
    advertiser: Mapped["DirectAdvertiser | None"] = relationship("DirectAdvertiser", back_populates="ad_views")

    __table_args__ = (
        Index("ix_ad_views_client_mac", "client_mac"),
        Index("ix_ad_views_hotspot_id", "hotspot_id"),
        Index("ix_ad_views_viewed_at", "viewed_at"),
    )


class AccessGrant(Base):
    __tablename__ = "access_grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_mac: Mapped[str] = mapped_column(String(17), nullable=False)
    hotspot_id: Mapped[int] = mapped_column(Integer, ForeignKey("hotspots.id"), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    hotspot: Mapped["Hotspot"] = relationship("Hotspot", back_populates="access_grants")

    __table_args__ = (
        Index("ix_access_grants_client_mac", "client_mac"),
        Index("ix_access_grants_expires_at", "expires_at"),
    )


class BlockedDevice(Base):
    __tablename__ = "blocked_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_mac: Mapped[str] = mapped_column(String(17), unique=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    blocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_blocked_devices_client_mac", "client_mac"),
        Index("ix_blocked_devices_expires_at", "expires_at"),
    )


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_user: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[Any] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_audit_log_admin_user", "admin_user"),
        Index("ix_audit_log_action", "action"),
        Index("ix_audit_log_created_at", "created_at"),
    )


def _make_engine() -> Any:
    return create_async_engine(
        settings.async_database_url,
        echo=settings.environment == "development",
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )


async_engine = _make_engine()

async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")


def is_valid_mac(mac: str) -> bool:
    return bool(MAC_RE.match(mac))
