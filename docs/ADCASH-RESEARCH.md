# Adcash 調查報告

> 研究日期：2026-03-15（夜間優化任務自動生成）

---

## 1. Adcash 基本介紹

Adcash 是一個全球性廣告平台（總部愛沙尼亞 Tallinn），聲稱每日覆蓋數億獨立訪客，旗下超過 100,000 個網站與 App。主打「無最低流量門檻」、100% fill rate、高 eCPM。

官網：https://adcash.com
Publisher 平台：https://adcash.myadcash.com

---

## 2. Publisher 申請要求

| 條件 | 詳情 |
|------|------|
| 最低流量 | **無**（No minimum traffic requirement） |
| 語言限制 | 無特定語言要求 |
| 內容限制 | 禁止暴力、仇恨言論、騷擾等，Ad quality 標準嚴格 |
| 申請方式 | 在 adcash.myadcash.com 免費註冊 Publisher 帳號 |
| 審核機制 | 如果 Adcash 認為廣告主不匹配目標受眾，可能拒絕申請 |

✅ **結論**：菲律賓 WiFi portal 場景（大量本地用戶）有機會通過審核，但需確保流量質量。

---

## 3. CPM 費率（菲律賓相關）

| 廣告格式 | 預估 CPM 範圍 | 備註 |
|----------|-------------|------|
| Pop-Under | $0.50–$2.00 | 東南亞地區偏低 |
| Interstitial | $1.00–$3.00 | 全屏廣告，適合 WiFi Portal |
| In-Page Push | $0.30–$1.00 | 低干擾，高點擊 |
| Native Ads | $0.50–$2.00 | 融入頁面 |
| Display/Banner | $0.20–$0.80 | 最低 CPM |
| Video Ads（其他網絡） | 最高 $25 CPM | Adcash video 較少使用 |

> 注意：東南亞/菲律賓地區 CPM 普遍偏低，約 $0.50–$2.00 USD 之間。高轉換流量可以提升 eCPM。
> 文獻資料顯示 Adcash CPM 起步約 $1/CPM，整體「高於平均」但不及 AdSense 或 Mediavine。

---

## 4. 廣告格式（與 WiFi Portal 相容性分析）

| 格式 | WiFi Portal 適合度 | 原因 |
|------|------------------|------|
| **Interstitial** | ⭐⭐⭐⭐⭐ | 全屏觀看，Portal 倒計時期間完美契合 |
| **Pop-Under** | ⭐⭐⭐ | 彈窗需要用戶確認，但可作為次要收入 |
| **In-Page Push** | ⭐⭐⭐⭐ | 低打擾，倒計時後顯示 |
| **Native Ads** | ⭐⭐⭐ | 在 thanks 頁面效果好 |
| **Banner** | ⭐⭐⭐ | 低 CPM，但填充率高 |
| **Autotag**（自動置入） | ⭐⭐⭐⭐ | 適合靜態頁面，Publisher 專屬 |

---

## 5. 付款條件

| 項目 | 詳情 |
|------|------|
| 最低提款 | $25 USD |
| 付款週期 | Net-30（月結） |
| 付款方式 | PayPal、Skrill、銀行轉帳、WebMoney、信用卡、加密貨幣（USDT/BTC/ETH） |
| 幣種 | USD |

---

## 6. Adcash 特色優勢

- **Anti-AdBlock 技術**：自動繞過廣告封鎖器（對 WiFi 用戶效果顯著，因為用戶無法自訂路由器 AdBlock）
- **CPA Target 模式**：依轉換計費，對性能型廣告主吸引力高
- **全球覆蓋**：70+ 主要國家，包含菲律賓
- **自助平台**：無需客戶經理，自助管理廣告位

---

## 7. 與現有系統整合可行性

現有系統已有 `ad_network == "adcash"` 欄位（見 `admin.py` 的 revenue 查詢），代表 **Adcash 整合已在規劃/進行中**。

建議整合路徑：
1. 在 `portal.html` 倒計時頁面嵌入 Adcash Interstitial 廣告
2. 在 `thanks.html` 頁面嵌入 Native/Banner 廣告
3. 使用 Autotag 自動化管理

---

## 8. 風險與注意事項

- 菲律賓地區 CPM 相對低（SEA tier-2 市場）
- 若用戶使用 VPN 可能影響地理定向
- 需遵守菲律賓 DPA（Data Privacy Act）的用戶數據規定
- Captive Portal 環境下廣告 JavaScript 可能受到設備瀏覽器限制

---

## 來源

- Blognife.com - Adcash CPM Rates 2025
- MonetizePros.com - Adcash Review for Publishers
- Mobidea Academy - Adcash Review 2026
- Kochava Media Index - AdCash
- Adcash 官方文件
