# Changelog

## [SaaS MVP] — 2026-03-17

### 多租戶 SaaS 平台 Phase 1 MVP

在現有 AbotKamay WiFi 系統（FastAPI + PostgreSQL + Redis + Omada）基礎上擴展為多租戶 SaaS 平台。

---

## 新增檔案

### Backend (server/)

#### `server/routers/saas_auth.py`
- SaaS 客戶認證 router
- `POST /api/auth/register` — 註冊（建立 Organization + SaasUser + 免費訂閱）
- `POST /api/auth/login` — 登入，回傳 JWT token
- `GET /api/auth/me` — 取得當前用戶資訊
- JWT 認證（python-jose），bcrypt 密碼雜湊（passlib）
- 重複 email / org slug 檢查

#### `server/routers/dashboard.py`
- SaaS 客戶 Dashboard API router
- `GET /api/dashboard/stats` — 連線數、廣告次數、收入統計（支援 `?days=N`）
- `GET /api/dashboard/hotspots` — 此組織的場所列表（含 30 天連線數和收入）
- `POST /api/dashboard/hotspots` — 新增場所（含訂閱額度檢查、重複 MAC 檢查）
- `GET /api/dashboard/revenue` — 收入拆帳明細列表
- `POST /api/dashboard/provision` — 自助佈建：輸入 EAP MAC，建立 hotspot 並回傳 Omada 設定教學步驟
- Authorization: Bearer JWT token via `Authorization` header

#### `server/alembic/versions/003_saas_multitenant.py`
- 資料庫 migration（Revision 003）
- 新增 `organizations` 表
- 新增 `saas_users` 表
- 新增 `subscriptions` 表
- 新增 `revenue_splits` 表
- 在 `hotspots` 表新增 `org_id` 外鍵欄位

#### `server/tests/test_saas_auth.py`
- 8 個 pytest 測試案例：
  - 成功註冊
  - 重複 email 409
  - 重複 org slug 409
  - 密碼太短 422
  - 成功登入
  - 密碼錯誤 401
  - 不存在用戶 401
  - `/me` endpoint

#### `server/tests/test_dashboard.py`
- 8 個 pytest 測試案例：
  - 無場所時的統計
  - 空場所列表
  - 建立場所
  - 重複 MAC 409
  - 超出訂閱額度 403
  - 無 auth 401
  - 空收入列表
  - 自助佈建

### Frontend (web/)

#### `web/app/login/page.tsx`
- Next.js 登入頁面（client component）
- email + password 表單
- 登入成功後儲存 JWT 到 localStorage，跳轉 `/dashboard`
- 顯示/隱藏密碼切換

#### `web/app/register/page.tsx`
- Next.js 註冊頁面
- 姓名、email、密碼、組織名稱、org slug 輸入
- 組織名稱自動生成 slug
- 註冊成功後自動登入並跳轉 dashboard

#### `web/app/dashboard/layout.tsx`
- SaaS Dashboard 共用 Layout（client component）
- 左側 sidebar 導覽（Overview / Hotspots / Revenue）
- 響應式設計（mobile hamburger menu）
- 顯示用戶姓名、組織名、登出按鈕
- 未登入自動跳轉 `/login`

#### `web/app/dashboard/page.tsx`
- Dashboard 總覽頁面
- 顯示 4 個 stat cards：連線數、廣告次數、總收入、你的收益
- Quick Summary 表格
- Get Started 引導卡片

#### `web/app/dashboard/hotspots/page.tsx`
- 場所管理頁面
- 場所卡片列表（狀態、連線數、收入）
- 新增場所表單（含 Omada 設定）
- 自助佈建結果顯示（含逐步設定教學）

#### `web/app/dashboard/revenue/page.tsx`
- 收入明細頁面
- 總已付 / 待付金額 summary
- 收入拆帳記錄表格（period、廣告次數、總收入、你的份額、狀態）

---

## 修改檔案

### `server/models/database.py`
- 新增 `Organization` ORM model
- 新增 `SaasUser` ORM model
- 新增 `Subscription` ORM model
- 新增 `RevenueSplit` ORM model
- `Hotspot` 新增 `org_id` 外鍵欄位和 `organization` relationship

### `server/models/schemas.py`
- 新增 `OrganizationCreate`, `OrganizationResponse`
- 新增 `RegisterRequest`, `LoginRequest`, `TokenResponse`, `SaasUserResponse`
- 新增 `DashboardStatsResponse`
- 新增 `DashboardHotspotCreate`, `DashboardHotspotResponse`
- 新增 `RevenueSplitResponse`
- 新增 `ProvisionRequest`, `ProvisionResponse`

### `server/main.py`
- 新增 import `saas_auth`, `dashboard` routers
- 註冊兩個新 router

### `server/requirements.txt`
- 新增 `passlib[bcrypt]==1.7.4`
- 新增 `python-jose[cryptography]==3.5.0`

---

## 資料庫 Schema 摘要

```
organizations
  id, name, slug (unique), contact_email, contact_phone, is_active, created_at, updated_at

saas_users
  id, email (unique), hashed_password, full_name, organization_id (FK), role, is_active, is_verified, created_at, updated_at

subscriptions
  id, organization_id (FK), plan, status, monthly_fee_usd, revenue_share_pct, max_hotspots, starts_at, ends_at, created_at

revenue_splits
  id, organization_id (FK), hotspot_id (FK), period_start, period_end,
  total_revenue_usd, platform_pct, partner_pct, platform_amount_usd, partner_amount_usd,
  ad_views_count, status, notes, created_at

hotspots (已有，新增欄位)
  + org_id (FK -> organizations.id)
```

---

## 訂閱方案設計

| Plan       | 月費 USD | Revenue Share | Max Hotspots |
|------------|---------|---------------|--------------|
| free       | $0      | 70% partner   | 1            |
| starter    | TBD     | 70%           | 5            |
| pro        | TBD     | 75%           | 20           |
| enterprise | TBD     | 80%           | unlimited    |

---

## 測試結果

```
70 passed, 1 warning in 6.51s
```
（16 新增測試 + 54 原有測試，全部通過）

---

## API 端點總覽（新增）

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /api/auth/register` | None | SaaS 客戶註冊 |
| `POST /api/auth/login` | None | SaaS 客戶登入，回傳 JWT |
| `GET /api/auth/me` | JWT (query) | 取得當前用戶 |
| `GET /api/dashboard/stats` | JWT (Bearer) | Dashboard 統計 |
| `GET /api/dashboard/hotspots` | JWT (Bearer) | 場所列表 |
| `POST /api/dashboard/hotspots` | JWT (Bearer) | 新增場所 |
| `GET /api/dashboard/revenue` | JWT (Bearer) | 收入明細 |
| `POST /api/dashboard/provision` | JWT (Bearer) | 自助佈建 EAP |
