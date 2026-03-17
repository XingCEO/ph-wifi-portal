# Walled Garden 設定清單

Omada Controller（軟體版或 OC200 硬體）的 Walled Garden 必須允許以下域名，
用戶在看廣告（未認證）期間才能正常載入頁面和廣告。

## 必須加入的域名

### 你的伺服器
```
*.zeabur.app           (Zeabur 預設域名)
你的自訂域名.com        (如果有綁自訂域名)
```

### Adcash CDN
```
adcash.com
*.adcash.com
topcreativeformat.com
*.topcreativeformat.com
highperformancedisplayformat.com
*.highperformancedisplayformat.com
```

### Android Captive Portal Detection（重要！）
不加這個，Android 手機不會自動彈出 portal 視窗：
```
clients3.google.com
connectivitycheck.gstatic.com
connectivitycheck.android.com
```

### Apple iOS Captive Portal Detection
```
captive.apple.com
www.apple.com
```

## Omada Controller 設定路徑

Omada Controller 管理介面 → Hotspot → Portal → Walled Garden
（軟體版：`https://omada.你的域名`，OC200：`https://OC200_IP:8043`）

每行加一個域名，支援萬用字元 `*`。

## 測試 Walled Garden 是否正確

連上 WiFi 但未認證時，在瀏覽器開：
```
http://adcash.com
```

如果能開，表示 Walled Garden 設定正確。
如果不能開，廣告會顯示空白。
