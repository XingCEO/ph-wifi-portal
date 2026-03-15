from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncGenerator

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="hotspot")
    ad_views: Mapped[list["AdView"]] = relationship("AdView", back_populates="hotspot")
    access_grants: Mapped[list["AccessGrant"]] = relationship("AccessGrant", back_populates="hotspot")


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


def _make_engine() -> Any:
    return create_async_engine(
        settings.database_url,
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
