# 測試指南 — PH WiFi Portal

## 本地測試（不需要 OC200）

### 1. 啟動開發環境

```bash
cd ~/life/projects/ph-wifi-system
docker-compose -f deploy/docker-compose.yml up -d
cd server
pip install -r requirements.txt
cp .env.example .env
# 編輯 .env，填入 OMADA_HOST=mock（測試模式）
uvicorn main:app --reload
```

### 2. 模擬 OC200 重定向

在瀏覽器直接開：
```
http://localhost:8000/portal?clientMac=aa:bb:cc:dd:ee:ff&apMac=11:22:33:44:55:66&ssidName=FreeWiFi_PH&radioId=0&site=test_site&redirectUrl=https://google.com
```

應該看到廣告頁面。

### 3. 測試授權流程

```bash
# 取得 session_id（從頁面 HTML 或 API）
curl -X POST http://localhost:8000/api/grant-access \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR_SESSION_ID"}'
```

預期回應：
```json
{"status": "granted", "redirect": "https://google.com"}
```

### 4. 測試管理 Dashboard

```
http://localhost:8000/admin/
```

### 5. 真機測試（需要 OC200）

1. 把 OC200 的 External Portal 設為 `http://你的電腦IP:8000/portal`
2. 手機連 FreeWiFi_PH SSID
3. 應該自動跳出廣告頁面
4. 看完廣告，點擊「Connect Now」
5. 確認可以上網

## 常見問題

### Portal 沒有跳出來
- 確認 OC200 External Portal URL 正確
- 確認 Walled Garden 有加入你的伺服器 IP

### 授權後還是不能上網
- 確認 OMADA_OPERATOR 帳號有 Hotspot 管理權限
- 確認 Controller ID 正確
- 查看 server log：`docker-compose logs app`

### Adcash 廣告沒顯示
- 確認 Zone Key 正確
- 確認 Walled Garden 有允許 adcash.com 域名
- 某些廣告 Block 會攔截，測試用不裝 AdBlock 的瀏覽器
