"use client";

import { useEffect, useState } from "react";
import { Wifi, Eye, DollarSign, TrendingUp, Loader2, Activity, BarChart2 } from "lucide-react";

interface Stats {
  total_connections: number;
  total_ad_views: number;
  total_revenue_usd: string;
  partner_revenue_usd: string;
  active_hotspots: number;
  period_days: number;
}

interface DailyTrend {
  date: string;
  connections: number;
}

interface HotspotSummary {
  id: number;
  name: string;
  is_active: boolean;
  today_connections: number;
  monthly_revenue_usd: string;
}

function StatCard({
  title,
  value,
  sub,
  icon: Icon,
  color,
}: {
  title: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{title}</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
          {sub && <p className="mt-1 text-sm text-gray-400">{sub}</p>}
        </div>
        <div className={`p-3 rounded-xl ${color}`}>
          <Icon size={22} className="text-white" />
        </div>
      </div>
    </div>
  );
}

function CssBarChart({ data }: { data: DailyTrend[] }) {
  if (!data.length) return null;
  const maxVal = Math.max(...data.map((d) => d.connections), 1);

  return (
    <div className="flex items-end gap-1.5 h-24 mt-3">
      {data.map((d, i) => {
        const pct = (d.connections / maxVal) * 100;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              className="w-full rounded-t transition-all"
              style={{
                height: `${Math.max(pct, 4)}%`,
                background: "var(--color-brand-green)",
                opacity: 0.75,
              }}
            />
            <span className="text-gray-400 text-xs hidden sm:block">
              {d.date.slice(5)}
            </span>
            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs rounded px-2 py-1 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
              {d.connections} 次連線
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [dailyTrend, setDailyTrend] = useState<DailyTrend[]>([]);
  const [hotspots, setHotspots] = useState<HotspotSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchAll = async () => {
      const token = localStorage.getItem("saas_token");
      if (!token) { window.location.href = "/login"; return; }
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [statsRes, trendRes, hotspotsRes] = await Promise.all([
          fetch("/api/dashboard/stats", { headers }),
          fetch("/api/dashboard/daily-trend?days=7", { headers }),
          fetch("/api/dashboard/hotspots", { headers }),
        ]);
        if (!statsRes.ok) throw new Error("無法載入統計資料");
        setStats(await statsRes.json());
        if (trendRes.ok) setDailyTrend(await trendRes.json());
        if (hotspotsRes.ok) {
          const hs = await hotspotsRes.json();
          setHotspots(hs.slice(0, 4)); // show max 4 in overview
        }
      } catch {
        setError("無法載入 Dashboard 資料");
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-[#2d6a4f]" size={32} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
        {error}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">總覽</h1>
        <p className="text-gray-500 mt-1">
          近 {stats?.period_days ?? 30} 天表現
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <StatCard
          title="連線次數"
          value={(stats?.total_connections ?? 0).toLocaleString()}
          sub="WiFi 連線授予次數"
          icon={Wifi}
          color="bg-blue-500"
        />
        <StatCard
          title="廣告觀看"
          value={(stats?.total_ad_views ?? 0).toLocaleString()}
          sub="完整廣告觀看次數"
          icon={Eye}
          color="bg-[#2d6a4f]"
        />
        <StatCard
          title="總收入"
          value={`$${parseFloat(stats?.total_revenue_usd ?? "0").toFixed(2)}`}
          sub="USD（稅前）"
          icon={TrendingUp}
          color="bg-amber-500"
        />
        <StatCard
          title="我的收益"
          value={`$${parseFloat(stats?.partner_revenue_usd ?? "0").toFixed(2)}`}
          sub="你的 70% 分潤"
          icon={DollarSign}
          color="bg-emerald-600"
        />
      </div>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 7-day trend */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-1">
            <Activity size={16} className="text-[#2d6a4f]" />
            <h2 className="text-lg font-semibold text-gray-800">近 7 天連線趨勢</h2>
          </div>
          <p className="text-sm text-gray-400 mb-2">每日連線次數</p>
          <CssBarChart data={dailyTrend} />
          {dailyTrend.length === 0 && (
            <p className="text-gray-400 text-sm text-center py-6">暫無資料</p>
          )}
        </div>

        {/* Quick Summary */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">快速摘要</h2>
          <dl className="space-y-3">
            {[
              ["活躍站點", `${stats?.active_hotspots ?? 0} 個`],
              ["統計期間", `近 ${stats?.period_days ?? 30} 天`],
              ["平台抽成", "30%"],
              ["我的分潤", "70%"],
            ].map(([label, val]) => (
              <div key={String(label)} className="flex justify-between text-sm">
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium text-gray-900">{String(val)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      {/* Site status cards */}
      {hotspots.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-800">我的站點狀態</h2>
            <a href="/dashboard/hotspots" className="text-sm text-[#2d6a4f] hover:underline font-medium">
              查看全部 →
            </a>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {hotspots.map((hs) => (
              <div key={hs.id} className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${hs.is_active ? "bg-emerald-500" : "bg-gray-300"}`} />
                  <p className="font-medium text-gray-900 text-sm truncate">{hs.name}</p>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>今日連線</span>
                  <span className="font-semibold text-gray-800">{hs.today_connections}</span>
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>本月收入</span>
                  <span className="font-semibold text-emerald-600">${parseFloat(hs.monthly_revenue_usd).toFixed(4)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Get started CTA */}
      {(stats?.active_hotspots ?? 0) === 0 && (
        <div className="mt-6 bg-[#2d6a4f] rounded-2xl p-6 text-white">
          <div className="flex items-center gap-2 mb-2">
            <BarChart2 size={20} />
            <h2 className="text-lg font-semibold">開始賺取 WiFi 廣告收益</h2>
          </div>
          <p className="text-white/80 text-sm mb-4">
            新增你的第一個站點，開始透過 WiFi 廣告賺取收益。
          </p>
          <a
            href="/dashboard/hotspots"
            className="inline-flex items-center gap-2 bg-white text-[#2d6a4f] font-semibold text-sm px-4 py-2 rounded-xl hover:bg-gray-50 transition-colors"
          >
            <Wifi size={16} />
            管理站點
          </a>
        </div>
      )}
    </div>
  );
}
