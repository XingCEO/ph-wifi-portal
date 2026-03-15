# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Philippines WiFi ad monetization system — users connect to free WiFi, watch a 30-second Adcash ad, then get 1 hour of internet access via TP-Link OC200 hardware controller.

## Tech Stack

- **Backend:** Python 3.12, FastAPI 0.110.0, Uvicorn (async)
- **Database:** PostgreSQL 16 (SQLAlchemy 2.0 async + asyncpg)
- **Cache:** Redis 7 (redis-asyncio) for sessions and anti-spam
- **Frontend:** Vanilla HTML/JS/CSS (no framework), Chart.js for admin dashboard
- **Infrastructure:** Docker Compose (Nginx + App + Postgres + Redis + Certbot)

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
cd server && pytest tests/test_auth.py      # single file
cd server && pytest tests/ -v --cov         # with coverage

# Type checking
mypy server/

# Database migrations
cd server && alembic upgrade head
```

## Architecture

**Request flow:** User phone → OC200 captive portal redirect → `GET /portal` (creates Redis session, records visit) → 30s ad countdown → `POST /api/grant-access` (consumes session, calls Omada API to authorize MAC) → 1hr WiFi access.

**Key modules:**
- `server/main.py` — App factory with lifespan handler (init DB, Redis, Omada on startup)
- `server/routers/portal.py` — Captive portal page, validates MAC params from OC200 redirect
- `server/routers/auth.py` — `/api/grant-access` endpoint, orchestrates session→Omada→DB flow
- `server/routers/admin.py` — Admin dashboard (HTML inline) + all `/admin/api/*` JSON endpoints (~1300 lines, dashboard HTML/CSS/JS embedded)
- `server/services/omada.py` — OmadaClient: authenticates with OC200, authorizes/deauthorizes MACs
- `server/services/redis_service.py` — Session management (create/consume), anti-spam cooldowns, active user tracking
- `server/models/database.py` — SQLAlchemy ORM models (Hotspot, Visit, AdView, AccessGrant, DirectAdvertiser)
- `server/config.py` — Pydantic Settings, all config from env vars

**Frontend is split:**
- `frontend/templates/` — Portal HTML (user-facing captive portal page)
- `frontend/static/` — CSS + JS for both portal and admin
- Admin dashboard HTML is embedded directly in `server/routers/admin.py`

**Auth:** Admin endpoints use HTTP Basic Auth (`secrets.compare_digest`). Portal/grant endpoints are public but session-validated.

**Database tables:** `hotspots` (AP info), `visits` (traffic logs), `ad_views` (ad impressions), `access_grants` (WiFi grants with expiry), `direct_advertisers` (direct ad deals).

## API Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /portal` | None | Captive portal page (OC200 redirects here) |
| `POST /api/grant-access` | Session | Grant WiFi after ad view |
| `GET /health` | None | Health check |
| `GET /admin/` | Basic | Admin dashboard |
| `GET /admin/api/stats` | Basic | Overall statistics |
| `GET /admin/api/hotspots` | Basic | Hotspot list |
| `POST /admin/api/hotspots` | Basic | Create hotspot |
| `PATCH /admin/api/hotspots/{id}` | Basic | Update/toggle hotspot |
| `GET /admin/api/revenue` | Basic | Revenue analytics |
| `GET /admin/api/live` | Basic | Real-time online users |
| `GET /admin/api/visits` | Basic | Visit history (paginated) |
| `GET /admin/api/security` | Basic | Security overview |

## Deployment

Two options: **Zeabur** (config in `zeabur.json`) or **self-hosted VPS** (`deploy/setup.sh` for Ubuntu 22.04 one-click setup, `deploy/update.sh` for rolling updates, `deploy/backup.sh` for DB backups).

## Testing Notes

Tests use SQLite in-memory DB via fixtures in `server/tests/conftest.py`. Omada API calls are mocked. Redis service is mocked in tests.
