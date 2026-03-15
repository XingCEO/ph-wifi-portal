# 第一次部署完整指南（從零開始）

> 預計時間：2-3 小時  
> 難度：中等（有基本 Git 和網路知識即可）

---

## Prerequisites 前置需求

在開始之前，確認你有以下東西：

- [ ] **Zeabur 帳號** → https://zeabur.com（可用 GitHub 登入）
- [ ] **GitHub 帳號** → https://github.com
- [ ] **域名**（推薦 Namecheap，約 $10-12/年）→ https://namecheap.com
- [ ] **OC200 + EAP225 + EAP650** 已開箱並通電
- [ ] 電腦可以連到 OC200 同一網段

---

## Step 1: GitHub — 推送代碼

### 1.1 初始化並推送
在 `ph-wifi-system/` 目錄執行：

```bash
# 初始化 git repo
git init

# 設定 .gitignore（防止把密碼推上去）
cat > .gitignore << 'EOF'
# 環境變數（絕對不能推！）
server/.env
*.env
.env.*

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/

# 系統
.DS_Store
*.log
EOF

# 加入所有文件
git add .
git status   # 確認 .env 沒有在列表中！

# 提交
git commit -m "feat: initial PH WiFi portal system"

# 連接 GitHub repo（先在 GitHub 建立空 repo）
git remote add origin https://github.com/XingCEO/ph-wifi-portal
git branch -M main
git push -u origin main
```

### 1.2 在 GitHub 建立 Repo
1. 前往 https://github.com/new
2. Repository name: `ph-wifi-portal`
3. **Private**（推薦，保護你的代碼）
4. 不要初始化（不勾選 README、.gitignore）
5. 點 Create repository

---

## Step 2: Zeabur — 部署後端

### 2.1 建立 Zeabur Project
1. 前往 https://zeabur.com，登入
2. 點擊 **New Project**
3. 輸入名稱：`ph-wifi-portal`
4. 選擇區域：**Southeast Asia（Singapore）**（離菲律賓近，延遲低）

### 2.2 部署 GitHub Repo
1. 在 Project 中點擊 **+ Add Service**
2. 選擇 **GitHub**
3. 授權 Zeabur 存取你的 GitHub
4. 選擇 `ph-wifi-portal` repo
5. Zeabur 會自動偵測 Python 專案並開始 Build

### 2.3 Add PostgreSQL Service
1. 再點 **+ Add Service**
2. 選擇 **Database** → **PostgreSQL**
3. 版本選 **16**
4. 建立後，點擊 PostgreSQL service → **Environment Variables**
5. 複製 `DATABASE_URL`（格式：`postgresql://user:pass@host:5432/dbname`）

### 2.4 Add Redis Service
1. 再點 **+ Add Service**
2. 選擇 **Database** → **Redis**
3. 建立後複製 `REDIS_URL`

### 2.5 設定環境變數
點擊 App Service → **Environment Variables** → **+ Add Variable**

必填的環境變數：

```bash
# 資料庫
DATABASE_URL=postgresql://...         # 從 PostgreSQL service 複製
REDIS_URL=redis://...                  # 從 Redis service 複製

# Omada Controller
OMADA_HOST=https://YOUR-OC200-IP:8043  # OC200 的 IP 或域名
OMADA_SITE_ID=YOUR_CONTROLLER_ID       # 見 OC200-SETUP.md Step 7
OMADA_USERNAME=ph_wifi_api             # Operator 帳號
OMADA_PASSWORD=YOUR_OPERATOR_PASSWORD  # Operator 密碼

# Adcash 廣告
ADCASH_ZONE_KEY=AC_XXXXXXX            # 見 ADCASH-SETUP.md Step 3
ADCASH_ENABLED=true
AD_DISPLAY_SECONDS=15

# 系統設定
SECRET_KEY=your-random-secret-key-min-32-chars  # 隨機字串
ENVIRONMENT=production
LOG_LEVEL=INFO

# 管理員帳號
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-admin-password
```

> 產生隨機 SECRET_KEY：`python -c "import secrets; print(secrets.token_hex(32))"`

### 2.6 綁定域名
1. App Service → **Domains**
2. 點擊 **+ Add Domain**
3. 方案 A：使用 Zeabur 免費子域名（`ph-wifi-portal.zeabur.app`）
4. 方案 B：綁定自有域名（需到 Namecheap 加 CNAME 記錄）

**Namecheap DNS 設定（方案 B）：**
| Type | Host | Value |
|------|------|-------|
| CNAME | wifi | `ph-wifi-portal.zeabur.app` |

等待 DNS 生效（5-60 分鐘），Zeabur 自動申請 Let's Encrypt 憑證。

### 2.7 確認部署成功
1. Zeabur → App Service → **Logs** tab
2. 看到 `Application startup complete.` 表示成功
3. 用瀏覽器訪問你的域名，應該看到 API 回應或 Portal 頁面

---

## Step 3: OC200 — 設定 External Portal

詳細設定見 [OC200-SETUP.md](OC200-SETUP.md)，這裡是快速版：

### 3.1 進入 Omada Controller
```
http://OC200的IP:8043
```

### 3.2 設定 External Portal URL
**Settings** → **Hotspot Manager** → **Portal**
- Portal Type：External Web Portal
- Portal URL：`https://YOUR-DOMAIN/portal`

### 3.3 設定 Walled Garden
**Settings** → **Hotspot Manager** → **Walled Garden**

加入以下域名：
```
YOUR-ZEABUR-DOMAIN
*.adcash.com
static.adcash.com
connectivitycheck.gstatic.com
captive.apple.com
```

---

## Step 4: 測試整個流程

### 4.1 手機測試（最真實）
1. 手機設定 → WiFi → 找到 `FreeWiFi_PH`
2. 點擊連線
3. **預期行為**：手機自動彈出 Captive Portal 頁面（廣告）
4. 等廣告計時器結束或點擊按鈕
5. **預期行為**：手機可以正常上網

### 4.2 後端確認
```bash
# 測試 API 健康狀態
curl https://YOUR-DOMAIN/api/health

# 預期回應
{"status": "ok", "database": "connected", "redis": "connected"}
```

### 4.3 Dashboard 確認
1. 打開 `https://YOUR-DOMAIN/admin`
2. 用 ADMIN_USERNAME / ADMIN_PASSWORD 登入
3. 確認：
   - Sessions 有新記錄
   - Impressions 計數增加
   - 地圖顯示連線位置

### 4.4 常見問題排查

| 問題 | 排查方向 |
|------|----------|
| 手機沒自動彈出 Portal | Walled Garden 少加 Google 域名 |
| Portal 頁面 404 | Zeabur 部署失敗，看 Logs |
| 廣告不顯示 | Adcash Zone Key 錯誤 / Walled Garden 少加 |
| 看完廣告無法上網 | Omada API 設定錯誤（Controller ID / 帳密）|
| Dashboard 無法登入 | 確認 ADMIN_USERNAME 環境變數 |

---

## 完成！🎉

恭喜，你的 PH WiFi 廣告系統已經上線。

**接下來：**
- 查看 [ADCASH-SETUP.md](ADCASH-SETUP.md) 優化廣告收入
- 查看 [BUSINESS-PLAYBOOK.md](BUSINESS-PLAYBOOK.md) 擴展業務
- 每天查看 Dashboard 確認系統正常運作
