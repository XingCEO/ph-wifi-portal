# 收入優化指南

> 從 0 到最大化的 WiFi Portal 廣告收益策略

---

## 1. 廣告時間 vs UX vs 收入 Tradeoff

### 最佳點：30 秒

```
廣告時間   收入指數   跳出率   用戶滿意度
──────────────────────────────────────
10 秒       ★★☆      低(8%)    ★★★★★
20 秒       ★★★      低(12%)   ★★★★☆
30 秒      ★★★★★   中(18%)   ★★★☆☆  ← 最佳平衡
45 秒       ★★★★     高(35%)   ★★☆☆☆
60 秒       ★★★☆     高(55%)   ★☆☆☆☆
```

**結論：**
- **30 秒** 是收益與留存率的黃金平衡點
- 菲律賓用戶對 30 秒免費上網交換接受度高
- 超過 45 秒跳出率急升（選擇不連網或用行動數據）

**實作建議：**
```javascript
// 前端倒數邏輯
const AD_DURATION = 30; // 秒
let countdown = AD_DURATION;
const timer = setInterval(() => {
    countdown--;
    updateDisplay(countdown);
    if (countdown <= 0) {
        clearInterval(timer);
        showConnectButton(); // 才顯示連網按鈕
    }
}, 1000);
```

---

## 2. Adcash 廣告格式 CPM 比較

### 菲律賓市場實測數據

| 格式 | CPM 範圍 | 建議 | 說明 |
|------|---------|------|------|
| Interstitial | $2.0 - $6.0 | ⭐⭐⭐ **主力** | 全屏，強制觀看，最高收益 |
| In-Page Push | $0.8 - $2.0 | ⭐⭐ 輔助 | 非干擾性，搭配使用 |
| Banner 300x250 | $0.3 - $0.8 | ⭐ 補充 | 可放在倒數頁面旁 |
| Native | $1.0 - $3.0 | ⭐⭐ 可測試 | 外觀像內容，CTR 較高 |

### 組合策略（推薦）

```
連網流程：
[用戶連 WiFi] → [Interstitial 廣告 30秒] → [點擊連網] → [In-Page Push 跟隨]

每次連網收益（估算）：
- Interstitial：$0.002 - $0.006（CPM 換算）
- In-Page Push：$0.001 - $0.002
- 合計：~$0.003 - $0.008 per session
```

---

## 3. 高流量時段（菲律賓）

### 3.1 日內時段分析

```
時間         流量指數   廣告 CPM   策略
────────────────────────────────────────
06:00-07:00   ★★☆      中        上班通勤前
07:00-09:00  ★★★★★    高        ← 早高峰，廣告商搶量
09:00-12:00   ★★★☆     中高       工作中休息
12:00-14:00  ★★★★★    高        ← 午休，購物類廣告多
14:00-17:00   ★★★☆     中        下午低谷
17:00-18:00   ★★★★     中高       下班前
18:00-22:00  ★★★★★    高        ← 黃金晚間
22:00-00:00   ★★★☆     中        夜間休閒
00:00-06:00   ★☆☆      低        深夜
```

### 3.2 週內分析

| 星期 | 流量 | CPM | 說明 |
|------|------|-----|------|
| 週一 | ★★★ | 中 | 工作日 |
| 週二 ~ 週四 | ★★★★ | 中高 | 廣告主週中投放旺季 |
| 週五 | ★★★★ | 高 | 週末前活躍 |
| 週六 | ★★★★★ | 最高 | 外出、購物、餐廳 |
| 週日 | ★★★★ | 高 | 家庭活動 |

### 3.3 月份週期

- **月初（1-5 日）**：廣告主投放高峰，CPM 提升 20-40%
- **月底（25-31 日）**：廣告主預算燃盡，CPM 下降
- **節慶期間**（聖誕節、情人節、復活節）：特別高

---

## 4. 如何接觸直接廣告主

繞過廣告網路，利潤更高（直接廣告主 CPM 可達 $10-30）

### 4.1 目標客戶

適合直接接觸的廣告主：
- **本地餐廳/咖啡廳**：WiFi 覆蓋範圍內的客戶
- **超市/零售商**：賣場附近 WiFi
- **電信商**（Globe, Smart, DITO）：行動數據促銷
- **速食連鎖**（Jollibee, McDonald's 周邊）
- **銀行/金融**（GCash, Maya 推廣）
- **房地產商**

### 4.2 接洽方式

**準備資料包：**
```
📊 媒體資料包內容：
1. 月流量報告（截圖）
2. 用戶地理分布（菲律賓 XX 省 XX 市）
3. 廣告位截圖
4. 定價方案
5. 聯繫方式
```

**開場白模板（英文/菲律賓文）：**
```
Hi [Brand Name],

I operate a free WiFi network serving [XXX] daily users in [Location], Philippines.

Every user sees a full-screen ad before connecting. This is a premium, 
captive audience — they're waiting for WiFi access and actively paying attention.

Monthly stats: ~[X,000] impressions, [Location] geo-targeted.

Interested in a sponsored month? Rates from ₱5,000/month.

[Your name / contact]
```

### 4.3 定價參考

| 方案 | 費用 | 曝光量 |
|------|------|--------|
| 試用週 | ₱500 | ~1,000 次展示 |
| 月包 Basic | ₱3,000 | ~6,000 次 |
| 月包 Premium | ₱8,000 | ~15,000 次 |
| 獨家包月 | ₱15,000 | 全部展示 |

---

## 5. 定價策略（包月版位費）

### 5.1 市場定位

```
定位：精準地理定向 + 強制曝光
競爭優勢：捕獲式廣告（Captive Audience），注意力 100%
```

### 5.2 分級定價

**Starter（起步期）**
- 目標：建立第一批廣告主，累積口碑
- 策略：低價甚至免費換 testimonial
- 價格：₱1,000-2,000/月

**Growth（成長期，日均 200+ 連線）**
- 正式報價：₱5,000-10,000/月（依位置和流量）
- 可提供 A/B 測試、週報告

**Scale（規模化，多地點）**
- 套裝銷售：₱20,000-50,000/月（全網路覆蓋）
- 獨家區域代理

### 5.3 定價錨定技巧

```
提供 3 個方案，讓客戶選中間那個：

┌─────────────────────────────────────────┐
│ Bronze  ₱3,000/月  ~ 6,000 次展示       │
│ Silver  ₱6,000/月  ~12,000 次展示 ✓推薦 │
│ Gold    ₱12,000/月  24,000 次展示 + 報告 │
└─────────────────────────────────────────┘
```

---

## 6. 付費選項：₱5/30 分鐘

為不想看廣告的用戶提供付費跳過選項。

### 6.1 商業邏輯

```
每次連線：
- 免費用戶：看廣告 30 秒 → 上網 1 小時，你收 $0.004 廣告費
- 付費用戶：付 ₱5 → 上網 30 分鐘，你收 ~$0.09

付費選項收益是廣告的 22 倍！即使只有 5% 的用戶選擇付費
整體收益也能大幅提升。
```

### 6.2 支付整合方案

**推薦：GCash QR Code（菲律賓最普及）**

```python
# server/routes/payment.py
import gcash  # 使用 GCash for Business API

@router.post("/api/create-payment")
async def create_payment(client_mac: str, duration: int = 1800):
    """
    duration: 秒（1800 = 30 分鐘）
    """
    payment = await gcash.create_qr(
        amount=5.00,  # ₱5
        currency="PHP",
        description=f"WiFi 30分鐘 | {client_mac[:8]}",
        callback_url=f"https://yourdomain.com/api/payment-callback"
    )
    return {"qr_url": payment.qr_url, "payment_id": payment.id}

@router.post("/api/payment-callback")
async def payment_callback(data: PaymentCallbackData):
    if data.status == "PAID":
        await grant_access(data.metadata["client_mac"], duration=1800)
```

**其他支付選項：**
- Maya（原 PayMaya）
- 7-Eleven 支付
- 現金投幣機（進階，需硬體）

### 6.3 UI 設計

```
┌─────────────────────────────────┐
│         FreeWiFi_PH             │
│                                 │
│  [廣告中... 28秒後可免費上網]   │
│                                 │
│         — 或者 —                │
│                                 │
│  💳 ₱5 直接上網 30 分鐘         │
│      [GCash QR 碼支付]          │
│                                 │
└─────────────────────────────────┘
```

---

## 7. 快速收益提升清單

| 優先級 | 行動 | 預期影響 |
|--------|------|---------|
| 🔴 高 | 確保廣告完整載入（Walled Garden 正確設定） | +40-60% CPM |
| 🔴 高 | 廣告時間設 30 秒（非 5 秒） | +3-4x 收益 |
| 🟡 中 | 加入 In-Page Push 補充 | +15-25% |
| 🟡 中 | 接觸 1 個本地廣告主 | +₱3,000-10,000/月 |
| 🟢 低 | 新增付費跳過選項 | 潛力 +200% |
| 🟢 低 | 多地點部署（同一套系統） | 線性增長 |
