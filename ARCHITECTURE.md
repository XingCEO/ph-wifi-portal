# PH WiFi Ad System — 系統架構文件

> 菲律賓「看廣告換免費上網」服務架構設計  
> 參考 Purple WiFi 雲端模型，完全自建

---

## 一、系統全景圖

```
[用戶手機/平板]
      │
      │ 1. 連到 WiFi，開啟瀏覽器
      ▼
[MikroTik 路由器]
      │
      │ 2. Hotspot 攔截所有 HTTP 請求
      │    → 重定向到 VPS Captive Portal
      ▼
[VPS 廣告伺服器] — Singapore (低延遲到 PH)
      │
      ├── Nginx (reverse proxy + SSL)
      ├── FastAPI App (業務邏輯)
      ├── Redis (session / rate limiting)
      ├── PostgreSQL (用戶/廣告/收入記錄)
      │
      │ 3. 顯示廣告頁（Adcash Interstitial）
      │ 4. 用戶看完廣告（30秒倒數）
      │ 5. POST /api/grant-access
      ▼
[MikroTik API]
      │
      │ 6. 開通該用戶 MAC address 上網
      │    時效：60 分鐘
      ▼
[用戶可以自由上網 60 分鐘]
```

---

## 二、VPS 廣告伺服器元件

### 2.1 技術棧

| 元件 | 技術 | 用途 |
|------|------|------|
| Web Server | Nginx 1.24 | Reverse proxy、SSL termination、靜態文件 |
| API Backend | FastAPI (Python 3.11) | 業務邏輯 API |
| Session Store | Redis 7 | 用戶 session、rate limiting、MAC 計時 |
| Database | PostgreSQL 15 | 持久化記錄：用戶、廣告曝光、收入 |
| Ad Network | Adcash (primary) + 直接廣告主 (fallback) | 廣告變現 |
| Container | Docker + Docker Compose | 部署管理 |
| SSL | Let's Encrypt (Certbot) | HTTPS |

### 2.2 資料庫 Schema

```sql
-- 熱點管理
CREATE TABLE hotspots (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    location    VARCHAR(200),
    router_ip   INET NOT NULL,
    router_port INTEGER DEFAULT 8728,
    router_user VARCHAR(50) NOT NULL,
    router_pass VARCHAR(100) NOT NULL,
    api_key     VARCHAR(64) UNIQUE NOT NULL,
    active      BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 用戶 session 記錄
CREATE TABLE user_sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hotspot_id   UUID REFERENCES hotspots(id),
    mac_address  MACADDR NOT NULL,
    ip_address   INET,
    granted_at   TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ,
    duration_min INTEGER DEFAULT 60,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- 廣告曝光記錄
CREATE TABLE ad_impressions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hotspot_id   UUID REFERENCES hotspots(id),
    mac_address  MACADDR NOT NULL,
    ad_network   VARCHAR(50) DEFAULT 'adcash',
    ad_zone_id   VARCHAR(50),
    viewed_at    TIMESTAMPTZ DEFAULT NOW(),
    completed    BOOLEAN DEFAULT false,
    revenue_usd  DECIMAL(10,6) DEFAULT 0
);

-- 每日統計（預聚合，加速 dashboard）
CREATE TABLE daily_stats (
    date         DATE NOT NULL,
    hotspot_id   UUID REFERENCES hotspots(id),
    unique_users INTEGER DEFAULT 0,
    impressions  INTEGER DEFAULT 0,
    completions  INTEGER DEFAULT 0,
    revenue_usd  DECIMAL(10,4) DEFAULT 0,
    PRIMARY KEY (date, hotspot_id)
);

-- Index
CREATE INDEX idx_user_sessions_mac ON user_sessions(mac_address, expires_at);
CREATE INDEX idx_ad_impressions_date ON ad_impressions(viewed_at, hotspot_id);
```

---

## 三、MikroTik 路由器設定

### 3.1 Hotspot 模式設定

在 MikroTik RouterOS 上執行（透過 Winbox 或 SSH）：

```routeros
# 1. 啟用 Hotspot
/ip hotspot setup
# → 選擇 bridge interface（接 WiFi AP 的那個）
# → 設定 DNS name: portal.yourdomain.com

# 2. 設定 Hotspot Profile
/ip hotspot profile set default login-by=http-chap
/ip hotspot profile set default http-cookie-lifetime=1h

# 3. 自訂 Redirect URL（指向 VPS）
/ip hotspot profile set default login-page=https://portal.yourdomain.com/portal

# 4. 設定 DNS（讓未認證用戶能解析 VPS 域名）
/ip dns set servers=8.8.8.8,1.1.1.1
```

### 3.2 Walled Garden（白名單）

允許未認證用戶存取 VPS（顯示廣告頁必須）：

```routeros
# HTTP Walled Garden
/ip hotspot walled-garden add dst-host=portal.yourdomain.com action=allow
/ip hotspot walled-garden add dst-host=*.adcash.com action=allow
/ip hotspot walled-garden add dst-host=*.adcashmedia.com action=allow
/ip hotspot walled-garden add dst-host=*.googleapis.com action=allow

# IP-level Walled Garden（加上 VPS IP，防 DNS 問題）
/ip hotspot walled-garden ip add dst-address=<VPS_IP> action=allow
```

### 3.3 API 對接設定

MikroTik RouterOS API 設定（讓 VPS 可以控制路由器）：

```routeros
# 啟用 API
/ip service enable api
/ip service set api port=8728

# 建立專用 API 用戶（最低權限）
/user add name=wifi-api password=<強密碼> group=write
/user set wifi-api policy=api,read,write,ftp

# 防火牆：只允許 VPS IP 連入 API
/ip firewall filter add chain=input src-address=<VPS_IP> dst-port=8728 protocol=tcp action=accept
/ip firewall filter add chain=input dst-port=8728 protocol=tcp action=drop
```

---

## 四、廣告伺服器完整流程

### 4.1 用戶抵達 Portal（Step by Step）

```
Step 1: 用戶連 WiFi
  → 手機自動偵測 captive portal（HTTP probe）
  → MikroTik 攔截，302 redirect 到：
    https://portal.yourdomain.com/portal?mac=XX:XX:XX:XX:XX:XX&ip=192.168.x.x&hotspot=<hotspot_id>

Step 2: Portal 頁面載入
  → FastAPI 接收請求
  → 查詢 Redis：此 MAC 是否在冷卻期（1小時限制）
  → 如果在冷卻期：顯示「請稍後再試」頁面
  → 如果不在冷卻期：顯示廣告頁

Step 3: 廣告展示
  → 載入 Adcash Interstitial 廣告
  → 開始 30 秒倒數計時
  → 在 Redis 記錄此次廣告展示（防刷用）
  → 在 DB 建立 ad_impression 記錄

Step 4: 用戶完成廣告
  → 30 秒倒數結束，或用戶點擊廣告後返回
  → 前端 POST /api/ad-viewed { mac, hotspot_id, impression_id }
  → 伺服器驗證 impression_id 有效
  → 生成 one-time access token（UUID，TTL 60秒）
  → 回傳 token

Step 5: 開通上網
  → 前端自動 POST /api/grant-access { token, mac }
  → 伺服器驗證 token（Redis 取出，用完即刪）
  → 呼叫 MikroTik API：新增 MAC 到 allowed list，TTL 60分鐘
  → 在 Redis 設定 MAC 冷卻計時器（1小時）
  → 更新 DB：user_sessions, ad_impressions.completed = true
  → 回傳成功，前端顯示「上網開通！」

Step 6: 60 分鐘後自動到期
  → MikroTik 自動斷開（hotspot 本身有時限控制）
  → 或由 background job 每分鐘掃描到期 session，呼叫 API 移除
```

### 4.2 廣告展示邏輯

```
Primary: Adcash Interstitial (Zone ID: 設定在環境變數)
  ↓ 如果 Adcash 載入失敗（timeout 3秒）
Fallback A: 直接廣告主橫幅（本地 HTML banner）
  ↓ 如果沒有直接廣告主
Fallback B: 自家宣傳頁（推薦其他熱點位置）
```

### 4.3 防刷廣告機制

```
Redis Key: cooldown:{mac_address}
  TTL: 3600 秒（1小時）
  Value: hotspot_id + timestamp

Redis Key: impression:{impression_id}
  TTL: 120 秒（防重放攻擊）
  Value: { mac, hotspot_id, created_at }

Redis Key: token:{access_token}
  TTL: 60 秒（one-time use）
  Value: { mac, hotspot_id, impression_id }
```

額外安全措施：
- MAC 地址格式驗證（防偽造參數）
- Access token 一次性使用（Redis 取出後立即刪除）
- Hotspot API key 驗證（路由器必須帶 key 才能呼叫 API）
- Rate limiting：同一 IP 每分鐘最多 10 次 API 請求

---

## 五、數據追蹤 & Dashboard

### 5.1 追蹤指標

| 指標 | 來源 | 更新頻率 |
|------|------|---------|
| 每個熱點用戶數（日） | user_sessions | 即時 |
| 廣告曝光次數 | ad_impressions | 即時 |
| 完成率（CTR） | completions/impressions | 每小時聚合 |
| 估算收入（USD） | CPM × impressions / 1000 | 每小時聚合 |
| 在線用戶列表 | MikroTik API 即時拉取 | 每30秒刷新 |

### 5.2 Dashboard 架構

```
GET /dashboard → 管理員頁面（Basic Auth 保護）
GET /api/stats → JSON 數據（API key 保護）

數據來源：
  - PostgreSQL daily_stats（歷史趨勢）
  - Redis（即時在線用戶）
  - MikroTik API（路由器狀態）
```

---

## 六、部署架構

```
Ubuntu 22.04 VPS (Singapore)
├── Docker Compose
│   ├── nginx (443, 80)
│   ├── app (FastAPI, port 8000, internal)
│   ├── redis (port 6379, internal)
│   └── postgres (port 5432, internal)
├── Certbot (Let's Encrypt SSL)
└── UFW Firewall (只開 80, 443, 22)
```

---

## 七、成本估算

| 項目 | 方案 | 月費 |
|------|------|------|
| VPS | DigitalOcean Droplet 2GB/Singapore | $12 USD |
| 域名 | Namecheap .com | $1 USD |
| SSL | Let's Encrypt | 免費 |
| **合計** | | **~$13 USD/月** |

**預估收入**（1個熱點，日流量100人）：
- Adcash CPM（菲律賓）：$0.3 ~ $0.8 USD
- 日收入：100 × $0.5 / 1000 × 1000 = $0.05 USD → 換算 ~$1.5/月
- **10個熱點**：~$15/月 → 接近損益平衡
- **50個熱點**：~$75/月 → 純利約 $60/月
