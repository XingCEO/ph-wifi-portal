# AbotKamay WiFi 系統 — 完整部署說明書

> 2026-03-17 | Felix 🦞 整理
> 從零到「手機連 WiFi → 看廣告 → 免費上網」的完整步驟

---

## 架構總覽

```
用戶手機
  │ 連 WiFi
  ▼
EAP225（現場 AP）
  │ 攔截 HTTP → redirect 到 Controller
  ▼
Omada Controller（VPS: 107.174.155.124）
  │ redirect 到 External Portal
  ▼
Zeabur FastAPI（ph-wifi-portal.zeabur.app）
  │ 顯示廣告頁 → 用戶看完廣告 → 按按鈕
  │ POST /api/grant-access → 呼叫 Omada API 授權 MAC
  ▼
用戶可以上網（1 小時）
```

---

## Part 1：準備工作

### 你需要的東西
- 1 台 TP-Link EAP225（或其他 Omada 系列 AP）~$40
- 1 台 VPS（任何廠商，$5-10/月，要能開 port 29810-29813 + 8043 + 8088）
- Zeabur 帳號（跑 FastAPI + PostgreSQL + Redis）
- GitHub 帳號（程式碼倉庫）

### 帳號清單
| 服務 | 帳號 | 用途 |
|---|---|---|
| Zeabur | XingCEO | 廣告系統 + 官網 |
| VPS | root | Omada Controller |
| Omada Controller | xingceo | 管理 AP |
| Hotspot Operator | portal | API 授權用 |
| SaaS Admin | xingceo / xingwifi2026 | Super Admin 後台 |

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

### Step 1：EAP225 接電 + 網路
- PoE 線接到路由器/交換機
- 等燈穩定

### Step 2：設定 Controller IP
- 電腦/手機連 EAP225 的 WiFi（TP-Link_XXXX）
- 開 `http://192.168.0.254` 或 EAP 的 IP
- 登入 → Management → Controller Settings
- **Inform URL/IP Address：** 填 `<VPS公網IP>`
- **Cloud-Based Controller Management：** 關掉
- Save

### Step 3：Adopt
- 回 Controller 管理頁 → Devices
- EAP225 會出現（閒置中 → 點 Adopt）
- 等 1-2 分鐘變「已連線」

> ⚠️ 帳密要一致！EAP225 的帳密要跟 Controller 站點設備帳號一樣，不然 Adopt 會失敗（「納管失敗」）。
> 如果失敗：長按 Reset 10 秒重設 EAP → 重新設定帳密 → 重新 Adopt。

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
- **網址：** `https://ph-wifi-portal.zeabur.app/portal`
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

## Part 5：Zeabur 廣告系統部署

### 環境變數（Zeabur Service）
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

| 項目 | 月費 |
|---|---|
| VPS（Omada Controller） | ~$0.50（$6/年） |
| Zeabur（廣告系統 + DB + Redis） | ~$5 |
| EAP225 硬體 | $40 一次性 |
| **總計** | **~$5.50/月 + $40 硬體** |

---

*這份文件花了你兩天的血淚換來的。下次部署照做，30 分鐘搞定。*
