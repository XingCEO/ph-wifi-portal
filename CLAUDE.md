# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AbotKamay WiFi** — Free public WiFi SaaS platform for the Philippines. Users connect to WiFi, watch a short ad, and get free internet (default 1 hour). Omada Software Controller (Docker) replaces the physical OC200 hardware. The project has two frontends: a Next.js brand website and a FastAPI-served captive portal, plus a multi-tenant SaaS layer.

## Tech Stack

- **Brand website:** Next.js 16 (App Router, static export), Tailwind CSS 4, Framer Motion, Lucide icons, i18n (EN/Filipino/繁體中文)
- **Backend:** Python 3.11+ (Docker uses 3.12-slim), FastAPI 0.115.0, Uvicorn (async)
- **Database:** PostgreSQL 16 (SQLAlchemy 2.0 async + asyncpg)
- **Cache:** Redis 7 (redis-asyncio) for sessions and anti-spam
- **Portal frontend:** Vanilla HTML/CSS/JS, Alpine.js + Chart.js for admin dashboard
- **Infrastructure:** Docker Compose (Nginx + Next.js + FastAPI + Postgres + Redis + Certbot)
- **Auth:** JWT (python-jose) for SaaS users, HTTP Basic Auth for admin, bcrypt for passwords
- **Logging:** structlog (JSON-formatted structured logging)

## Commands

```bash
# Backend (from server/) — uses Poetry for dependency management
cd server
cp .env.example .env          # configure env vars first
poetry install                 # install dependencies
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Brand website (from web/)
cd web && npm install
npm run dev                    # dev server (port 3000)
npm run build                  # static export to out/
npm run lint                   # ESLint (flat config)

# Docker (production)
cd deploy && docker-compose up -d

# Tests (MUST run from server/ directory)
cd server && pytest tests/                    # all tests (121 total)
cd server && pytest tests/test_portal.py      # single file
cd server && pytest tests/ -v --cov           # with coverage
cd server && pytest tests/ -k "test_name"     # single test by name

# Type checking (from server/)
cd server && mypy .

# Database migrations (from server/)
cd server && alembic upgrade head
```

## Architecture

**Request flow:** User phone → Omada Controller captive portal redirect → `GET /portal` (creates Redis session, records visit) → ad countdown → `POST /api/grant-access` (atomic session consume, anti-spam SET NX, calls Omada API to authorize MAC) → 1hr WiFi access.

**Two frontends, one repo:**
- `web/` — Next.js brand website (abotkamay.net). Static export (`output: "export"`), client-side locale detection redirects `/` to `/en/`, `/fil/`, or `/zh-hant/` based on `navigator.language`. Translations in `web/dictionaries/*.json`.
- `frontend/` — FastAPI-served portal pages (captive portal, thanks, admin dashboard). Vanilla HTML with brand-consistent styling.

**Key backend modules:**
- `server/main.py` — App factory (`create_app()`) with lifespan handler (init DB, Redis, Omada). Rate limiting via slowapi. CORS credentials disabled when origins contain `"*"`.
- `server/routers/portal.py` — Captive portal page, validates MAC params, loads `frontend/templates/portal.html`. Also serves `GET /` (legacy landing) and `GET /thanks`.
- `server/routers/auth.py` — `/api/grant-access` endpoint. Uses atomic `check_and_record_anti_spam` (Redis SET NX) to prevent TOCTOU race. Skips Omada call when `omada_controller_id` is empty (test mode).
- `server/routers/admin.py` — Admin dashboard + all `/admin/api/*` JSON endpoints. `verify_basic_auth()` rejects requests when `admin_password` is empty.
- `server/routers/saas_auth.py` — SaaS customer auth: registration, login, JWT token management. Uses passlib/bcrypt for password hashing.
- `server/routers/dashboard.py` — SaaS customer dashboard API (per-organization stats, hotspot management).
- `server/routers/superadmin.py` — Platform-wide super admin API (all organizations, subscriptions, platform metrics).
- `server/services/omada.py` — OmadaClient: authenticates with Omada Controller (software or OC200), authorizes/deauthorizes MACs via httpx with session/CSRF token management.
- `server/rate_limit.py` — Shared slowapi Limiter instance (default 200/min), imported by main.py and routers to avoid circular imports.
- `server/services/redis_service.py` — Session management (atomic pipeline consume), `check_and_record_anti_spam` (SET NX), active user tracking. Module-level singleton via `set_redis_instance()`/`get_redis()`.
- `server/models/database.py` — SQLAlchemy 2.0 ORM (mapped_column), `get_db()` async generator (auto-commit/rollback), `is_valid_mac()`. Includes SaaS models: `Organization`, `SaasUser`, `Subscription`.
- `server/config.py` — Pydantic Settings with bounds validation on startup. Defaults: ad 10s, session 3600s, anti-spam 10s. Production requires non-empty `admin_password` and non-default `secret_key` (RuntimeError if missing). Auto-detects Zeabur-injected env var names. API docs (`/docs`) disabled in production.

**Auth layers:**
- **Admin endpoints:** HTTP Basic Auth (`secrets.compare_digest`). Empty password is rejected with 401.
- **SaaS endpoints:** JWT bearer tokens via `Authorization` header. Issued by `saas_auth.py` on login.
- **Portal/grant endpoints:** Public but session-validated via Redis.

**Database tables:** `hotspots`, `visits`, `ad_views`, `access_grants`, `direct_advertisers`, `blocked_devices`, `admin_audit_log`, `organizations`, `saas_users`, `subscriptions`. Migrations in `server/alembic/versions/`.

## API Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /portal` | None | Captive portal page (Omada Controller redirects here) |
| `POST /api/grant-access` | Session | Grant WiFi after ad view |
| `GET /health` | None | Health check (DB + Redis status) |
| `GET /_health` | None | Emergency health (minimal, bypasses middleware) |
| `GET /metrics` | Basic | App metrics |
| `GET /admin/` | Basic | Admin dashboard |
| `GET /admin/api/stats` | Basic | Overall statistics |
| `GET /admin/api/hotspots` | Basic | Hotspot CRUD |
| `GET /admin/api/revenue` | Basic | Revenue analytics |
| `GET /admin/api/revenue/daily` | Basic | Daily revenue breakdown |
| `GET /admin/api/live` | Basic | Real-time online users |
| `GET /admin/api/visits` | Basic | Visit history (paginated) |
| `GET /admin/api/security` | Basic | Security overview |
| `PATCH /admin/api/settings` | Basic | Update runtime settings (bounded: ad 1-300s, session 60-86400s, anti-spam 1-86400s) |
| `POST /api/saas/register` | None | SaaS user registration |
| `POST /api/saas/login` | None | SaaS user login (returns JWT) |
| `GET /api/dashboard/*` | JWT | SaaS customer dashboard endpoints |
| `GET /api/superadmin/*` | Basic | Platform-wide super admin endpoints |

## Testing Notes

- Tests use **SQLite in-memory** DB via `aiosqlite` — see `server/tests/conftest.py`
- Redis is mocked with `MagicMock`/`AsyncMock` (including pipeline transactions)
- Omada API calls are fully mocked
- `conftest.py` patches `admin_password` to `"testpass123"` — admin tests use matching Basic Auth header
- Tests that need Omada calls must patch `settings.omada_controller_id` to a non-empty value (otherwise test mode skips Omada)
- Test client uses `httpx.AsyncClient` with `ASGITransport`
- pytest runs with `asyncio_mode = "auto"` (no need for `@pytest.mark.asyncio`)
- Rate limiting is disabled in tests via `limiter.enabled = False` in conftest
- `factory-boy` and `faker` available for test data generation (dev dependencies)
- Test files: `test_portal.py`, `test_auth.py`, `test_auth_extended.py`, `test_admin_api.py`, `test_omada.py`, `test_saas_auth.py`, `test_dashboard.py`, `test_superadmin.py` (121 tests total)

## Deployment

**Self-hosted VPS:** `deploy/setup.sh` (Ubuntu 22.04+), `deploy/update.sh` (rolling updates), `deploy/backup.sh` (DB backups). Docker Compose runs 8 services: Nginx, Next.js, FastAPI, PostgreSQL, Redis, Omada Controller, Certbot. Nginx routes by subdomain: `omada.*` → Omada Controller; main domain routes `/portal`, `/api/`, `/admin`, `/health`, `/thanks` to FastAPI; `/_next/` and `/` to Next.js. Omada AP communication ports (29810-29814) are exposed to host.

**Zeabur + VPS:** `zeabur.json` deploys FastAPI only (uses `requirements.txt`, not Poetry). Omada Controller must run on a separate VPS (`deploy/omada/docker-compose.yml`) since Zeabur only exposes one HTTP port. Brand website on Vercel.

**Operational scripts:** `deploy/update.sh` pulls `main`, rebuilds app image, runs zero-downtime rolling update, and executes migrations. `deploy/backup.sh` does local Postgres backups (7-day retention) with optional S3/R2 upload. Docker app runs as non-root `appuser` (UID 1000).

## Key Patterns

- All async — DB sessions, Redis calls, and HTTP (Omada) are async throughout
- Redis sessions consumed atomically via pipeline (GET + DELETE) to prevent replay
- Anti-spam uses atomic `SET NX` to prevent TOCTOU race conditions
- Next.js uses static export (`output: "export"`) with client-side locale redirect, no server runtime needed
- Config supports multiple env var names for the same service (Zeabur compatibility)
- Comments in codebase mix English and Traditional Chinese (繁體中文)
- Brand colors: deep blue `#1B4F8A` (primary), orange `#F58220` (accent), light blue `#0099DB` (WiFi/functional), warm white `#faf8f5` (background)
