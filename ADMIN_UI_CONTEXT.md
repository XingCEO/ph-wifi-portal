# Admin UI 修改 Context

## 任務
替換 `server/routers/admin.py` 中的 `DASHBOARD_HTML` 字串為完整專業後台。

## 唯一要修改的位置
- 檔案：`server/routers/admin.py`
- 只替換 `DASHBOARD_HTML = """..."""` 這一段
- 不動其他任何 Python 程式碼

## 可用的 API（全部需要 Basic Auth header）
```
Authorization: Basic eGluZ2Nlbzp4aW5nd2lmaTIwMjY=
（即 xingceo:xingwifi2026 的 base64）
```

- `GET /admin/api/stats` → 整體統計
  回傳：today_visits, today_ad_views, total_visits, total_ad_views, total_revenue_usd, hotspots[], database_status, redis_status
- `GET /admin/api/hotspots` → 熱點列表
  回傳：[{id, name, location, ap_mac, site_name, is_active, today_visits, today_ad_views}]
- `POST /admin/api/hotspots` → 新增熱點
  Body: {name, location, ap_mac, site_name, latitude?, longitude?}
- `GET /admin/api/revenue?month=YYYY-MM` → 收入
  回傳：adcash_revenue_usd, direct_revenue_php, total_ad_views, breakdown_by_hotspot[]
- `GET /admin/api/live` → 即時用戶
  回傳：total_active_users, hotspots[], omada_clients
- `GET /admin/api/visits?limit=50&offset=0` → 用戶記錄
  回傳：total, items[{id, client_mac, hotspot_name, ip_address, user_agent, visited_at}]
- `GET /admin/api/security` → 資安概覽
  回傳：today_requests, last_hour_requests, suspicious_macs[], rate_limit_active
- `GET /health` → 系統健康（不需要 Auth）
  回傳：status, version, environment, database, redis

## 設計規格
- 強制 light mode：`<meta name="color-scheme" content="light">`
- 主色：#6366f1（Indigo）
- 成功：#10b981、警告：#f59e0b、危險：#ef4444
- Chart.js 4.x from CDN
- 左側固定 sidebar（240px）

## 必須有的分頁
1. Dashboard（KPI + 圖表 + 熱點狀態 + 系統健康）
2. 熱點管理（列表 + 搜尋 + 新增 + 狀態）
3. 收入分析（月份選擇 + KPI + 表格 + Donut圖）
4. 即時監控（大字體在線數 + 熱點表格）
5. 用戶記錄（visits 表格，分頁）
6. 資安中心（異常 MAC、今日請求量、系統資訊）

## Python 字串注意事項
- HTML 用 `"""..."""` 包
- HTML 結尾 `"""` 後必須有**兩個空行**再接 Python 程式碼
- `from __future__ import annotations` 只能在**檔案最開頭**，不要在 HTML 後面重複
- HTML 中如有反斜線，使用 `\\` 轉義

## 完成後
```bash
cd ~/life/projects/ph-wifi-system
python3 -c "import ast; ast.parse(open('server/routers/admin.py').read()); print('OK')"
git add server/routers/admin.py
git commit -m "feat: complete admin dashboard UI"
git push origin main
```
