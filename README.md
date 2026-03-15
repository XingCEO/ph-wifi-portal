# PH WiFi Portal

Enterprise WiFi Ad Monetization System — Philippines Market

> Turn your TP-Link Omada WiFi network into a revenue-generating platform. Users watch a 30-second ad to receive 1 hour of free internet. No forced ads. Clean, professional UX.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  CLOUD (Zeabur / VPS)                               │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐ │
│  │ FastAPI  │ │PostgreSQL│ │ Redis  │ │  Nginx   │ │
│  └──────────┘ └──────────┘ └────────┘ └──────────┘ │
└─────────────────────────────────────────────────────┘
                    ↕ HTTPS (Omada External Portal API)
┌─────────────────────────────────────────────────────┐
│  ON-SITE                                            │
│  OC200 Controller → EAP225 (Indoor) + EAP650 (Outdoor)│
└─────────────────────────────────────────────────────┘
                    ↕ WiFi
                  User Devices
```

## Hardware

| Device | Model | Role |
|--------|-------|------|
| Indoor AP | TP-Link EAP225 AC1350 | Indoor WiFi coverage |
| Outdoor AP | TP-Link EAP650-Outdoor (IP67) | Outdoor coverage |
| Controller | TP-Link OC200 | Network management + Portal redirect |

## Quick Start

### Option A: Zeabur (Recommended)

1. Fork this repository
2. Connect to Zeabur: New Project → GitHub → Select repo
3. Add services: PostgreSQL + Redis
4. Set environment variables (see `server/.env.example`)
5. Deploy

### Option B: Self-hosted VPS

```bash
git clone https://github.com/XingCEO/ph-wifi-portal
cd ph-wifi-portal
sudo bash deploy/setup.sh
```

## Documentation

- [OC200 Setup Guide](docs/OC200-SETUP.md)
- [Adcash Integration](docs/ADCASH-SETUP.md)
- [Business Playbook](docs/BUSINESS-PLAYBOOK.md)
- [Revenue Optimization](docs/REVENUE-OPTIMIZATION.md)
- [Testing Guide](docs/TESTING.md)

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL, Redis
- **Frontend**: Vanilla HTML/CSS/JS, Inter font
- **Infrastructure**: Docker, Nginx, Let's Encrypt
- **Integration**: TP-Link Omada API v2, Adcash Publisher API

## License

MIT — Commercial use allowed with attribution.

---

## 繁體中文說明

企業級 WiFi 廣告變現系統，專為菲律賓市場設計。

用戶連上 WiFi → 自願觀看 30 秒廣告 → 獲得 1 小時免費上網。

硬體需求：TP-Link OC200 控制器 + EAP225（室內）+ EAP650-Outdoor（戶外）

### 快速開始

詳見 [OC200-SETUP.md](docs/OC200-SETUP.md) 和 [ADCASH-SETUP.md](docs/ADCASH-SETUP.md)。
