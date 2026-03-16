# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Philippines WiFi ad monetization system — users connect to free WiFi, watch a 30-second Adcash ad, then get 1 hour of internet access via TP-Link OC200 hardware controller.

## Tech Stack

- **Backend:** Python 3.12, FastAPI 0.115.0, Uvicorn (async)
- **Database:** PostgreSQL 16 (SQLAlchemy 2.0 async + asyncpg)
- **Cache:** Redis 7 (redis-asyncio) for sessions and anti-spam
- **Frontend:** Vanilla HTML/JS/CSS (no framework), Chart.js for admin dashboard
- **Infrastructure:** Docker Compose (Nginx + App + Postgres + Redis + Certbot)
- **Logging:** structlog (JSON-formatted structured logging throughout)

## Commands

```bash
# Run locally (from server/)
cd server
cp .env.example .env          # configure env vars first
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run with Docker
cd deploy && docker-compose up -d

# Tests
cd server && pytest tests/                  # all tests
cd server && pytest tests/test_portal.py    # single file
cd server && pytest tests/ -v --cov         # with coverage

# Type checking
mypy server/

# Database migrations
cd server && alembic upgrade head
```

## Architecture

**Request flow:** User phone → OC200 captive portal redirect → `GET /portal` (creates Redis session, records visit) → 30s ad countdown → `POST /api/grant-access` (consumes session, calls Omada API to authorize MAC) → 1hr WiFi access.

**Key modules:**
- `server/main.py` — App factory (`create_app()`) with lifespan handler (init DB, Redis, Omada on startup). Rate limiting via slowapi.
- `server/routers/portal.py` — Captive portal page, validates MAC params from OC200 redirect, loads template from `frontend/templates/portal.html`
- `server/routers/auth.py` — `/api/grant-access` endpoint, orchestrates session→Omada→DB flow. Checks blocked devices and anti-spam before granting.
- `server/routers/admin.py` — Admin dashboard + all `/admin/api/*` JSON endpoints (~850 lines). Serves `frontend/templates/admin/dashboard.html`.
- `server/services/omada.py` — OmadaClient: authenticates with OC200 controller, authorizes/deauthorizes MACs via HTTP API. Uses httpx with session/CSRF token management.
- `server/services/redis_service.py` — `RedisService` class: session management (create/consume with atomic pipeline), anti-spam cooldowns, active user tracking per hotspot. Module-level singleton pattern via `set_redis_instance()`/`get_redis()`.
- `server/models/database.py` — SQLAlchemy 2.0 ORM with mapped_column style. Also contains `get_db()` async generator (auto-commit/rollback) and `is_valid_mac()` helper.
- `server/models/schemas.py` — Pydantic v2 request/response models
- `server/config.py` — Pydantic Settings. Auto-detects Zeabur-injected DB/Redis env var names (checks multiple keys like `DATABASE_URL`, `POSTGRES_URI`, etc.).
- `server/main_wrapper.py` — Fallback wrapper used in Zeabur deployment; loads real app but exposes health/debug endpoints if import fails.

**Frontend structure:**
- `frontend/templates/portal.html` — User-facing captive portal page
- `frontend/templates/admin/dashboard.html` — Admin dashboard HTML
- `frontend/static/css/` — `portal.css`, `admin.css`
- `frontend/static/js/` — `portal.js`, `admin.js`
- `frontend/templates/thanks.html` — Post-grant thank you page
- `frontend/templates/error.html` — Error page

**Auth:** Admin endpoints use HTTP Basic Auth (`verify_basic_auth()` in admin.py with `secrets.compare_digest`). Portal/grant endpoints are public but session-validated via Redis.

**Database tables:** `hotspots`, `visits`, `ad_views`, `access_grants`, `direct_advertisers`, `blocked_devices`, `admin_audit_log`. Migrations in `server/alembic/versions/`.

## API Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /portal` | None | Captive portal page (OC200 redirects here) |
| `POST /api/grant-access` | Session | Grant WiFi after ad view |
| `GET /health` | None | Health check (DB + Redis status) |
| `GET /_health` | None | Emergency health (bypasses middleware) |
| `GET /metrics` | Basic | App metrics |
| `GET /admin/` | Basic | Admin dashboard |
| `GET /admin/api/stats` | Basic | Overall statistics |
| `GET /admin/api/hotspots` | Basic | Hotspot list |
| `POST /admin/api/hotspots` | Basic | Create hotspot |
| `PATCH /admin/api/hotspots/{id}` | Basic | Update/toggle hotspot |
| `GET /admin/api/revenue` | Basic | Revenue analytics |
| `GET /admin/api/live` | Basic | Real-time online users |
| `GET /admin/api/visits` | Basic | Visit history (paginated) |
| `GET /admin/api/security` | Basic | Security overview |

## Testing Notes

- Tests use **SQLite in-memory** DB via `aiosqlite` (not asyncpg) — see `server/tests/conftest.py`
- Redis is mocked with `MagicMock`/`AsyncMock` (including pipeline transactions)
- Omada API calls are fully mocked
- The test app fixture overrides the lifespan to avoid connecting to real services
- Test client uses `httpx.AsyncClient` with `ASGITransport`
- Test files: `test_portal.py`, `test_omada.py`

## Deployment

Two options: **Zeabur** (config in `zeabur.json`, uses `main_wrapper.py` entrypoint) or **self-hosted VPS** (`deploy/setup.sh` for Ubuntu 22.04 one-click setup, `deploy/update.sh` for rolling updates, `deploy/backup.sh` for DB backups).

## Key Patterns

- All async — DB sessions, Redis calls, and HTTP (Omada) are async throughout
- Redis sessions are consumed atomically via pipeline (get + delete in one transaction) to prevent replay
- Config supports multiple env var names for the same service (Zeabur compatibility)
- Comments in codebase mix English and Traditional Chinese (繁體中文)
