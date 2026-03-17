# AbotKamay WiFi

**Free public WiFi platform for the Philippines.**

Users connect to WiFi, watch a short ad, and get free internet. Zero cost to users, ad revenue for operators. Evolving into a multi-tenant SaaS platform.

[繁體中文版在下方 ↓](#繁體中文)

---

## Architecture

```
┌─ VPS (single server) ──────────────────────────────────────────┐
│                                                                 │
│  ┌─ Nginx (:80/:443) ────────────────────────────────────┐     │
│  │  abotkamay.net       → Next.js + FastAPI              │     │
│  │  omada.abotkamay.net → Omada Controller               │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
│  Next.js (:3000)    FastAPI (:8000)    Omada Controller (:8043)│
│  Brand website      Portal + API       AP management            │
│                         │                    │                  │
│  PostgreSQL (:5432)  Redis (:6379)      Certbot (auto SSL)     │
│                                                                 │
│  AP communication ports: :29810/udp :29811-29814               │
└────────────────────────────┬────────────────────────────────────┘
                             │ Internet
                ┌─ On-site ──┴────────────┐
                │  TP-Link EAP225 AP      │
                │  → connects to VPS      │
                │  📱 Users               │
                └─────────────────────────┘
```

**Traffic Flow:**
1. User connects to the open WiFi SSID (no password)
2. Omada Controller redirects to `https://your-domain/portal`
3. Portal shows a short ad with countdown (default 30s)
4. After countdown, user clicks "Get Free WiFi"
5. FastAPI calls Omada API to authorize the user's MAC address
6. User gets free internet (default 1 hour)

> See the [繁體中文 section](#繁體中文) below for a detailed step-by-step connection flow diagram.

---

## Project Structure

```
ph-wifi-system/
├── web/                 Next.js 16 brand website (abotkamay.net)
│   ├── app/[lang]/      i18n pages (EN / Filipino / 繁體中文)
│   ├── app/dashboard/   SaaS customer dashboard
│   ├── app/superadmin/  Platform admin panel
│   └── dictionaries/    Translation JSON files
├── server/              FastAPI backend
│   ├── routers/         portal, auth, admin, saas_auth, dashboard, superadmin
│   ├── services/        Omada client, Redis session service
│   ├── models/          SQLAlchemy ORM + Pydantic schemas
│   ├── rate_limit.py    Shared rate limiter (slowapi)
│   └── tests/           121 async tests (pytest)
├── frontend/            Portal & admin static assets
│   ├── templates/       HTML templates (portal, thanks, admin dashboard)
│   └── static/          CSS + JS
└── deploy/              Production deployment
    ├── docker-compose.yml   8 services (Nginx, Next.js, FastAPI, PG, Redis, Omada, Certbot)
    ├── Dockerfile           FastAPI container (multi-stage)
    ├── nginx.conf           Reverse proxy (main site + Omada subdomain)
    ├── omada/               Standalone Omada deployment (for split setup)
    ├── setup.sh             One-click setup (Ubuntu 22.04+)
    ├── update.sh            Zero-downtime rolling updates
    └── backup.sh            Database backup + S3 upload
```

---

## Quick Start

### Prerequisites

- Ubuntu 22.04+ VPS (**2GB RAM** recommended, Omada Controller is Java-based)
- Domain name with DNS pointing to your VPS IP:
  - `abotkamay.net` → VPS IP
  - `omada.abotkamay.net` → VPS IP (same server)
- TP-Link EAP access points at the physical location
- Adcash publisher account (see [docs/ADCASH-SETUP.md](docs/ADCASH-SETUP.md))

> **No OC200 hardware needed.** The Omada Software Controller runs on the same VPS as your app, replacing the physical OC200 controller entirely.

### Installation

```bash
git clone https://github.com/XingCEO/ph-wifi-portal.git
cd ph-wifi-portal
sudo bash deploy/setup.sh
```

The setup script will:
1. Install Docker & Docker Compose
2. Open firewall ports (80, 443, 29810-29814 for AP communication)
3. Prompt for domain name + admin password
4. Generate `server/.env` with secure random keys
5. Obtain Let's Encrypt SSL certificate (main domain + omada subdomain)
6. Start all 8 services
7. Wait for Omada Controller to be ready
8. Print all URLs + next steps

### Post-Setup: Configure Omada Controller

After `setup.sh` completes:

1. Open `https://omada.your-domain.com` in your browser
2. Complete the Omada Controller setup wizard
3. Create a Site → WiFi SSID → set External Portal URL to `https://your-domain.com/portal`
4. Create a Hotspot Manager operator account
5. Note the `controller_id` from the URL bar
6. Edit `server/.env` — fill in `OMADA_CONTROLLER_ID`, `OMADA_OPERATOR`, `OMADA_PASSWORD`
7. Restart: `docker compose -f deploy/docker-compose.yml restart app`
8. At the physical site: set EAP AP's Controller Host to your VPS IP

### Local Development

```bash
# Backend (terminal 1) — runs in test mode (no Omada needed)
cd server
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Brand website (terminal 2)
cd web && npm install
npm run dev

# Tests
cd server && pytest tests/ -v
cd web && npm run lint
```

- Brand website: http://localhost:3000
- Portal: http://localhost:8000/portal
- Admin: http://localhost:8000/admin/
- API docs: http://localhost:8000/docs

When `OMADA_CONTROLLER_ID` is empty, FastAPI runs in **test mode** — `/api/grant-access` skips the Omada API call.

### Configuration

All configuration is in `server/.env` (auto-generated by setup.sh):

```env
# Application
ENVIRONMENT=production
SECRET_KEY=<auto-generated 64-char hex>

# Database
DATABASE_URL=postgresql+asyncpg://wifi_admin:PASSWORD@postgres:5432/ph_wifi
POSTGRES_USER=wifi_admin
POSTGRES_PASSWORD=<auto-generated>

# Redis
REDIS_URL=redis://redis:6379/0

# Omada Software Controller
OMADA_HOST=omada                    # Docker service name (same VPS)
OMADA_PORT=8043
OMADA_CONTROLLER_ID=<from Omada URL after setup>
OMADA_OPERATOR=<hotspot operator username>
OMADA_PASSWORD=<hotspot operator password>

# Adcash
ADCASH_ZONE_KEY=<your zone key>

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong password>

# Business Rules
AD_DURATION_SECONDS=30
SESSION_DURATION_SECONDS=3600       # 1 hour WiFi access
ANTI_SPAM_WINDOW_SECONDS=3600       # 1 hour between ads per device
```

---

## Hardware

**No OC200 required** — the Omada Software Controller replaces it. You only need APs at the physical location.

| Device | Model | Purpose | Price |
|--------|-------|---------|-------|
| Indoor AP | TP-Link EAP225 | Indoor coverage, AC1200, ~30m radius, PoE | ~₱3,000 |
| Outdoor AP | TP-Link EAP650-Outdoor | Outdoor coverage, AX3000, IP67, ~50m | ~₱6,000 |
| PoE Switch | Any 802.3af switch | Power the APs via Ethernet | ~₱1,500 |

**Typical setup:** 1-4x EAP225 (interior) + 0-2x EAP650-Outdoor (exterior). All APs connect to the cloud Omada Controller on your VPS over the internet.

---

## Deployment

### Option A: Self-Hosted VPS (Recommended)

One VPS runs everything: your app + Omada Controller + database.

```bash
sudo bash deploy/setup.sh   # Follow interactive prompts
```

| Provider | Region | Price | Latency to PH |
|----------|--------|-------|---------------|
| Vultr | Singapore | $12/mo (2GB) | ~30ms |
| DigitalOcean | Singapore | $12/mo (2GB) | ~35ms |
| Linode (Akamai) | Singapore | $12/mo (2GB) | ~35ms |

Docker Compose runs 8 services: Nginx, Next.js, FastAPI, PostgreSQL, Redis, Omada Controller, Certbot.

**Services & URLs:**

| URL | Service |
|-----|---------|
| `https://your-domain.com` | Brand website (Next.js) |
| `https://your-domain.com/portal` | Captive portal |
| `https://your-domain.com/admin/` | Admin dashboard |
| `https://your-domain.com/dashboard` | SaaS customer dashboard |
| `https://your-domain.com/superadmin` | Platform admin |
| `https://omada.your-domain.com` | Omada Controller (AP management) |

### Option B: Zeabur + Separate VPS

For those who prefer managed PaaS for the app, with a cheap VPS for Omada only.

- **Zeabur**: Deploys FastAPI + PostgreSQL + Redis (auto-detected via `zeabur.json`)
- **Vercel**: Deploys Next.js brand website (free tier)
- **Cheap VPS ($5/mo, 1GB RAM)**: Runs Omada Controller only (`deploy/omada/docker-compose.yml`)

Set `OMADA_HOST=<VPS_IP>` in Zeabur environment variables.

### Updates (Zero Downtime)

```bash
sudo bash deploy/update.sh              # Pull latest + rolling restart
sudo bash deploy/update.sh --skip-pull  # Rebuild only, no git pull
```

### Backup

```bash
bash deploy/backup.sh                         # Local backup (keeps 7)
bash deploy/backup.sh --s3=s3://bucket/path   # + upload to S3/R2
```

---

## SaaS Platform

The system supports multi-tenant operation where multiple business owners can manage their own WiFi hotspots.

### Tenant Model

```
Organization (business)
  └─ SaasUser (owner, JWT auth)
  └─ Subscription (free / starter / pro / enterprise)
  └─ Hotspot[] (limited by plan)
       └─ Visits, AdViews, AccessGrants
```

### Plans

| Plan | Hotspots | Revenue Share | Monthly Fee |
|------|:--------:|:------------:|:-----------:|
| Free | 1 | 70% | $0 |
| Starter | 3 | 75% | $9.99 |
| Pro | 10 | 80% | $29.99 |
| Enterprise | 100 | 85% | $99.99 |

### Auth

| Endpoint Type | Auth Method |
|---------------|-------------|
| Captive portal (`/portal`, `/api/grant-access`) | Redis session |
| SaaS customer (`/api/auth/*`, `/api/dashboard/*`) | JWT bearer token |
| Admin (`/admin/*`) | HTTP Basic Auth |
| Super Admin (`/api/superadmin/*`) | HTTP Basic Auth |

### Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `POST /api/grant-access` | 10/min per IP |
| `POST /api/auth/register` | 5/min per IP |
| `POST /api/auth/login` | 10/min per IP |
| `POST /api/auth/forgot-password` | 3/min per IP |
| Global default | 200/min per IP |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Brand website | Next.js 16, React 19, Tailwind CSS 4, Framer Motion, i18n (EN/FIL/ZH) |
| Backend | Python 3.11+, FastAPI 0.115, Uvicorn (async) |
| Database | PostgreSQL 16 (SQLAlchemy 2.0 async + asyncpg) |
| Cache | Redis 7 (sessions, anti-spam, active user tracking) |
| Auth | JWT (python-jose) for SaaS, HTTP Basic for admin, bcrypt for passwords |
| Rate limiting | slowapi (per-endpoint) + Nginx (per-zone) |
| Portal frontend | Vanilla HTML/CSS/JS |
| Admin dashboard | Alpine.js, Chart.js |
| WiFi Controller | Omada Software Controller 5.14 (Docker, replaces OC200 hardware) |
| Infrastructure | Docker Compose (8 services), Let's Encrypt SSL |
| Logging | structlog (JSON-formatted structured logging) |

### Brand Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Deep Blue | `#1B4F8A` | Primary brand color |
| Orange | `#F58220` | Accent, CTAs |
| Light Blue | `#0099DB` | WiFi/functional elements |
| Warm White | `#faf8f5` | Background |

---

## Revenue Estimate

| Daily Users | Monthly Ad Revenue | Location Example |
|------------|-------------------|-----------------|
| 50 | $3 - $6 | Small cafe, barbershop |
| 200 | $12 - $24 | Restaurant, clinic |
| 500 | $30 - $60 | Supermarket, bus terminal |
| 1,000 | $60 - $120 | Mall food court, wet market |

Add direct advertisers or paid skip options to increase revenue further.

---

## Documentation

| Document | Description |
|----------|-------------|
| [OC200 Setup](docs/OC200-SETUP.md) | Hardware controller setup (if using OC200 instead of software controller) |
| [Adcash Integration](docs/ADCASH-SETUP.md) | Publisher account, ad zone creation, revenue tracking, payout |
| [Revenue Optimization](docs/REVENUE-OPTIMIZATION.md) | CPM strategies, peak hours, direct advertiser outreach, paid tiers |
| [Walled Garden](docs/WALLED-GARDEN.md) | Complete allowed-domains list for pre-auth traffic |
| [Deployment Guide](docs/DEPLOYMENT-GUIDE.md) | Step-by-step deployment instructions |
| [Testing](docs/TESTING.md) | End-to-end test checklist |

---

## License

MIT

---
---

# 繁體中文

## AbotKamay WiFi — 菲律賓免費公共 WiFi SaaS 平台

讓免費 WiFi 成為持續被動收入。用戶觀看一段短廣告，即可獲得免費上網。用戶零費用，你賺廣告收益。支援多租戶 SaaS 模式，讓多個商家各自管理自己的 WiFi 站點。

## 架構說明

```
┌─ VPS 一台搞定 ─────────────────────────────────────────────┐
│                                                             │
│  Nginx (:80/:443)                                          │
│    abotkamay.net       → Next.js + FastAPI（你的程式）      │
│    omada.abotkamay.net → Omada Controller（網路管理後台）   │
│                                                             │
│  Next.js    FastAPI    Omada Controller                     │
│  品牌官網    Portal+API   AP管理                            │
│                                                             │
│  PostgreSQL   Redis    Certbot                              │
│                                                             │
│  AP 通訊 ports: :29810/udp :29811-29814                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ Internet
              ┌─ 現場 ─────┴─────┐
              │  TP-Link EAP AP  │
              │  📱 用戶         │
              └──────────────────┘

```

**完整連線流程：**

```
📱 用戶手機                          VPS（你的伺服器）
    │                                 ┌────────────────────────────────┐
    │                                 │ Omada Controller │ FastAPI     │
    │                                 │ (取代 OC200)     │ +Redis +PG │
    │                                 └────────────────────────────────┘
    │                                              │
    │  1. 連上 WiFi SSID                           │
    ├──────────► EAP225 AP ───────────────────────►│
    │            (現場硬體)                         │
    │                                              │
    │  2. 開任何網頁                               │
    ├──────────► EAP225 ──────────────────────────►│
    │                                 Omada：「這個 MAC 沒認證」
    │                                 302 → https://域名/portal
    │                                      ?clientMac=XX&apMac=YY
    │                                              │
    │  3. 被重導向到 Portal                        │
    ├─────────────────────────────────────────────►│ FastAPI /portal
    │                                              │  → Redis 建立 session
    │                                              │  → DB 記錄 visit
    │  4. 收到廣告頁面                             │
    │◄─────────────────────────────────────────────┤
    │                                              │
    │  5. 看廣告 30 秒 ⏳（Adcash）                │
    │                                              │
    │  6. 點擊「免費上網」                          │
    │     POST /api/grant-access                   │
    ├─────────────────────────────────────────────►│ FastAPI:
    │                                              │  → Redis 原子消費 session
    │                                              │  → Redis SET NX 防刷
    │                                              │  → Omada API: POST /auth
    │                                              │    {clientMac, time: 3600}
    │                                              │
    │                                 Omada Controller:
    │                                 「放行這個 MAC 1 小時」
    │                                       │
    │                                 通知 EAP225 AP
    │                                       │
    │  7. 回傳 redirect URL                │
    │◄─────────────────────────────────────────────┤ DB 記錄 ad_view + grant
    │                                              │
    │  8. 🎉 自由上網！                            │
    ├──────────► EAP225 ──────────► Internet       │
    │                                              │
    │  9. 1 小時後自動斷開                         │
    │◄──────── (Omada 到期撤銷) ───────────────────┤
    │                                              │
    │  10. 重複步驟 1                              │
```

## 快速開始

```bash
git clone https://github.com/XingCEO/ph-wifi-portal.git
cd ph-wifi-portal
sudo bash deploy/setup.sh
```

一鍵腳本自動完成：Docker 安裝、防火牆設定、SSL 憑證申請、8 個服務啟動、資料庫遷移。

**不需要 OC200 硬體**，Omada Software Controller 跑在同一台 VPS 上。

### 設定完成後：

1. 開瀏覽器 → `https://omada.你的域名` → 完成 Omada Controller 初始設定
2. 建立 Site → WiFi SSID → External Portal URL: `https://你的域名/portal`
3. 建立 Hotspot Manager operator 帳號
4. 取得 `controller_id`（URL 中的長字串）
5. 編輯 `server/.env` → 填入 `OMADA_CONTROLLER_ID`、`OMADA_OPERATOR`、`OMADA_PASSWORD`
6. `docker compose -f deploy/docker-compose.yml restart app`
7. 現場 EAP AP 設定 Controller Host → 你的 VPS IP

## 本地開發

```bash
# 後端（test mode，不需要 Omada）
cd server && cp .env.example .env && uvicorn main:app --reload --port 8000

# 品牌官網
cd web && npm install && npm run dev

# 測試
cd server && pytest tests/ -v     # 121 個測試
cd web && npm run lint             # ESLint
```

## 硬體設備

不需要 OC200 控制器，只需要現場 AP：

| 設備 | 用途 | 價格 |
|------|------|------|
| TP-Link EAP225 | 室內 AP，AC1200，~30m | ~₱3,000 |
| TP-Link EAP650-Outdoor | 戶外 AP，AX3000，IP67 | ~₱6,000 |
| PoE Switch | 供電給 AP | ~₱1,500 |

## 部署方式

### 方式 A：自架 VPS（推薦）

一台 VPS 跑所有東西，包含 Omada Controller。

```bash
sudo bash deploy/setup.sh
```

8 個 Docker 服務：Nginx、Next.js、FastAPI、PostgreSQL、Redis、Omada Controller、Certbot。

推薦 **2GB RAM** VPS（Omada Controller 是 Java，需要較多記憶體），Vultr/DO/Linode Singapore ~$12/月。

### 方式 B：Zeabur + 獨立 VPS

- **Zeabur**：部署 FastAPI + PG + Redis
- **Vercel**：部署 Next.js 品牌官網（免費）
- **便宜 VPS ($5/月)**：只跑 Omada Controller（`deploy/omada/docker-compose.yml`）

## SaaS 多租戶系統

| 方案 | 站點數 | 收益分成 | 月費 |
|------|:------:|:-------:|:----:|
| Free | 1 | 70% | $0 |
| Starter | 3 | 75% | $9.99 |
| Pro | 10 | 80% | $29.99 |
| Enterprise | 100 | 85% | $99.99 |

## 技術棧

| 層級 | 技術 |
|------|------|
| 品牌官網 | Next.js 16、React 19、Tailwind CSS 4、Framer Motion、i18n 三語 |
| 後端 | Python 3.11+、FastAPI、Uvicorn（非同步） |
| 資料庫 | PostgreSQL 16（SQLAlchemy 2.0 async） |
| 快取 | Redis 7（session、防刷、在線追蹤） |
| 認證 | JWT（SaaS 用戶）、HTTP Basic（管理員）、bcrypt（密碼） |
| WiFi 控制 | Omada Software Controller 5.14（Docker，取代 OC200 硬體） |
| 基礎設施 | Docker Compose（8 服務）、Let's Encrypt SSL |

## 收益估算

| 日連線人次 | 月廣告收益 | 場景 |
|-----------|-----------|------|
| 50 人     | $3 - $6   | 小咖啡廳、理髮店 |
| 200 人    | $12 - $24 | 餐廳、診所 |
| 500 人    | $30 - $60 | 超市、公車站 |
| 1,000 人  | $60 - $120| 商場美食街、菜市場 |

## 文件

- [OC200 設定指南](docs/OC200-SETUP.md) — 硬體控制器設定（如果使用 OC200 而非軟體版）
- [Adcash 整合指南](docs/ADCASH-SETUP.md) — 申請帳號、建立廣告 Zone、收款
- [收入優化指南](docs/REVENUE-OPTIMIZATION.md) — 廣告策略、高流量時段、直接廣告主
- [部署指南](docs/DEPLOYMENT-GUIDE.md) — 完整部署步驟
