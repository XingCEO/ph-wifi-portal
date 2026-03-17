# 測試指南 — AbotKamay WiFi

## 自動化測試

```bash
# 後端測試（121 tests, SQLite in-memory, Redis mocked）
cd server && pytest tests/ -v

# 後端測試 + coverage
cd server && pytest tests/ -v --cov

# 單一檔案
cd server && pytest tests/test_portal.py

# 單一測試
cd server && pytest tests/ -k "test_register_success"

# 前端 Lint
cd web && npm run lint

# 前端 Build（驗證靜態匯出）
cd web && npm run build
```

## 本地測試（不需要 Omada Controller）

### 1. 啟動開發環境

```bash
cd server
cp .env.example .env
# .env 中 OMADA_CONTROLLER_ID 留空 → 自動進入 test mode
uvicorn main:app --reload --port 8000
```

Test mode 下，`/api/grant-access` 會跳過 Omada API 呼叫，但其餘流程（session、防刷、DB 記錄）完全正常。

### 2. 模擬 Omada 重定向

在瀏覽器直接開（模擬 Omada Controller 的重定向）：
```
http://localhost:8000/portal?clientMac=aa:bb:cc:dd:ee:ff&apMac=11:22:33:44:55:66&ssidName=FreeWiFi_PH&radioId=0&site=test_site&redirectUrl=https://google.com
```

應該看到廣告頁面。

### 3. 測試授權流程

```bash
# 取得 session_id（從頁面 HTML 中找 data-session-id 或 hidden input）
curl -X POST http://localhost:8000/api/grant-access \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR_SESSION_ID"}'
```

預期回應：
```json
{"status": "granted", "redirect_url": "https://google.com", "expires_at": "..."}
```

### 4. 測試管理 Dashboard

```
http://localhost:8000/admin/
# 帳號: admin / 密碼: 你在 .env 設的 ADMIN_PASSWORD
```

### 5. 真機測試（需要 Omada Controller + EAP AP）

1. 確認 Omada Controller 的 External Portal URL 設為 `https://你的域名/portal`
2. 手機連上 WiFi SSID
3. 應該自動跳出廣告頁面
4. 看完廣告，點擊「免費上網」
5. 確認可以上網

## 常見問題

### Portal 沒有跳出來
- 確認 Omada Controller External Portal URL 正確
- 確認 Walled Garden 有加入你的伺服器域名
- 確認 EAP AP 已被 Omada Controller adopt

### 授權後還是不能上網
- 確認 OMADA_OPERATOR 帳號有 Hotspot 管理權限
- 確認 OMADA_CONTROLLER_ID 正確
- 查看 server log：`docker compose -f deploy/docker-compose.yml logs app`

### Adcash 廣告沒顯示
- 確認 ADCASH_ZONE_KEY 正確
- 確認 Walled Garden 有允許 adcash.com 相關域名
- 測試用不裝 AdBlock 的瀏覽器

### Rate Limiting 被觸發
- `/api/grant-access` 限制 10/min per IP
- `/api/auth/login` 限制 10/min per IP
- `/api/auth/register` 限制 5/min per IP
- 測試環境中 rate limiting 已自動禁用
