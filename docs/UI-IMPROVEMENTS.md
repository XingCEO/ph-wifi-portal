# 後台 UI 改善建議

> 分析日期：2026-03-15（夜間優化任務自動生成）
> 分析來源：`server/routers/admin.py`、`frontend/templates/admin/dashboard.html`

---

## 改善點總覽

以下 8 個改善點依優先順序排列（高 → 低）。

---

### 🔴 #1：Dashboard KPI 缺少「今日廣告收入」顯示

**現狀問題**：
- Dashboard 的 KPI 卡片只顯示「今日訪客」、「總連線」、「活躍熱點」、「本月收入」
- **沒有「今日廣告收入（Today's Ad Revenue）」** — 這是最重要的運營指標
- `/api/stats` 已回傳 `total_revenue_usd`，但 Dashboard KPI 只顯示 `monthly_revenue`

**改善建議**：
在 KPI grid 新增一個卡片：
```html
<div class="kpi-card kpi-green">
  <div class="kpi-label">今日廣告收入</div>
  <div class="kpi-value" x-text="stats ? '$' + Number(stats.total_revenue_usd || 0).toFixed(4) : '...'"></div>
</div>
```

---

### 🔴 #2：Basic Auth 安全性不足，需升級為 Token-Based 或 Session Auth

**現狀問題**：
- 使用 HTTP Basic Auth，密碼以 Base64 明文傳輸（非加密）
- 代碼中連 `auth_method` 欄位都自我標注：`"Basic Auth (bcrypt recommended for production)"`
- 每次請求都需要帶上認證頭，無 session 管理

**改善建議**：
1. 改用 JWT Token 或 Session Cookie 機制
2. 加入登入頁面（`/admin/login`），設定 httpOnly Cookie
3. 加入登入嘗試限制（每 IP 最多 5 次，鎖定 15 分鐘）
4. 生產環境強制 HTTPS

---

### 🟡 #3：熱點列表缺少「今日廣告收入」欄位

**現狀問題**：
- 熱點列表（Hotspots tab）顯示：ID、名稱、地點、AP MAC、Site、座標、今日訪問、狀態
- **缺少「今日廣告收入」和「今日廣告觀看次數」** — 運營者最關心的數據
- `api/stats` 已在 `hotspots[]` 中包含這些資料，只是 UI 沒顯示

**改善建議**：
在熱點表格新增兩欄：
- 「今日廣告觀看」（`ad_views_today`）
- 「今日收入」（`revenue_today_usd`）

---

### 🟡 #4：收入分析頁（Revenue Tab）缺少時間維度圖表

**現狀問題**：
- 收入分析只按熱點分解，沒有時間軸趨勢
- `/api/revenue` 只回傳單月總計，沒有每日明細
- Dashboard 有「7天趨勢圖」，但 Revenue tab 缺乏對應圖表

**改善建議**：
1. 在 `/api/revenue` 新增 `daily_breakdown` 陣列，包含每日廣告收入
2. Revenue tab 加入折線圖，顯示當月每日收入趨勢
3. 提供月份選擇器（已有 `month` query param，但 UI 沒有對應控件）

---

### 🟡 #5：安全中心頁面（Security Tab）缺少「可疑 MAC 封鎖」快捷操作

**現狀問題**：
- Security tab 顯示「可疑高頻 MAC」列表（1小時內超過 5 次請求）
- 但**沒有直接從安全頁面封鎖這些 MAC 的按鈕**
- 用戶必須切換到「設備管理」tab 手動封鎖

**改善建議**：
在可疑 MAC 列表每行新增「一鍵封鎖」按鈕，直接呼叫 `POST /admin/api/blocked-devices`：
```javascript
async blockMac(mac) {
  await fetch('/admin/api/blocked-devices', {
    method: 'POST',
    body: JSON.stringify({ mac_address: mac, reason: 'Auto-blocked (suspicious activity)' })
  });
}
```

---

### 🟡 #6：缺少「廣告主到期提醒」警示

**現狀問題**：
- 直接廣告主（Direct Advertisers）有 `starts_at` 欄位，但沒有到期日欄位
- 後台無法提醒管理者「哪位廣告主即將到期需要續約」
- 可能導致廣告主流失和收入中斷

**改善建議**：
1. 在 `DirectAdvertiser` model 新增 `ends_at` 欄位（可選）
2. Dashboard 新增「⚠️ 到期警示」卡片：顯示 7 天內到期的廣告主
3. 廣告主列表顯示合約到期狀態

---

### 🟢 #7：即時監控（Live Tab）缺少「熱點地圖」視覺化

**現狀問題**：
- Live tab 顯示各熱點的即時用戶數，以列表形式呈現
- 沒有地圖視覺化，無法直觀看到哪個地點最熱門
- 所有熱點都有 `latitude`/`longitude` 欄位，但沒有被利用

**改善建議**：
整合輕量地圖（如 Leaflet.js）：
1. 在 Live tab 加入地圖視圖切換
2. 以圓圈大小代表即時用戶數
3. 點擊熱點顯示詳細資訊

```html
<!-- 在 Live tab 加入 -->
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```

---

### 🟢 #8：稽核日誌（Audit Log）缺少搜尋與過濾功能

**現狀問題**：
- `AdminAuditLog` model 已有完整記錄（admin_user、action、target_type、ip_address）
- 後台有稽核日誌 API 端點
- 但 UI 缺少：時間範圍過濾、操作類型過濾、管理員過濾、搜尋框

**改善建議**：
在稽核日誌頁面新增過濾列：
- 日期範圍選擇器
- 操作類型下拉（create_hotspot / update_hotspot / create_advertiser 等）
- 管理員帳號過濾
- IP 位址搜尋

---

## 技術債注意事項

- `_ADMIN_TEMPLATE_CACHE` 在 production 環境下快取 HTML，修改後需重啟服務才生效
- Admin auth 使用 `secrets.compare_digest` 防時序攻擊，這個做對了 ✅
- API 有 audit log 記錄，但沒有 rate limiting on `/admin/api/*`，建議加入

---

## 實作優先順序建議

| 優先 | 改善點 | 預估時間 |
|------|--------|---------|
| P0 | #1 今日廣告收入 KPI | 30 分鐘 |
| P0 | #2 認證機制升級 | 2–4 小時 |
| P1 | #3 熱點表格新增收入欄 | 1 小時 |
| P1 | #5 安全頁面快捷封鎖 | 1 小時 |
| P2 | #4 收入趨勢圖 | 3 小時 |
| P2 | #6 廣告主到期提醒 | 2 小時 |
| P3 | #7 熱點地圖 | 4 小時 |
| P3 | #8 稽核日誌搜尋 | 2 小時 |
