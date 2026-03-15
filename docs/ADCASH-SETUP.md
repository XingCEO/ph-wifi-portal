# Adcash 廣告整合指南

> 讓 PH WiFi Portal 每次用戶連網前，看一段廣告，轉換為收入。

---

## 1. 申請 Publisher 帳號

**網址：** https://adcash.com/publishers/

**申請步驟：**
1. 點選 **Sign Up as Publisher**
2. 填寫資料：
   - Email：使用**獨立帳號**（非個人主帳號）
   - Website URL：填入你的 Portal 域名，如 `https://portal.example.com`
   - Website Category：選 **Entertainment** 或 **Technology**
   - Monthly Traffic：誠實填寫（初期可填 1,000-10,000 UV/month）
3. 同意服務條款
4. 確認 Email

> ⚠️ **重要：** Adcash 需要審核你的網站。確保 Portal 頁面能正常訪問且有實際內容，不要是空白頁。

---

## 2. 選擇廣告格式

建議並用兩種格式以最大化收入：

### 2.1 Interstitial（全屏插播廣告）⭐⭐⭐ 首選

- **形式：** 全屏廣告，用戶必須等待 5-30 秒才能關閉
- **CPM：** $1.5 - $8（菲律賓市場）
- **適合場景：** 連網前強制觀看，最符合 WiFi Portal 使用情境
- **設定要點：** 倒數 30 秒後才出現關閉按鈕

### 2.2 In-Page Push（頁內推播廣告）⭐⭐ 輔助

- **形式：** 頁面右下角浮現通知樣式廣告
- **CPM：** $0.5 - $2（菲律賓市場）
- **適合場景：** 搭配 Interstitial，增加曝光次數
- **特點：** 不需要 Push Permission，無侵入感

---

## 3. 建立 Ad Zone 並取得 Zone Key

### 3.1 建立 Interstitial Zone

```
Publisher Dashboard → Ad Zones → + Create New Zone
Zone Type: Interstitial
Name: PH-WiFi-Portal-Interstitial
Website: 你的 Portal 域名
```

建立後取得 **Zone Key**（一串數字，如 `1234567890`）

### 3.2 建立 In-Page Push Zone（可選）

```
Ad Zones → + Create New Zone
Zone Type: In-Page Push
Name: PH-WiFi-Portal-Push
```

### 3.3 取得廣告代碼

每個 Zone 建立後，複製 JavaScript 代碼：
```html
<!-- Adcash Interstitial -->
<script type="text/javascript">
    var zone_id = 1234567890;  // ← 這就是 Zone Key
    var aclib_params = { zoneId: zone_id };
</script>
<script src="https://cdn.acint.net/aci.js" async></script>
```

---

## 4. 填入設定

```bash
# 編輯 server/.env
ADCASH_ZONE_KEY=1234567890
```

Portal 前端會自動讀取此設定並載入廣告。

---

## 5. Walled Garden — 加入 Adcash CDN

在 OC200 Walled Garden 加入以下域名，讓未認證用戶也能載入廣告：

```
cdn.acint.net
static.adcash.com
syndication.adcash.com
prebid.adcash.com
rtb.adcash.com
*.acint.net
*.adcash.com
```

> 若廣告不顯示，先用 DevTools Network 面板確認哪個請求被封鎖，再加入對應域名。

---

## 6. 審核時間

| 階段 | 時間 |
|------|------|
| Email 驗證 | 即時 |
| 帳號審核 | 24-48 小時 |
| 首個廣告開始投放 | 審核後 2-4 小時 |
| 收益開始計算 | 首個廣告展示後 |

**審核失敗常見原因：**
- 網站無法訪問（SSL 問題、域名未解析）
- 內容違規（賭博、成人、盜版）
- 流量不足
- 使用 VPN 的 IP 申請

---

## 7. 收益追蹤

### 7.1 Dashboard 主要指標

```
Publisher Dashboard → Statistics
```

| 指標 | 說明 |
|------|------|
| Impressions | 廣告展示次數 |
| Clicks | 點擊次數 |
| CTR | 點擊率（目標 > 0.5%）|
| CPM | 每千次展示收益（菲律賓 $1-5） |
| Revenue | 總收益（USD） |

### 7.2 實際收益估算

菲律賓市場 Interstitial CPM 約 $2-4：

| 日連線人次 | 月展示 | 月收益估算 |
|-----------|--------|-----------|
| 50 人     | 1,500  | $3 - $6   |
| 200 人    | 6,000  | $12 - $24 |
| 500 人    | 15,000 | $30 - $60 |
| 1,000 人  | 30,000 | $60 - $120|

> 💡 高流量地點（商場、夜市、公車站）可達 500-2,000 人/天

### 7.3 API 整合（自動對帳）

```python
# Adcash Publisher API（選填）
GET https://api.adcash.com/publisher/v1/statistics
  ?start_date=2024-01-01
  &end_date=2024-01-31
  &zone_id=1234567890
Authorization: Bearer <API_KEY>
```

---

## 8. 最低提款

| 方式 | 最低金額 | 手續費 | 時間 |
|------|---------|--------|------|
| PayPal | $25 | 0% | 3-5 工作日 |
| Bank Transfer | $100 | 視銀行 | 5-7 工作日 |
| Payoneer | $25 | 2% | 2-3 工作日 |
| USDT (TRC20) | $25 | 網路費 | 即時 |

> 推薦：**Payoneer**（支援亞洲市場，再轉入菲律賓當地帳戶）

**付款週期：** NET30（每月底結算，下個月底付款）

---

## 常見問題

**Q: 廣告不顯示怎麼辦？**
A: 1) 確認 Walled Garden 設定正確 2) 確認 Zone Key 正確 3) 確認帳號已通過審核 4) 試用不同設備（排除快取問題）

**Q: CPM 很低怎麼辦？**
A: 1) 確認流量來自菲律賓（地理定向） 2) 優化廣告位置 3) 提高展示率（確保廣告完整載入） 4) 考慮接洽其他廣告網路對比

**Q: 帳號被暫停？**
A: 常見原因：流量異常（VPN/Bot）、點擊欺詐、違規內容。聯繫 support@adcash.com

---

> 📊 Adcash Publisher Support: support@adcash.com
> 📖 API Docs: https://adcash.com/publishers/api/
