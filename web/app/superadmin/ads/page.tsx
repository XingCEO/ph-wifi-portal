"use client";

import { useEffect, useState } from "react";
import { Loader2, Megaphone, TrendingUp, Eye, DollarSign, CheckCircle, XCircle } from "lucide-react";
import { superadminFetch } from "../layout";
import { toast } from "../../components/Toast";

interface AdsStats {
  adcash_connected: boolean;
  total_ad_views: number;
  avg_cpm_usd: string;
  monthly_revenue_usd: string;
  top_sites: TopSite[];
}

interface TopSite {
  hotspot_id: number;
  hotspot_name: string;
  ad_views: number;
  revenue_usd: string;
  cpm_usd: string;
}

interface DailyAdRevenue {
  date: string;
  revenue_usd: string;
  ad_views: number;
}

function CssBarChart({ data }: { data: DailyAdRevenue[] }) {
  if (!data.length) return null;
  const maxRev = Math.max(...data.map((d) => parseFloat(d.revenue_usd)), 0.001);

  return (
    <div className="flex items-end gap-1.5 h-36 mt-3">
      {data.map((d, i) => {
        const pct = (parseFloat(d.revenue_usd) / maxRev) * 100;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              className="w-full bg-amber-500/70 hover:bg-amber-400 rounded-t transition-all cursor-pointer"
              style={{ height: `${Math.max(pct, 3)}%` }}
            />
            <span className="text-gray-600 text-xs truncate w-full text-center hidden sm:block">
              {d.date.slice(5)}
            </span>
            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs rounded px-2 py-1 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
              ${parseFloat(d.revenue_usd).toFixed(4)}<br />
              <span className="text-gray-400">{d.ad_views} 次觀看</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function SuperAdminAdsPage() {
  const [stats, setStats] = useState<AdsStats | null>(null);
  const [daily, setDaily] = useState<DailyAdRevenue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [statsRes, dailyRes] = await Promise.all([
          superadminFetch("/api/superadmin/ads/stats"),
          superadminFetch("/api/superadmin/ads/daily?days=14"),
        ]);
        if (statsRes.ok) setStats(await statsRes.json());
        if (dailyRes.ok) setDaily(await dailyRes.json());
      } catch {
        toast("error", "無法載入廣告資料");
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-amber-400" size={32} />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">廣告管理</h1>
        <p className="text-gray-500 mt-1 text-sm">廣告網路整合狀態與收益分析</p>
      </div>

      {/* Adcash connection status */}
      <div className={`rounded-2xl border p-5 mb-6 flex items-center gap-4 ${
        stats?.adcash_connected
          ? "bg-emerald-900/20 border-emerald-800"
          : "bg-red-900/20 border-red-800"
      }`}>
        {stats?.adcash_connected ? (
          <CheckCircle size={24} className="text-emerald-400 shrink-0" />
        ) : (
          <XCircle size={24} className="text-red-400 shrink-0" />
        )}
        <div>
          <p className={`font-semibold ${stats?.adcash_connected ? "text-emerald-300" : "text-red-300"}`}>
            Adcash 廣告網路：{stats?.adcash_connected ? "已連線" : "未連線"}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            {stats?.adcash_connected
              ? "廣告網路正常運作，收益持續累積中"
              : "請檢查 Adcash API 金鑰設定或網路連線"}
          </p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <Eye size={16} className="text-blue-400" />
            <p className="text-xs text-gray-500">總廣告觀看次數</p>
          </div>
          <p className="text-2xl font-bold text-white">
            {(stats?.total_ad_views ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={16} className="text-purple-400" />
            <p className="text-xs text-gray-500">平均 CPM</p>
          </div>
          <p className="text-2xl font-bold text-white">
            ${parseFloat(stats?.avg_cpm_usd ?? "0").toFixed(4)}
          </p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign size={16} className="text-amber-400" />
            <p className="text-xs text-gray-500">本月廣告收入</p>
          </div>
          <p className="text-2xl font-bold text-amber-400">
            ${parseFloat(stats?.monthly_revenue_usd ?? "0").toFixed(2)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily revenue chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h2 className="font-semibold text-white mb-1">每日廣告收入</h2>
          <p className="text-xs text-gray-500 mb-2">近 14 天（USD）</p>
          <CssBarChart data={daily} />
          {daily.length === 0 && (
            <p className="text-gray-600 text-xs text-center py-10">暫無資料</p>
          )}
        </div>

        {/* Top sites ranking */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h2 className="font-semibold text-white mb-4">站點廣告表現排名</h2>
          {!stats?.top_sites?.length ? (
            <p className="text-gray-600 text-xs">暫無站點資料</p>
          ) : (
            <div className="space-y-3">
              {stats.top_sites.map((site, i) => (
                <div key={site.hotspot_id} className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-gray-800 flex items-center justify-center shrink-0">
                    <span className="text-xs font-bold text-amber-400">#{i + 1}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{site.hotspot_name}</p>
                    <p className="text-xs text-gray-500">{site.ad_views.toLocaleString()} 次觀看</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-semibold text-amber-400">${parseFloat(site.revenue_usd).toFixed(4)}</p>
                    <p className="text-xs text-gray-500">CPM ${parseFloat(site.cpm_usd).toFixed(4)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Info note */}
      <div className="mt-6 bg-gray-900 border border-gray-800 rounded-2xl p-5">
        <div className="flex items-start gap-3">
          <Megaphone size={18} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-white">廣告整合說明</p>
            <p className="text-xs text-gray-500 mt-1">
              廣告收入由 Adcash 廣告網路驅動。用戶連接 WiFi 後觀看短片廣告，平台從每次觀看中獲得 CPM 收益，
              並依方案分潤給合作夥伴（70–85%）。收益結算為每月一次。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
