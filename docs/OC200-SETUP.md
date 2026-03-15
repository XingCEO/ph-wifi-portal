# OC200 硬體控制器設定指南

> **TP-Link OC200 Omada Hardware Controller**
> 搭配 EAP225（室內）、EAP650-Outdoor（戶外 IP67）

---

## Section 1：初始設定

### 1.1 硬體連接

```
[光纖/WAN] → [路由器] → [OC200 WAN 口]
                       [OC200 LAN 口] → [Switch]
                                       ├── [EAP225 #1]
                                       ├── [EAP225 #2]
                                       └── [EAP650-Outdoor]
```

OC200 需要透過 PoE Switch 或 PoE Injector 供電給 EAP。

### 1.2 初次登入

1. 將電腦接入同一網段
2. 開啟瀏覽器，訪問：`https://192.168.0.239`
   - 若找不到，掃描網段：`nmap -p 8043 192.168.0.0/24`
3. 忽略 SSL 憑證警告（自簽憑證）
4. 初次設定會跳出 Setup Wizard

> **預設 IP：** `192.168.0.239`
> **預設帳密：** admin / admin（首次登入強制修改）

### 1.3 設定管理員密碼

```
Setup Wizard → Admin Password
- 設定強密碼（至少 12 字元，含大小寫+數字+符號）
- 記錄在安全的密碼管理器中
```

### 1.4 更新 Firmware

```
設定 → 系統 → Firmware Upgrade
1. 勾選 "Online Upgrade"
2. 點選 "Check for Updates"
3. 若有更新 → Upgrade（升級期間約 3-5 分鐘，請勿斷電）
```

也可手動下載：https://www.tp-link.com/en/support/download/oc200/

---

## Section 2：加入 AP（Adopt EAPs）

### 2.1 EAP225（室內型）

**規格參考：**
- AC1200 雙頻 Wi-Fi 5
- 2.4GHz 300Mbps + 5GHz 867Mbps
- PoE 供電（802.3af）
- 覆蓋半徑約 30m

**加入步驟：**

1. 將 EAP225 接上 PoE Switch（OC200 同網段）
2. OC200 管理介面 → **Site → Devices**
3. 等待 EAP 出現（通常 30 秒內，狀態：Pending）
4. 點選 EAP225 → **Adopt**
5. 等待狀態變為 **Connected**（約 1-2 分鐘）

### 2.2 EAP650-Outdoor（戶外型，IP67 防塵防水）

**規格參考：**
- AX3000 雙頻 Wi-Fi 6
- IP67 防護等級（防水防塵）
- 適用戶外、停車場、走廊
- 覆蓋半徑約 50m

**加入步驟：** 同 EAP225，但需確保：
- 使用防水 RJ45 接頭或安裝 weather proof 外殼
- 戶外接線需做防水處理

### 2.3 確認 AP 狀態

```
Site → Devices
AP 狀態欄應顯示：
✅ Connected（綠色）— 正常
⏳ Pending        — 等待採用
❌ Disconnected   — 離線，檢查網路
🔄 Updating       — 更新中，請等候
```

**CLI 驗證（SSH 到 OC200）：**
```bash
ssh admin@192.168.0.239
omada show ap list
```

---

## Section 3：建立 Hotspot SSID

### 3.1 新增無線網路

```
Site → Wireless Networks → + Add
```

| 欄位 | 設定值 |
|------|--------|
| SSID | `FreeWiFi_PH` |
| Band | 2.4GHz + 5GHz（雙頻） |
| Security | **Open（無加密）** ⚠️ |
| VLAN | 建議獨立 VLAN（如 VLAN 100） |

> ⚠️ **重要：** Captive Portal 必須使用 Open（不加密）模式。
> 若啟用 WPA2，設備在認證前無法訪問 Portal 頁面。

### 3.2 啟用 Portal

```
無線網路設定 → Portal → 啟用
Portal Type → 選擇 "External Portal"（下一節設定）
```

---

## Section 4：External Portal 設定

```
Site → Hotspot → Portal → + Create
```

| 欄位 | 設定值 |
|------|--------|
| Portal Type | **External** |
| Portal URL | `https://你的域名/portal` |
| Redirect to Landing Page | ❌ 不勾 |
| Authentication Timeout | `3600`（秒，即 1 小時） |
| Portal Customization | 可上傳 Logo（選填） |

**重要設定說明：**

- **Portal URL**：當用戶連上 FreeWiFi_PH，OC200 會將 HTTP 請求重導至此 URL
- OC200 會在 URL 後附加參數：
  ```
  https://portal.example.com/portal?
    client=<MAC_ADDRESS>
    &ap=<AP_MAC>
    &ssid=FreeWiFi_PH
    &redirect=<ORIGINAL_URL>
    &token=<AUTH_TOKEN>
  ```
- **Authentication Timeout 3600**：授權後，用戶可上網 1 小時，到期後自動斷線並再次顯示 Portal

---

## Section 5：Walled Garden

Walled Garden = 允許在認證前訪問的域名（必須加入廣告商 CDN 才能顯示廣告）

```
Site → Hotspot → Walled Garden → + Add
```

**必要域名清單（參考 docs/WALLED-GARDEN.md 完整版）：**

```
# Adcash CDN
*.adcash.com
*.acint.net
*.acsint.net

# Google（分析/字體）
*.googleapis.com
*.gstatic.com
fonts.google.com

# 你的 Portal 域名（避免重導迴圈）
portal.example.com
```

> 💡 詳細清單見：[WALLED-GARDEN.md](WALLED-GARDEN.md)

---

## Section 6：建立 Hotspot Operator 帳號

這是你的 FastAPI Server 用來呼叫 OC200 API 授權用戶的帳號。

```
Hotspot Manager → Operator → + Add
```

| 欄位 | 設定值 |
|------|--------|
| Username | `ph_wifi_operator`（自訂） |
| Password | 強密碼（填入 `.env` 的 `OMADA_PASSWORD`） |
| Role | **Hotspot Manager** |
| Sites | 選擇你的 Site |

> ⚠️ **安全注意：** 不要使用主管理員帳號，使用獨立的 Operator 帳號，最小權限原則。

**填入 `.env`：**
```env
OMADA_OPERATOR=ph_wifi_operator
OMADA_PASSWORD=你設定的密碼
```

---

## Section 7：取得 Controller ID

Controller ID 是呼叫 OC200 REST API 的必要參數。

### 方法一：從 URL 取得（最簡單）

登入 OC200 後，觀察瀏覽器網址列：
```
https://192.168.0.239:8043/1f2e3d4c5b6a.../portal/hotspot
                           ↑
                    這串就是 Controller ID
```

### 方法二：API 呼叫取得

```bash
# 1. 登入取得 Token
curl -k -X POST "https://192.168.0.239:8043/api/v2/hotspot/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"ph_wifi_operator","password":"你的密碼"}'

# Response 會含有 token

# 2. 查詢 Controller Info
curl -k -X GET "https://192.168.0.239:8043/api/v2/info" \
  -H "Authorization: Bearer <token>"
```

**填入 `.env`：**
```env
OMADA_CONTROLLER_ID=1f2e3d4c5b6a...
```

---

## Section 8：測試

### 8.1 手機連線測試

1. 手機關閉行動數據
2. 連接 `FreeWiFi_PH`
3. 等待 1-3 秒，系統應自動彈出 Portal 頁面
   - 若沒有自動彈出：開啟瀏覽器訪問 `http://captive.apple.com`（iOS）或 `http://connectivitycheck.gstatic.com`（Android）
4. 觀看廣告（30 秒倒數）
5. 確認「上網」按鈕出現並可點擊
6. 確認可以正常訪問網站

### 8.2 伺服器端驗證

```bash
# 查看 API logs
docker compose -f deploy/docker-compose.yml logs -f app

# 確認 grant-access 呼叫成功（HTTP 200）
# 確認 Omada API 回應正常
```

### 8.3 常見問題排查

| 問題 | 原因 | 解決 |
|------|------|------|
| Portal 不跳出 | SSID 安全性設定錯誤 | 改為 Open |
| Portal 跳出但廣告不顯示 | Walled Garden 未設定 | 加入 Adcash 域名 |
| 看完廣告仍不能上網 | API 呼叫失敗 | 查看 app logs |
| Operator 登入失敗 | 帳號權限不足 | 確認 Role = Hotspot Manager |
| SSL 錯誤 | Portal URL 用 HTTPS 但 OC200 不信任 | 確認 SSL 憑證有效 |

---

> 📖 需要更多協助？查看 TP-Link 官方文件：
> https://www.tp-link.com/en/omada-sdn/
