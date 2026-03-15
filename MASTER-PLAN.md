# 菲律賓 WiFi 廣告系統 — 完整規劃
> 2026-03-15 | Felix 🦞
> 硬體：TP-Link EAP225 + EAP650-Outdoor + OC200 | 伺服器：Zeabur

---

## 系統架構總覽

```
┌─────────────────────────────────────────────────────┐
│                    ZEABUR 雲端伺服器                   │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌───────┐ │
│  │  FastAPI  │  │PostgreSQL│  │ Redis  │  │Static │ │
│  │  後端 API │  │  數據庫  │  │Session │  │前端頁面│ │
│  └──────────┘  └──────────┘  └────────┘  └───────┘ │
└─────────────────────────────────────────────────────┘
          ↕ HTTPS API (官方 Omada External Portal API)
┌─────────────────────────────────────────────────────┐
│              OC200 硬體控制器 (本地)                   │
│  管理所有 AP + Hotspot 設定 + Portal 重定向             │
└─────────────────────────────────────────────────────┘
          ↕ PoE 供電 + 管理
┌──────────────────┐    ┌──────────────────────────┐
│  EAP225 (室內)    │    │  EAP650-Outdoor (戶外)    │
│  AC1350 吸頂式    │    │  AX3000 WiFi 6 IP67      │
└──────────────────┘    └──────────────────────────┘
          ↕ WiFi 訊號
┌─────────────────────────────────────────────────────┐
│                  用戶手機/平板                          │
│  1. 連 WiFi → 2. 跳出廣告頁 → 3. 看廣告 → 4. 上網     │
└─────────────────────────────────────────────────────┘
```

---

## 完整數據流程（官方 Omada API）

```
Step 1: 用戶連上 WiFi SSID
Step 2: 嘗試開啟任何網頁
Step 3: EAP225/EAP650 攔截 HTTP，轉給 OC200
Step 4: OC200 重定向到 Zeabur Portal:
        https://你的域名/portal?
          clientMac=AA:BB:CC:DD:EE:FF  ← 用戶手機 MAC
          &apMac=11:22:33:44:55:66     ← AP 的 MAC
          &ssidName=FreeWiFi_PH
          &radioId=0                   ← 0=2.4G, 1=5G
          &site=manila_site1
          &redirectUrl=https://google.com

Step 5: Zeabur 伺服器顯示廣告頁面
Step 6: 用戶看廣告（30秒倒數）
Step 7: 用戶點擊「獲得免費上網 60 分鐘」

Step 8: Zeabur 後端呼叫 OC200 授權 API:
        POST https://OC200_IP:8043/{controllerId}/api/v2/hotspot/extPortal/auth
        Header: Csrf-Token: {token}
        Body: {
          "clientMac": "aa:bb:cc:dd:ee:ff",
          "apMac": "11:22:33:44:55:66",
          "ssidName": "FreeWiFi_PH",
          "radioId": 0,
          "site": "manila_site1",
          "time": 3600,           ← 秒數（1小時）
          "traffic": 0            ← 0 = 不限流量
        }

Step 9: OC200 確認，開通用戶上網
Step 10: 用戶跳轉到 Google（或廣告主落地頁）
Step 11: 60 分鐘後，OC200 自動斷線，用戶回到 Step 1
```

---

## Zeabur 伺服器結構

```
ph-wifi-portal/
├── main.py                 # FastAPI 主程式
├── routers/
│   ├── portal.py           # /portal 入口頁
│   ├── auth.py             # /api/auth 開通 API
│   ├── admin.py            # /admin Dashboard
│   └── webhook.py          # /api/ad-callback (Adcash webhook)
├── services/
│   ├── omada.py            # OC200 API 整合
│   ├── adcash.py           # Adcash 廣告整合
│   └── analytics.py        # 數據記錄
├── models/
│   ├── session.py          # Redis session 管理
│   └── database.py         # PostgreSQL 模型
├── frontend/
│   ├── portal.html         # 廣告頁面（手機優化）
│   ├── portal.css          # 輕量樣式 (<10KB)
│   ├── portal.js           # 倒數計時邏輯
│   └── admin/              # 管理 Dashboard
├── requirements.txt
└── zeabur.json             # Zeabur 部署設定
```

---

## 程式碼（核心部分）

### `main.py`

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import portal, auth, admin
import uvicorn

app = FastAPI(title="PH WiFi Portal")

app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.include_router(portal.router)
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/admin")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### `routers/portal.py`

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from services.session import create_session
import redis, json, os

router = APIRouter()
templates = Jinja2Templates(directory="frontend")
r = redis.from_url(os.getenv("REDIS_URL"))

@router.get("/portal", response_class=HTMLResponse)
async def portal_page(
    request: Request,
    clientMac: str,
    apMac: str,
    ssidName: str,
    site: str,
    radioId: int = 0,
    redirectUrl: str = "https://google.com"
):
    # 建立 session，記錄用戶資訊
    session_id = create_session(r, {
        "clientMac": clientMac,
        "apMac": apMac,
        "ssidName": ssidName,
        "site": site,
        "radioId": radioId,
        "redirectUrl": redirectUrl
    })
    
    # 記錄到資料庫（非同步）
    await log_visit(clientMac, apMac, site)
    
    return templates.TemplateResponse("portal.html", {
        "request": request,
        "session_id": session_id,
        "redirect_url": redirectUrl
    })
```

### `routers/auth.py`

```python
from fastapi import APIRouter, HTTPException
from services.omada import OmadaClient
from services.session import get_session, mark_used
import redis, os

router = APIRouter()
r = redis.from_url(os.getenv("REDIS_URL"))
omada = OmadaClient(
    host=os.getenv("OMADA_HOST"),      # OC200 IP
    port=int(os.getenv("OMADA_PORT", "8043")),
    controller_id=os.getenv("OMADA_CONTROLLER_ID"),
    operator=os.getenv("OMADA_OPERATOR"),
    password=os.getenv("OMADA_PASSWORD")
)

@router.post("/grant-access")
async def grant_access(session_id: str):
    # 取得 session 資料
    session = get_session(r, session_id)
    if not session:
        raise HTTPException(status_code=400, detail="Invalid or expired session")
    
    # 防止重複使用
    if session.get("used"):
        raise HTTPException(status_code=400, detail="Session already used")
    
    # 呼叫 OC200 API 開通
    result = await omada.grant_access(
        client_mac=session["clientMac"],
        ap_mac=session["apMac"],
        ssid_name=session["ssidName"],
        radio_id=session["radioId"],
        site=session["site"],
        time_seconds=3600  # 1 小時
    )
    
    # 標記 session 已使用
    mark_used(r, session_id)
    
    # 記錄廣告曝光到資料庫
    await log_ad_view(session["clientMac"], session["site"])
    
    return {"status": "granted", "redirect": session["redirectUrl"]}
```

### `services/omada.py`

```python
import httpx
import os

class OmadaClient:
    def __init__(self, host, port, controller_id, operator, password):
        self.base_url = f"https://{host}:{port}/{controller_id}"
        self.operator = operator
        self.password = password
        self._token = None
        self._session_id = None
    
    async def _login(self):
        """登入 OC200 取得 token"""
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                f"{self.base_url}/api/v2/hotspot/login",
                json={"name": self.operator, "password": self.password}
            )
            data = resp.json()
            self._token = resp.headers.get("Csrf-Token")
            # 從 cookie 取得 session
            self._session_id = resp.cookies.get("TPOMADA_SESSIONID")
    
    async def grant_access(self, client_mac, ap_mac, ssid_name, radio_id, site, time_seconds=3600):
        """開通用戶上網"""
        await self._login()
        
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                f"{self.base_url}/api/v2/hotspot/extPortal/auth",
                headers={
                    "Csrf-Token": self._token,
                    "Cookie": f"TPOMADA_SESSIONID={self._session_id}"
                },
                json={
                    "clientMac": client_mac,
                    "apMac": ap_mac,
                    "ssidName": ssid_name,
                    "radioId": radio_id,
                    "site": site,
                    "time": time_seconds,
                    "traffic": 0
                }
            )
            return resp.json()
```

### `frontend/portal.html`（手機優化版）

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Free WiFi — Watch Ad to Connect</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, sans-serif;
  background: #0a0a1a;
  color: #fff;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.logo { font-size: 2rem; margin-bottom: 8px; }
.title { font-size: 1.3rem; font-weight: 700; text-align: center; margin-bottom: 4px; }
.subtitle { color: #aaa; font-size: 0.9rem; text-align: center; margin-bottom: 30px; }

.ad-container {
  width: 100%;
  max-width: 400px;
  background: #1a1a2e;
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 20px;
}
.ad-label {
  background: #ff6b35;
  color: white;
  text-align: center;
  padding: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 1px;
}
.ad-slot {
  min-height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
}

.timer-ring {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
}
.timer-ring svg { transform: rotate(-90deg); }
.timer-ring circle {
  fill: none;
  stroke-width: 6;
}
.timer-bg { stroke: #333; }
.timer-progress {
  stroke: #4ecdc4;
  stroke-dasharray: 220;
  stroke-dashoffset: 0;
  transition: stroke-dashoffset 1s linear;
}
.timer-text {
  position: absolute;
  font-size: 1.4rem;
  font-weight: 700;
  color: #4ecdc4;
}
.timer-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.benefit {
  text-align: center;
  color: #4ecdc4;
  font-size: 0.9rem;
  margin-bottom: 20px;
}

.btn-connect {
  width: 100%;
  max-width: 400px;
  padding: 16px;
  background: #4ecdc4;
  color: #0a0a1a;
  border: none;
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  display: none;
}
.btn-connect:active { opacity: 0.8; }

.tagalog { color: #888; font-size: 0.8rem; text-align: center; margin-top: 12px; }
</style>
</head>
<body>

<div class="logo">📶</div>
<div class="title">Free WiFi — 1 Hour</div>
<div class="subtitle">Manood ng ad para makakuha ng libreng internet</div>

<div class="ad-container">
  <div class="ad-label">📢 ADVERTISEMENT</div>
  <div class="ad-slot" id="adSlot">
    <!-- Adcash Interstitial Script Here -->
    <script type="text/javascript">
      atOptions = {
        'key': 'YOUR_ADCASH_ZONE_KEY',
        'format': 'iframe',
        'height': 250,
        'width': 300,
        'params': {}
      };
    </script>
    <script src="//www.topcreativeformat.com/YOUR_ADCASH_ZONE_KEY/invoke.js"></script>
  </div>
</div>

<div class="timer-wrap">
  <div class="timer-ring">
    <svg width="80" height="80" viewBox="0 0 80 80">
      <circle class="timer-bg" cx="40" cy="40" r="35"/>
      <circle class="timer-progress" id="timerCircle" cx="40" cy="40" r="35"/>
    </svg>
  </div>
  <div class="timer-text" id="timerText">30</div>
</div>

<div class="benefit">✅ Watch ad → Get <strong>1 hour free WiFi</strong></div>

<button class="btn-connect" id="btnConnect" onclick="grantAccess()">
  🌐 Connect Now — Free 1 Hour
</button>

<div class="tagalog">Ang iyong koneksyon ay ligtas at libreng walang bayad</div>

<script>
const SESSION_ID = "{{ session_id }}";
const REDIRECT_URL = "{{ redirect_url }}";
const TOTAL_SECONDS = 30;
let secondsLeft = TOTAL_SECONDS;
const circle = document.getElementById('timerCircle');
const circumference = 2 * Math.PI * 35; // 220

circle.style.strokeDasharray = circumference;

const timer = setInterval(() => {
  secondsLeft--;
  document.getElementById('timerText').textContent = secondsLeft;
  
  const progress = (TOTAL_SECONDS - secondsLeft) / TOTAL_SECONDS;
  circle.style.strokeDashoffset = circumference * (1 - progress);
  
  if (secondsLeft <= 0) {
    clearInterval(timer);
    document.getElementById('btnConnect').style.display = 'block';
    document.getElementById('timerText').textContent = '✓';
    circle.style.stroke = '#51cf66';
  }
}, 1000);

async function grantAccess() {
  const btn = document.getElementById('btnConnect');
  btn.textContent = 'Connecting...';
  btn.disabled = true;
  
  try {
    const resp = await fetch('/api/grant-access', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: SESSION_ID })
    });
    const data = await resp.json();
    
    if (data.status === 'granted') {
      btn.textContent = '✅ Connected!';
      btn.style.background = '#51cf66';
      setTimeout(() => {
        window.location.href = REDIRECT_URL;
      }, 1000);
    }
  } catch(e) {
    btn.textContent = 'Try Again';
    btn.disabled = false;
  }
}
</script>
</body>
</html>
```

### `requirements.txt`

```
fastapi==0.115.0
uvicorn==0.30.0
httpx==0.27.0
redis==5.0.8
sqlalchemy==2.0.36
asyncpg==0.29.0
python-dotenv==1.0.1
jinja2==3.1.4
```

### `zeabur.json`

```json
{
  "build": {
    "type": "python"
  },
  "run": {
    "command": "uvicorn main:app --host 0.0.0.0 --port $PORT"
  }
}
```

### `.env`（環境變數，不要 commit）

```env
# Zeabur 會自動注入 DATABASE_URL 和 REDIS_URL

# OC200 控制器設定
OMADA_HOST=192.168.1.x          # OC200 的 IP
OMADA_PORT=8043
OMADA_CONTROLLER_ID=xxx         # 在 OC200 後台找
OMADA_OPERATOR=admin            # Hotspot 管理員帳號
OMADA_PASSWORD=your_password

# Adcash
ADCASH_ZONE_KEY=your_zone_key

# 安全
SECRET_KEY=random_32_char_string
```

---

## OC200 設定步驟

### 1. 建立 Hotspot
1. 登入 OC200 後台（http://OC200_IP:8088）
2. Hotspot Manager → Add Hotspot
3. Authentication: **External Portal**
4. Portal URL: `https://你的Zeabur域名/portal`

### 2. Walled Garden（關鍵！）
必須把以下 IP/域名加入 Walled Garden，讓用戶未認證前可以存取：
- 你的 Zeabur 域名（例：`ph-wifi.zeabur.app`）
- Adcash CDN：`*.adcash.com`, `*.topcreativeformat.com`
- 任何廣告主的域名（直接廣告時）

### 3. 建立 Operator 帳號
Hotspot Manager → Operator → Add
記下帳號密碼，填入 `.env` 的 OMADA_OPERATOR / OMADA_PASSWORD

---

## Zeabur 部署步驟

```bash
# 1. 把專案 push 到 GitHub
git init && git add . && git commit -m "init" && git push

# 2. 去 zeabur.com
# New Project → GitHub → 選你的 repo

# 3. 新增服務
# + Add Service → PostgreSQL（自動建立）
# + Add Service → Redis（自動建立）

# 4. 設定環境變數
# Variables → 貼上 .env 的內容

# 5. 域名
# 綁定一個域名（例：portal.你的域名.com）
# 或用 Zeabur 免費子域名：xxx.zeabur.app

# 完成！Zeabur 自動部署，自動 SSL
```

---

## 收入追蹤 Dashboard

管理員頁面（`/admin`）顯示：

| 指標 | 說明 |
|------|------|
| 今日 UV | 每個熱點的獨立訪客 |
| 廣告曝光次數 | 完成看廣告的人數 |
| 預估 Adcash 收入 | 曝光 × 估算 CPM |
| 目前在線用戶 | 各熱點即時數 |
| 總累積收入 | 所有時間加總 |

---

## 費用估算

| 項目 | 月費 |
|------|-----:|
| Zeabur（FastAPI + PostgreSQL + Redis）| $8–15 USD |
| 域名（.com）| $1 USD |
| 菲律賓 ISP（Converge 25Mbps/點）| ₱1,500/點 |
| **合計（1個熱點）**| ~₱2,000 + $16 USD |

---

## 下一步行動清單

- [ ] 把程式碼 push 到 GitHub
- [ ] Zeabur 部署
- [ ] OC200 設定 External Portal
- [ ] Adcash 申請 Publisher 帳號（adcash.com）
- [ ] 本地測試（用自己手機連 WiFi 測試全流程）
- [ ] 找第一個場地部署
- [ ] 拜訪廣告主談包月
