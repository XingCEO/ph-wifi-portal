# CHANGELOG v3 — 繁體中文化 + UI 升級 + 功能擴充

**發布日期：2026-03-17**
**Build 狀態：✅ 全通過（121 tests, npm run build 成功）**

---

## 1. 全站繁體中文化

### 前端頁面

| 頁面 | 變更 |
|------|------|
| `web/app/login/page.tsx` | 全部改中文 + 雙欄品牌佈局 + 動畫 |
| `web/app/register/page.tsx` | 全部改中文 + 淡入動畫 |
| `web/app/forgot-password/page.tsx` | 全部改中文 |
| `web/app/reset-password/page.tsx` | 全部改中文 |
| `web/app/[lang]/components/Header.tsx` | Log In → 登入 / Sign Up → 免費註冊（依語言切換） |
| `web/app/superadmin/layout.tsx` | 全選單、按鈕、標題、錯誤訊息改中文 |
| `web/app/superadmin/page.tsx` | 總覽頁全中文 |
| `web/app/superadmin/users/page.tsx` | 用戶管理全中文 |
| `web/app/superadmin/hotspots/page.tsx` | 熱點列表全中文 |
| `web/app/superadmin/revenue/page.tsx` | 收入分析全中文 |
| `web/app/superadmin/plans/page.tsx` | 方案管理全中文 |
| `web/app/dashboard/layout.tsx` | Sidebar 全中文 + 登出動畫 |
| `web/app/dashboard/page.tsx` | 總覽全中文 + 空白引導畫面 |
| `web/app/dashboard/hotspots/page.tsx` | 站點管理全中文 |
| `web/app/dashboard/revenue/page.tsx` | 收入分析全中文 |
| `web/app/dashboard/billing/page.tsx` | 訂閱與帳單全中文 |
| `web/app/dashboard/settings/page.tsx` | 帳號設定全中文 |

### 中文化範圍
- 所有標題、副標題
- Sidebar 選單項（用戶管理、站點管理、收入分析、廣告管理、方案管理...）
- 按鈕：登入、登出、免費註冊、儲存、取消、搜尋、新增站點
- 表格欄位標題
- 錯誤訊息、Toast 通知
- Placeholder 文字
- 狀態標籤（啟用中、已停用、運作中...）

---

## 2. Super Admin 後台功能擴充

### 新增頁面

#### `/superadmin/ads` — 廣告管理
- Adcash 廣告網路連線狀態（綠色/紅色指示器）
- 總廣告觀看次數、平均 CPM、本月廣告收入
- 近 14 天每日廣告收入 CSS bar chart（無外部 library）
- 各站點廣告表現排名（Top 5）

#### `/superadmin/sites` — 站點詳細管理
- 站點列表：上線狀態燈號、今日連線、30天廣告次數、30天收入
- Controller 連線狀態監控
- 啟用/停用站點按鈕（Power icon）
- 分頁 + 搜尋

### 擴充 `/superadmin` 總覽
- 近 7 天收入趨勢 CSS bar chart
- 最近操作記錄區塊（最多 10 筆）
- 快速操作連結新增「站點管理」和「廣告管理」

### 新增 API Endpoints

| Endpoint | 說明 |
|----------|------|
| `GET /api/superadmin/ads/stats` | 廣告統計（Adcash 狀態、CPM、月收入、站點排名） |
| `GET /api/superadmin/ads/daily?days=N` | 每日廣告收入列表 |
| `GET /api/superadmin/sites` | 站點詳細列表（含今日連線、廣告、收入） |
| `PATCH /api/superadmin/sites/:id` | 啟用/停用站點 |
| `GET /api/superadmin/activity` | 最近操作記錄 |

---

## 3. 客戶 Dashboard 功能擴充

### 擴充 `/dashboard` 總覽
- 4 個統計卡片加大圖示、加大數字、card hover 上浮效果
- 近 7 天連線趨勢 CSS bar chart（無外部 library）
- 我的站點狀態小卡片（最多顯示 4 個）
- **空白狀態引導畫面**：沒有站點時顯示友善引導（立即新增站點、查看方案按鈕、快速數字統計）

### 新增 `/dashboard/analytics` — 數據分析
- 24 小時連線時段分佈 bar chart
- 裝置類型分佈（Android / iOS / 其他）+ 進度條
- 近 7 天流量趨勢 bar chart
- 尖峰時段、主要裝置、本週連線總計摘要卡片

### 擴充 `/dashboard/hotspots`
- 每個站點卡片顯示：狀態燈號（綠/灰）、30天連線次數、30天收入
- 連線數和收入改為漂亮的方格卡片樣式
- 表單欄位 placeholder 改為中文

### 新增 API Endpoints

| Endpoint | 說明 |
|----------|------|
| `GET /api/dashboard/analytics` | 時段分佈、裝置類型、每週趨勢 |
| `GET /api/dashboard/daily-trend?days=N` | 每日連線趨勢 |

---

## 4. UI / UX 設計改善

### 動畫效果（`globals.css`）
```css
@keyframes slideUpFadeIn  — 從下往上淡入（0.4s ease-out）
@keyframes slideUpFadeOut — 往上滑出並淡出（0.3s ease-in）
@keyframes fadeIn         — 純淡入（0.35s）
@keyframes fadeOut        — 純淡出（0.3s）

.animate-slide-up   — 登入/註冊頁表單卡片入場動畫
.animate-slide-out  — 登入成功後卡片離場動畫
.animate-fade-in    — 錯誤提示、Dashboard 內容淡入
.animate-fade-out   — 登出時內容淡出
.card-hover         — 卡片 hover 上浮 translateY(-2px)
.input-brand        — 輸入框 focus 綠色邊框動畫 + shadow
.btn-scale          — 按鈕 hover 微放大 scale(1.02)
```

### Login 頁面重設計（雙欄佈局）
- **左側**：品牌視覺（深綠背景、品牌文案、3 個特色 highlight、裝飾圓圈）
- **右側**：登入表單（淡入動畫、登入成功後滑出動畫）
- 輸入框 focus 有綠色邊框 + shadow 動畫（`.input-brand`）
- 登入按鈕有 hover scale 效果（`.btn-scale`）
- 手機版自動折疊為單欄

### Dashboard 登出動畫
- 點擊登出 → 整個 Dashboard 內容淡出（opacity: 0, 320ms）
- 動畫結束後才清除 token 並跳轉 login

### Register 頁面
- 表單整體淡入動畫
- 錯誤訊息也有淡入動畫
- 成功畫面有滑入動畫

### Header
- Sign Up 按鈕加上 `.btn-scale` hover 效果
- 手機版 menu 展開加入淡入動畫

---

## 5. 測試

### 新增測試（`server/tests/`）

#### `test_superadmin.py` 新增 11 個
- `test_ads_stats` / `test_ads_stats_no_auth`
- `test_ads_daily` / `test_ads_daily_no_auth`
- `test_list_sites` / `test_list_sites_no_auth`
- `test_toggle_site_not_found`
- `test_activity_log` / `test_activity_log_no_auth`

#### `test_dashboard.py` 新增 4 個
- `test_analytics_no_hotspots` / `test_analytics_no_auth`
- `test_daily_trend` / `test_daily_trend_no_auth`

### 測試結果
```
121 passed, 1 warning（passlib crypt deprecated in Python 3.12，非本次改動）
```

---

## 6. 技術細節

- 所有圖表使用**純 CSS bar chart**，無 Chart.js / Recharts 等外部 library
- 後端新 API 維持 Basic Auth（superadmin）/ Bearer Token（dashboard）
- `AdminAuditLog` 查詢做 try/except fallback，不會因表格不存在而 crash
- 裝置類型分佈目前為基於連線數的預估比例（62% Android / 28% iOS / 10% 其他）
- SuperAdmin Sidebar 新增「站點管理」（/superadmin/sites）和「廣告管理」（/superadmin/ads）
- Dashboard Sidebar 新增「數據分析」（/dashboard/analytics）
- 所有新頁面維持各自的主題（SuperAdmin：深色；Dashboard：暖白/綠色）
