from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from models.database import init_db
from routers import portal, auth, admin
import logging, time, uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing database...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down")

app = FastAPI(
    title="PH WiFi Portal",
    description="Enterprise WiFi Ad Monetization System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if __import__("os").getenv("ENVIRONMENT") != "production" else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(f"{request.method} {request.url.path} {response.status_code} {duration}ms [{request_id}]")
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred"})

app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")
app.include_router(portal.router)
app.include_router(auth.router)
app.include_router(admin.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ph-wifi-portal"}
