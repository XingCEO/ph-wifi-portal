from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer, DateTime, Numeric, JSON, ForeignKey, func
from datetime import datetime
from decimal import Decimal
from typing import Optional
import os

class Base(DeclarativeBase):
    pass

class Hotspot(Base):
    __tablename__ = "hotspots"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    location: Mapped[str] = mapped_column(String(200))
    ap_mac: Mapped[str] = mapped_column(String(17), unique=True)
    site_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Visit(Base):
    __tablename__ = "visits"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_mac: Mapped[str] = mapped_column(String(17), index=True)
    hotspot_id: Mapped[int] = mapped_column(ForeignKey("hotspots.id"))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    visited_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

class AdView(Base):
    __tablename__ = "ad_views"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_mac: Mapped[str] = mapped_column(String(17), index=True)
    hotspot_id: Mapped[int] = mapped_column(ForeignKey("hotspots.id"))
    ad_network: Mapped[str] = mapped_column(String(50), default="adcash")
    estimated_revenue_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0035"))
    viewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

class AccessGrant(Base):
    __tablename__ = "access_grants"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_mac: Mapped[str] = mapped_column(String(17), index=True)
    hotspot_id: Mapped[int] = mapped_column(ForeignKey("hotspots.id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)

# Engine 和 Session
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/wifi_portal")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
