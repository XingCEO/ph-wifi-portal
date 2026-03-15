# Adcash 整合指南 — PH WiFi Ad System

> 菲律賓市場廣告變現：Adcash Publisher 完整設定

---

## 一、Adcash 帳號申請

### 1.1 申請步驟

1. 前往 [https://adcash.com](https://adcash.com) → 點「Sign Up」
2. 選擇 **Publisher** 帳號（不是 Advertiser）
3. 填寫資料：
   - Email（用獨立帳號，遵守超星男孩規則）
   - Website URL：填入你的 portal 域名，例如 `https://portal.yourdomain.com`
   - Website category：選 **Technology & Internet**
   - Monthly traffic：誠實填寫預估值

4. 等待審核（通常 24-48 小時）
5. 審核通過後收到 Publisher ID

### 1.2 審核技巧

- 確保 portal 頁面已上線（審核時他們會訪問）
- 頁面要有實際內容（不能是空白）
- 不要一開始就說是「WiFi captive portal」— 說是「internet access portal」

---

## 二、Publisher 設定

### 2.1 建立廣告區塊（Ad Zone）

登入 Adcash Dashboard → **My Sites** → **Add New Zone**

**推薦廣告格式（菲律賓市場）：**

| 格式 | CPM 估算 (PH) | 推薦度 | 適用場景 |
|------|-------------|--------|---------|
| **Interstitial** | $0.5 - $1.5 | ⭐⭐⭐⭐⭐ | Captive Portal 主廣告 |
| **Pop-under** | $0.3 - $0.8 | ⭐⭐⭐⭐ | 點擊後觸發 |
| **In-Page Push** | $0.2 - $0.5 | ⭐⭐⭐ | 補充收入 |
| Banner 300x250 | $0.1 - $0.3 | ⭐⭐ | 頁面邊欄 |

**選擇 Interstitial（全螢幕廣告）原因：**
- CPM 最高
- 和「等待看廣告」流程完全吻合
- 用戶必須看完才能關閉，完成率高

### 2.2 Zone 設定參數

```
Zone Type: Interstitial
Zone Name: PH-WiFi-Portal-[城市名]
Category: General
Traffic type: Mobile Web（重要！菲律賓 99% 手機用戶）
```

建立後會得到：
- **Zone ID**（例如：`1234567`）
- **Script Code**（嵌入用）

---

## 三、嵌入 Captive Portal

### 3.1 環境變數設定

在 `.env` 檔案設定：

```bash
ADCASH_ZONE_ID=1234567    # 你的 Zone ID
```

### 3.2 Interstitial 廣告嵌入方式

Adcash Interstitial 有兩種觸發方式：

**方式 A：自動觸發（頁面載入時）**

```html
<!-- 放在 portal.html 的 </body> 前 -->
<script type="text/javascript">
  (function(d,z,s){s.src='https://'+d+'/401/'+z;
  try{(document.body||document.documentElement).appendChild(s)}catch(e){}})
  ('gonsenmade.com', YOUR_ZONE_ID, document.createElement('script'));
</script>
```

**方式 B：用戶點擊觸發（更好的用戶體驗）**

```javascript
// 在 portal.html 的 loadAd() 函數中
function loadAd() {
  const adZone = CONFIG.adcashZone;
  if (!adZone) { startTimer(); return; }
  
  // Adcash Interstitial script
  const s = document.createElement('script');
  s.src = `https://gonsenmade.com/401/${adZone}`;
  s.async = true;
  s.onload = () => {
    console.log('Adcash loaded');
  };
  s.onerror = () => {
    // Fallback to placeholder
    document.getElementById('ad-placeholder').textContent = 
      '📱 Thank you for supporting free WiFi!';
  };
  document.head.appendChild(s);
  
  // Always start timer (ad may block briefly)
  setTimeout(startTimer, 1000);
}
```

### 3.3 Pop-under 額外收入

在主廣告之外，可加 pop-under 增加收入：

```html
<!-- 放在 portal.html 任意位置 -->
<script type="text/javascript">
  (function(d,z,s){s.src='https://'+d+'/400/'+z;
  try{(document.body||document.documentElement).appendChild(s)}catch(e){}})
  ('gonsenmade.com', YOUR_POPUNDER_ZONE_ID, document.createElement('script'));
</script>
```

**注意：** Pop-under 在部分瀏覽器會被封鎖，不要依賴它為主要收入。

---

## 四、最大化 CPM 策略

### 4.1 廣告格式選擇

```
Captive Portal 最佳組合：
1. Interstitial（主）→ 全螢幕，30秒倒數期間展示
2. In-Page Push（次）→ 在 portal 頁面底部
3. Pop-under（補）→ 用戶點擊任意區域觸發
```

### 4.2 菲律賓市場 CPM 優化

| 策略 | 效果 |
|------|------|
| 設定 Mobile Traffic only | CPM +20-30% |
| 選擇 Premium Zone（付費）| CPM +15% |
| 投放時間：7AM-10PM PHT | 避免低 CPM 夜間流量 |
| 避免頻繁重載廣告 | 避免帳號被標記 |

### 4.3 直接廣告主（更高收入）

達到一定規模後，直接找本地廣告主：

**目標廣告主：**
- GCash / Maya（電子錢包）— CPM 可達 $2-5
- Smart / Globe（電信）
- Jollibee / McDonald's（快餐）
- 本地購物 app（Shopee/Lazada PH）

**報價參考：**
- CPM $2-3（比 Adcash 高 3-5 倍）
- 保底月費 + CPM 計費

---

## 五、防止帳號被封

### 5.1 Adcash 規定

⚠️ **禁止行為（會被封號）：**
- 人工點擊廣告（click fraud）
- 自動刷廣告曝光（impression fraud）
- 在限制地區投放（確認 PH 在允許名單）
- 同一 IP 過多曝光

✅ **我們的防護機制：**
- MAC 地址 1小時冷卻期（已實作）
- 每個 impression_id 只用一次（已實作）
- Redis rate limiting（已實作）

### 5.2 合規設定

在 Adcash Dashboard → Site Settings：
- 勾選 **I have a captive portal / WiFi hotspot** （如果有這個選項）
- Traffic type 設為 **Mobile**
- Country targeting：Philippines

---

## 六、收益追蹤和提款

### 6.1 Adcash Dashboard 追蹤

登入 → **Reports** → 選擇日期區間

查看：
- Impressions（曝光數）
- Revenue（收入 USD）
- eCPM（有效 CPM）
- Fill Rate（廣告填充率）

### 6.2 提款設定

**最低提款金額：** $25 USD

**支援方式：**
- PayPal（手續費約 2%）
- Bank Wire（$20 手續費）
- Bitcoin/USDT（推薦，手續費低）
- WebMoney

**建議：** 選 USDT（Tether），手續費最低，到帳快。

### 6.3 收入預測模型

```
收入計算公式：
Revenue = (Impressions / 1000) × eCPM

菲律賓 Adcash Interstitial eCPM 估算：
  低估：$0.30
  中估：$0.60
  高估：$1.20（優質位置）

範例：
  10個熱點 × 100人/天 × 30天 = 30,000 impressions/月
  Revenue = (30,000 / 1000) × $0.60 = $18 USD/月

  50個熱點：$90 USD/月
  100個熱點：$180 USD/月
```

---

## 七、備選廣告網路

如果 Adcash 審核失敗或 CPM 太低：

| 網路 | 門檻 | PH CPM | 備注 |
|------|------|--------|------|
| **PropellerAds** | 低 | $0.4-0.8 | 接受 captive portal |
| **HilltopAds** | 低 | $0.3-0.7 | 對流量要求低 |
| **TrafficStars** | 中 | $0.5-1.0 | 需審核 |
| **ExoClick** | 中 | $0.3-0.6 | 需有一定流量 |

**推薦：** 先用 PropellerAds 作為 Fallback，Adcash 作為 Primary。

```javascript
// portal.html 中的 fallback 邏輯
function loadAd() {
  // 嘗試載入 Adcash
  loadAdcash(CONFIG.adcashZone)
    .catch(() => {
      // Adcash 失敗 → 試 PropellerAds
      return loadPropellerAds(CONFIG.propellerZone);
    })
    .catch(() => {
      // 全部失敗 → 顯示本地 banner
      showFallbackBanner();
    })
    .finally(() => {
      startTimer();  // 永遠開始倒數
    });
}
```
