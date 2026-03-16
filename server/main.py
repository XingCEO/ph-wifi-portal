from __future__ import annotations

import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings, validate_settings
from models.database import init_db
from models.schemas import ErrorResponse, HealthResponse
from routers import admin, auth, portal
from services import omada as omada_module
from services.redis_service import set_redis_instance

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
_metrics: dict[str, int] = defaultdict(int)


def increment_metric(name: str) -> None:
    _metrics[name] += 1


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log = logger.bind(action="startup")
    log.info("app_starting", environment=settings.environment)
    validate_settings()
    try:
        await init_db()
        log.info("database_initialized")
    except Exception as e:
        log.error("database_init_failed", error=str(e))
        # 繼續啟動，允許服務在無 DB 時仍能回應 health check
    try:
        redis: Redis = Redis.from_url(settings.resolved_redis_url, encoding="utf-8", decode_responses=True)
        await redis.ping()
        set_redis_instance(redis)
        log.info("redis_connected")
    except Exception as e:
        log.error("redis_connect_failed", error=str(e))
    omada_module.omada_client = omada_module.OmadaClient()
    log.info("omada_client_initialized")
    log.info("app_started")
    yield
    log.info("app_shutting_down")
    await redis.aclose()
    if omada_module.omada_client:
        await omada_module.omada_client.close()
    log.info("app_shutdown_complete")


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Enterprise WiFi Ad Monetization System",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials="*" not in settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Any:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, method=request.method, path=request.url.path)
        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info("request_completed", status_code=response.status_code, duration_ms=round(duration_ms, 2))
        response.headers["X-Request-ID"] = request_id
        increment_metric("requests_total")
        return response

    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.error("unhandled_exception", error=str(exc), error_type=type(exc).__name__, request_id=request_id)
        increment_metric("errors_total")
        error = ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            detail=str(exc) if settings.environment != "production" else None,
            request_id=request_id,
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error.model_dump())

    @application.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        error = ErrorResponse(error_code="NOT_FOUND", message="The requested resource was not found", request_id=request_id)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=error.model_dump())

    application.include_router(portal.router)
    application.include_router(auth.router)
    application.include_router(admin.router)

    # Static files (frontend assets)
    static_path = Path(__file__).parent.parent / "frontend" / "static"
    if static_path.exists():
        application.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    @application.get("/health", response_model=HealthResponse)
    async def health_check(request: Request) -> HealthResponse:
        from services.redis_service import get_redis as _get_redis
        redis_status = "ok"
        try:
            r = _get_redis()
            await r.ping()
        except Exception:
            redis_status = "error"
        db_status = "ok"
        try:
            from models.database import async_engine
            import sqlalchemy
            async with async_engine.connect() as conn:
                await conn.execute(sqlalchemy.text("SELECT 1"))
        except Exception:
            db_status = "error"
        return HealthResponse(
            status="ok" if (redis_status == "ok" and db_status == "ok") else "degraded",
            version="1.0.0",
            environment=settings.environment,
            database=db_status,
            redis=redis_status,
        )

    @application.get("/metrics")
    async def metrics_endpoint(request: Request) -> dict[str, Any]:
        from routers.admin import verify_basic_auth
        verify_basic_auth(request)
        from services.redis_service import get_redis as _get_redis
        redis_key_count = 0
        try:
            r = _get_redis()
            info = await r.info("keyspace")
            redis_key_count = sum(int(v.get("keys", 0)) for v in info.values() if isinstance(v, dict))
        except Exception:
            pass
        return {"version": "1.0.0", "environment": settings.environment, "counters": dict(_metrics), "redis_keys": redis_key_count}

    # Next.js brand website (static export) — catch-all via route, not mount
    web_out_path = Path(__file__).parent.parent / "web" / "out"

    if web_out_path.exists():
        from fastapi.responses import FileResponse, HTMLResponse

        @application.get("/{full_path:path}")
        async def serve_nextjs(full_path: str):
            """Catch-all: serve Next.js static files for unmatched routes."""
            # Try exact file
            file_path = web_out_path / full_path
            if file_path.is_file():
                return FileResponse(file_path)

            # Try with index.html (directory)
            index_path = file_path / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)

            # Try .html extension
            html_path = web_out_path / f"{full_path}.html"
            if html_path.is_file():
                return FileResponse(html_path)

            # Fallback to root index.html (SPA-style)
            root_index = web_out_path / "index.html"
            if root_index.is_file():
                return FileResponse(root_index)

            return HTMLResponse(content="Not Found", status_code=404)

    return application


app = create_app()


# Emergency health check — 繞過所有中間件
@app.get("/_health")
async def emergency_health():
    return {"status": "alive"}
