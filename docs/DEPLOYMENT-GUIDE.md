# AbotKamay WiFi 系統 — 完整部署說明書

> 2026-03-17 | Felix 🦞 整理（2026-03-17 更新：支援自架 VPS 全套方案）
> 從零到「手機連 WiFi → 看廣告 → 免費上網」的完整步驟

---

## 架構總覽

### 方案 A：自架 VPS 全套（推薦）

```
用戶手機
  │ 連 WiFi
  ▼
EAP225（現場 AP）
  │ 攔截 HTTP → redirect 到 Controller
  ▼
┌─ VPS 一台 ($12/月, 2GB RAM) ──────────────────┐
│                                                 │
│  Omada Controller → redirect 到 Portal          │
│  FastAPI → 顯示廣告 → 授權 MAC → 呼叫 Omada API│
│  Next.js → 品牌官網 + SaaS Dashboard            │
│  PostgreSQL + Redis + Nginx + Certbot           │
│                                                 │
│  一鍵部署：sudo bash deploy/setup.sh            │
└─────────────────────────────────────────────────┘
  ▼
用戶可以上網（1 小時）
```

### 方案 B：Zeabur + 獨立 VPS

```
用戶手機
  │ 連 WiFi
  ▼
EAP225（現場 AP）
  │ 攔截 HTTP → redirect 到 Controller
  ▼
VPS ($5/月) → Omada Controller
  │ redirect 到 External Portal
  ▼
Zeabur → FastAPI + PostgreSQL + Redis
  │ 顯示廣告頁 → 呼叫 VPS 的 Omada API 授權 MAC
  ▼
用戶可以上網（1 小時）
```

---

## Part 1：準備工作

### 方案 A 需要的東西
- 1 台 TP-Link EAP225（或其他 Omada 系列 AP）~₱3,000
- 1 台 VPS（2GB RAM，$12/月，推薦 Singapore 機房）
- 域名 + DNS 指向 VPS（主域名 + `omada.*` 子域名）
- GitHub 帳號

### 方案 B 需要的東西
- 1 台 TP-Link EAP225 ~₱3,000
- 1 台便宜 VPS（1GB RAM，$5/月，只跑 Omada Controller）
- Zeabur 帳號（跑 FastAPI + PostgreSQL + Redis）
- GitHub 帳號

---

## Part 2：VPS 設定 Omada Controller

### Step 1：開 VPS
- 買任何便宜 VPS（推薦新加坡/日本機房，離菲律賓近）
- Ubuntu 22.04 或 24.04
- 至少 1GB RAM

### Step 2：安裝 Omada Controller（Docker）
SSH 進 VPS：
```bash
ssh root@<VPS_IP>
```

安裝 Docker：
```bash
curl -fsSL https://get.docker.com | sh
```

跑 Omada Controller：
```bash
docker run -d \
  --name omada-controller \
  --restart always \
  -p 8088:8088 \
  -p 8043:8043 \
  -p 8843:8843 \
  -p 29810:29810/udp \
  -p 29811:29811 \
  -p 29812:29812 \
  -p 29813:29813 \
  -p 29814:29814 \
  -v omada-data:/opt/tplink/EAPController/data \
  -v omada-logs:/opt/tplink/EAPController/logs \
  mbentley/omada-controller:latest
```

### Step 3：開防火牆
```bash
ufw allow 8043/tcp
ufw allow 8088/tcp
ufw allow 8843/tcp
ufw allow 29810/udp
ufw allow 29811:29814/tcp
ufw enable
```

### Step 4：設定 Controller
1. 瀏覽器開 `https://<VPS_IP>:8043`
2. 建立管理員帳號
3. 建立站點（Site）

### Step 5：⚠️ 關鍵設定 — Controller hostname
**右上角齒輪 → 控制器設定：**
- **控制器主機名稱/IP：** 改成 `<VPS公網IP>`（不是 172.17.0.x！）
- **門戶認證主機名稱/IP：** 也改成 `<VPS公網IP>`
- **自動更新 IP：** 關掉
- 儲存

> ⚠️ 這是最容易踩的坑！Docker 內部 IP 會讓 Portal redirect 失敗。

---

## Part 3：EAP225 連接 Controller

### Step 1：EAP225 硬體接線
1. 把 **PoE 注入器**（隨 EAP225 附贈的黑色小盒子）接上：
   - **PoE 孔** → 用網路線連到 **EAP225**
   - **LAN 孔** → 用網路線連到你的**路由器**
   - **電源線** → 插牆壁電源
2. EAP225 的 LED 燈會亮起，等到**燈穩定不閃**（約 1-2 分鐘）

> 如果沒有 PoE 注入器，直接用 PoE 交換機供電也行。

### Step 2：找到 EAP225 的 IP
方法 A（推薦）：到路由器管理頁看 DHCP 客戶端列表，找 TP-Link 的裝置
方法 B：用 Omada Discovery Utility（需要 Java）
方法 C：試 `http://192.168.0.254` 或 `http://192.168.1.254`

### Step 3：EAP225 初始設定
1. 電腦/手機連上 EAP225 的 WiFi（`TP-Link_2.4GHz_XXXXXX` 或 `TP-Link_5GHz_XXXXXX`）
2. 瀏覽器開 EAP225 的 IP（例如 `http://192.168.1.16`）
3. 第一次進去會要你設帳密：
   - **Username：** `admin`
   - **Password：** 跟 Controller 站點設備帳號**一模一樣**（例如 `Ak@WiFi2026!ph`）
   - ⚠️ **這很重要！** 密碼要跟 Controller 站點設備帳號一致，不然 Adopt 會失敗
   - 密碼要求：10-64 字元，大小寫 + 數字 + 特殊符號，不能連續相同字元
4. 按 Next → 跳過 WiFi 設定（Skip）→ 進入管理頁面

### Step 4：設定 Controller IP
1. 進入管理頁面後，點上方 **Management** 分頁
2. 找到 **Controller Settings** 區塊
3. 設定：
   - **Inform URL/IP Address：** 填 `<VPS公網IP>`（例如 `107.174.155.124`）
   - **Cloud-Based Controller Management：** ❌ **關掉**（不要勾）
4. 按 **Save**

> 如果頁面顯示「This AP is being managed by Omada Controller」且無法操作：
> 代表 EAP 被 Cloud Controller 管著。去 Cloud → 裝置 → 移除此設備 → 等 1 分鐘 → 重新整理本地 GUI。

### Step 5：Controller Adopt
1. 開瀏覽器 → `https://<VPS_IP>:8043` → 登入
2. 進入你的站點（例如 AbotKamay）
3. 左邊 **Devices** → EAP225 應該出現（狀態：閒置中）
4. 勾選 → 按 **套用**（Adopt）
5. 等 1-2 分鐘，狀態會變：閒置中 → 預先配置 → **已連線** ✅

### Adopt 失敗怎麼辦

**情況 1：顯示「納管失敗」**
- 原因：EAP 帳密跟 Controller 站點設備帳號不一致
- 解法：
  1. Controller → 站點設定 → 設備帳號 → 改成跟 EAP 一樣的帳密
  2. 或：長按 EAP225 Reset 鍵 10 秒 → 重設 → 重新設定帳密（跟 Controller 一致）→ 重新 Adopt

**情況 2：EAP225 沒有出現在 Devices 列表**
- 原因：EAP 不知道 Controller IP
- 解法：回到 Step 4 確認 Inform URL 有填對

**情況 3：一直卡在「預先配置」**
- 解法：拔插 EAP 電源重啟

### Step 6：確認設定同步
1. Adopt 成功後，點 EAP225 看詳情
2. 確認 `configSyncStatus` 不是 3（3 = 未同步）
3. 如果是 3：拔插 EAP 電源，重啟後會重新拉設定

### SSH 連接 EAP225（偵錯用）
```bash
# Windows CMD（EAP225 的 SSH 用舊版演算法）
ssh -oHostKeyAlgorithms=+ssh-rsa -oPubkeyAcceptedAlgorithms=+ssh-rsa admin@<EAP_IP>

# 如果出現 HOST KEY CHANGED 錯誤
ssh-keygen -R <EAP_IP>
# 然後重新連
```

> EAP225 的 SSH 是 BusyBox，沒有 `uci`、`set-inform` 等指令。
> 設定 Controller IP 只能透過本地 GUI（Management → Controller Settings）。

---

## Part 4：設定 External Portal

### Step 1：建立 Hotspot Operator
Controller → 進入站點 → Hotspot → Operators → 新增：
- Name: `portal`
- Password: `<你設的密碼>`
- Site Privilege: 選你的站點

### Step 2：建立 WiFi SSID
Controller → 無線網路 → 新增 SSID：
- 名稱：`AbotKamay Free WiFi`
- 安全模式：無（Open）

### Step 3：設定 Portal
Controller → 驗證 → 門戶 → 新增：
- 驗證名稱：`AbotKamay Portal`
- 門戶：開啟
- SSID：選 `AbotKamay Free WiFi`
- **驗證類型：External Portal Server**
- **網址：** `https://你的域名/portal`（方案 A）或 `https://ph-wifi-portal.zeabur.app/portal`（方案 B）
- HTTPS 重新導向：啟用
- **導向頁面：原始網址**（⚠️ 不要選「成功頁面」！）

### Step 4：Walled Garden（白名單）
存取管理 → 預先驗證存取 → 啟用 → 新增：
- `ph-wifi-portal.zeabur.app`
- `<VPS_IP> / 32`

> ⚠️ 不要加 `portal.tplink.net`，那是 TP-Link 預設的，會衝突。

### Step 5：套用 + 重啟 EAP
- 按套用
- 拔插 EAP225 電源（讓它拉最新設定）
- 等 2 分鐘

---

## Part 5：部署主程式

### 方案 A：自架 VPS 全套（推薦）

Omada Controller 已經在 Part 2 裝好了。現在在**同一台 VPS** 部署整個系統：

```bash
git clone https://github.com/XingCEO/ph-wifi-portal.git
cd ph-wifi-portal
sudo bash deploy/setup.sh
```

setup.sh 會自動：
1. 裝 Docker（如果還沒裝）
2. 問你域名 + admin 密碼
3. 生成 `.env`（密鑰自動產生，`OMADA_HOST=omada` 指向同機 Docker 容器）
4. 簽 SSL 憑證（主域名 + omada 子域名）
5. 啟動 8 個 Docker 容器

然後填入 Omada 設定：
```bash
# 編輯 server/.env
nano server/.env
# 填入：
#   OMADA_CONTROLLER_ID=<Part 2 取得的 ID>
#   OMADA_OPERATOR=portal
#   OMADA_PASSWORD=<operator 密碼>

# 重啟 FastAPI
docker compose -f deploy/docker-compose.yml restart app
```

### 方案 B：Zeabur

#### 環境變數（Zeabur Service）
```
OMADA_HOST=<VPS_IP>
OMADA_PORT=8043
OMADA_CONTROLLER_ID=<從 /api/info 取得的 omadacId>
OMADA_OPERATOR=portal
OMADA_PASSWORD=<operator密碼>
OMADA_VERIFY_SSL=false
SECRET_KEY=<隨機字串>
ADMIN_USERNAME=<super admin帳號>
ADMIN_PASSWORD=<super admin密碼>
DATABASE_URL=${POSTGRESQL_URI}
REDIS_URL=${REDIS_URI}
```

### 取得 Controller ID
```bash
curl -sk "https://<VPS_IP>:8043/api/info" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['omadacId'])"
```

### 程式碼重點
- `server/services/omada.py` — Hotspot login 用 `{"name": "xxx", "password": "xxx"}`（不是 username！）
- `server/routers/auth.py` — grant_access 呼叫 Omada extPortal/auth，authType=4

---

## Part 6：測試清單

### 完整端到端測試
1. [ ] 手機連 `AbotKamay Free WiFi`
2. [ ] 自動跳出廣告頁面（不是 portal.tplink.net）
3. [ ] 倒數計時完成
4. [ ] 按「Get Free WiFi」按鈕
5. [ ] 顯示「Connected!」
6. [ ] 跳轉到 thanks 頁面
7. [ ] 手機可以正常上網

### API 測試
```bash
# Health
curl -s https://ph-wifi-portal.zeabur.app/health

# Portal 頁面
curl -s -o /dev/null -w "%{http_code}" "https://ph-wifi-portal.zeabur.app/portal?clientMac=AA:BB:CC:DD:EE:FF&apMac=3C:78:95:1A:22:74&ssidName=test&radioId=0&site=test"

# Omada Hotspot Login
curl -sk -X POST "https://<VPS_IP>:8043/<CONTROLLER_ID>/api/v2/hotspot/login" \
  -H "Content-Type: application/json" \
  -d '{"name":"portal","password":"<密碼>"}'

# Grant Access
curl -s -X POST "https://ph-wifi-portal.zeabur.app/api/grant-access" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<從portal頁面取得>"}'
```

---

## 踩過的坑（避雷清單）

| # | 坑 | 解法 |
|---|---|---|
| 1 | Controller hostname 是 Docker 內部 IP（172.17.0.x） | 手動改成公網 IP |
| 2 | EAP225 一直導到 portal.tplink.net | 「導向頁面」改成「原始網址」，不要選「成功頁面」 |
| 3 | Adopt 失敗（納管失敗） | EAP 帳密要跟 Controller 站點設備帳號一致 |
| 4 | EAP225 設定不同步（configSyncStatus: 3） | 拔插電源重啟 |
| 5 | Omada Cloud Essentials 不支援 External Portal | 必須自架 Controller |
| 6 | Zeabur port forwarding 是隨機的 | 不能用 Zeabur 跑 Controller，要用 VPS |
| 7 | Hotspot login 用 `name` 不是 `username` | `{"name":"xxx","password":"xxx"}` |
| 8 | extPortal/auth 需要 authType=4 | JSON body 加 `"authType": 4` |
| 9 | passlib + bcrypt 版本不相容 | 鎖定 bcrypt==4.0.1 |
| 10 | Next.js static export 不支援 middleware | 刪掉 middleware.ts，用 client-side redirect |
| 11 | FastAPI mount("/") 攔截所有路由 | 改用 catch-all GET route 放最後 |
| 12 | EAP225 SSH 沒有 set-inform | TP-Link 不是 UniFi，用 GUI 或 Discovery Utility |
| 13 | 學校網路擋非標準 port | 用 1.1.1.1 WARP 繞過 |
| 14 | portal.tplink.net 不能加白名單 | 刪掉它，只留你自己的域名 |

---

## 新增站點的快速步驟（之後部署新地點用）

1. 買 EAP225，接電 + 網路
2. 連上 EAP WiFi → 設 Controller IP → Save
3. Controller → Adopt
4. Portal 設定已經有了，新 EAP 自動套用
5. 測試手機連 WiFi
6. 完成！

---

## 費用

### 方案 A：自架 VPS 全套
| 項目 | 費用 |
|---|---|
| VPS（2GB RAM，全部服務） | ~$12/月 |
| 域名 | ~$10/年 |
| EAP225 硬體 | ~₱3,000 一次性 |
| **總計** | **~$12/月 + ₱3,000 硬體** |

### 方案 B：Zeabur + VPS
| 項目 | 費用 |
|---|---|
| VPS（只跑 Omada Controller） | ~$5/月 |
| Zeabur（FastAPI + DB + Redis） | ~$5/月 |
| EAP225 硬體 | ~₱3,000 一次性 |
| **總計** | **~$10/月 + ₱3,000 硬體** |

---

*這份文件花了你兩天的血淚換來的。下次部署照做，30 分鐘搞定。*
