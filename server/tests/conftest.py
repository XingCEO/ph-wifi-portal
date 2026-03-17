from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Ensure server/ is on sys.path when running from tests/
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


# ─── Test database (SQLite in-memory) ───────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine() -> AsyncGenerator[Any, None]:
    from models.database import Base

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


# ─── Mock Redis ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis() -> MagicMock:
    redis = MagicMock()
    redis.ping = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.set = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=1)
    redis.decr = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    redis.aclose = AsyncMock()
    redis.info = AsyncMock(return_value={})

    # Pipeline mock
    pipeline_mock = MagicMock()
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)
    pipeline_mock.get = AsyncMock()
    pipeline_mock.delete = AsyncMock()
    pipeline_mock.execute = AsyncMock(return_value=[None, 0])
    redis.pipeline = MagicMock(return_value=pipeline_mock)

    return redis


# ─── Mock Omada ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_omada() -> MagicMock:
    omada = MagicMock()
    omada.grant_access = AsyncMock(return_value={"status": "success"})
    omada.revoke_access = AsyncMock(return_value=None)
    omada.get_online_clients = AsyncMock(return_value=[])
    omada.close = AsyncMock()
    return omada


# ─── FastAPI test app ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def app(
    test_engine: Any,
    mock_redis: MagicMock,
    mock_omada: MagicMock,
) -> AsyncGenerator[Any, None]:
    """Create FastAPI app with test DB and mocked dependencies."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    test_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    # Patch all external dependencies
    with (
        patch("models.database.async_engine", test_engine),
        patch("models.database.async_session_factory", test_factory),
        patch("services.redis_service._redis_instance", mock_redis),
        patch("services.omada.omada_client", mock_omada),
        patch("models.database.init_db", new_callable=lambda: lambda: AsyncMock()),
        patch("config.settings.admin_password", "testpass123"),
    ):
        from main import create_app

        test_app = create_app()

        # Disable rate limiting in tests
        from rate_limit import limiter as _limiter
        _limiter.enabled = False

        # Override lifespan so it doesn't try to connect to real services
        async def override_lifespan(app: Any) -> AsyncGenerator[None, None]:
            import services.redis_service as redis_svc_module
            import services.omada as omada_module_ref

            redis_svc_module._redis_instance = mock_redis
            omada_module_ref.omada_client = mock_omada
            yield

        test_app.router.lifespan_context = override_lifespan

        yield test_app


@pytest_asyncio.fixture
async def client(app: Any) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ─── Hotspot factory helper ──────────────────────────────────────────────────

@pytest_asyncio.fixture
async def sample_hotspot(test_session: AsyncSession) -> Any:
    """Insert a sample hotspot into the test DB."""
    from datetime import datetime, timezone

    from models.database import Hotspot

    now = datetime.now(tz=timezone.utc)
    hotspot = Hotspot(
        name="Test Hotspot",
        location="Test Location",
        ap_mac="AA:BB:CC:DD:EE:FF",
        site_name="test-site",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    test_session.add(hotspot)
    await test_session.commit()
    await test_session.refresh(hotspot)
    return hotspot
