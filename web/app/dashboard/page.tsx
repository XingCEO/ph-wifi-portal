"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Wifi, Eye, DollarSign, TrendingUp, Loader2, Activity, BarChart2, Plus, ArrowRight } from "lucide-react";

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
  textColor,
}: {
  title: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  color: string;
  textColor?: string;
}) {
  return (
    <div className="card-hover bg-white rounded-2xl p-6 shadow-sm border border-gray-100 cursor-default">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-500 font-medium">{title}</p>
          <p className={`mt-2 text-3xl font-bold ${textColor ?? "text-gray-900"}`}>{value}</p>
          {sub && <p className="mt-1 text-sm text-gray-400">{sub}</p>}
        </div>
        <div className={`p-3 rounded-2xl shrink-0 ${color}`}>
          <Icon size={24} className="text-white" />
        </div>
      </div>
    </div>
  );
}

function CssBarChart({ data }: { data: DailyTrend[] }) {
  if (!data.length) return null;
  const maxVal = Math.max(...data.map((d) => d.connections), 1);

  return (
    <div className="flex items-end gap-2 h-28 mt-4">
      {data.map((d, i) => {
        const pct = (d.connections / maxVal) * 100;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              className="w-full rounded-t transition-all duration-200 hover:opacity-90"
              style={{
                height: `${Math.max(pct, 4)}%`,
                background: "var(--color-brand-green)",
                opacity: 0.7,
              }}
            />
            <span className="text-gray-400 text-xs hidden sm:block">{d.date.slice(5)}</span>
            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs rounded-lg px-2 py-1 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10 shadow-lg">
              {d.connections.toLocaleString()} 次連線
            </div>
          </div>
        );
      })}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-16 px-6 bg-white rounded-2xl border-2 border-dashed border-gray-200 animate-fade-in">
      <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl mb-6" style={{ background: "var(--color-brand-green)" }}>
        <Wifi size={36} className="text-white" />
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-2">還沒有站點？</h3>
      <p className="text-gray-500 text-sm mb-8 max-w-sm mx-auto leading-relaxed">
        新增你的第一個 WiFi 站點，讓用戶連接並觀看廣告。<br />
        你可以獲得 <strong className="text-[#1B4F8A]">70%</strong> 的廣告收益，每月自動結算。
      </p>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <Link
          href="/dashboard/hotspots"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-white font-semibold text-sm transition-all hover:opacity-90 btn-scale"
          style={{ background: "var(--color-brand-green)" }}
        >
          <Plus size={18} />
          立即新增站點
        </Link>
        <Link
          href="/dashboard/billing"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-gray-700 font-medium text-sm border border-gray-200 hover:bg-gray-50 transition-colors"
        >
          查看方案
          <ArrowRight size={16} />
        </Link>
      </div>
      <div className="mt-8 grid grid-cols-3 gap-4 max-w-sm mx-auto text-center">
        {[
          { label: "設定時間", value: "< 10 分鐘" },
          { label: "最低設備", value: "1 台 OC200" },
          { label: "你的分潤", value: "70%" },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-50 rounded-xl p-3">
            <p className="text-lg font-bold text-[#1B4F8A]">{value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>
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
      if (!token) return;
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
          setHotspots(hs.slice(0, 4));
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
        <Loader2 className="animate-spin text-[#1B4F8A]" size={32} />
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

  const hasHotspots = (stats?.active_hotspots ?? 0) > 0 || hotspots.length > 0;

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">總覽</h1>
        <p className="text-gray-500 mt-1">
          近 {stats?.period_days ?? 30} 天表現
        </p>
      </div>

      {/* 空白狀態引導 */}
      {!hasHotspots ? (
        <EmptyState />
      ) : (
        <>
          {/* Stats grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
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
              color="bg-[#1B4F8A]"
            />
            <StatCard
              title="總收入"
              value={`$${parseFloat(stats?.total_revenue_usd ?? "0").toFixed(2)}`}
              sub="USD（稅前）"
              icon={TrendingUp}
              color="bg-amber-500"
              textColor="text-amber-600"
            />
            <StatCard
              title="我的收益"
              value={`$${parseFloat(stats?.partner_revenue_usd ?? "0").toFixed(2)}`}
              sub="你的 70% 分潤"
              icon={DollarSign}
              color="bg-emerald-600"
              textColor="text-emerald-600"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* 7-day trend */}
            <div className="card-hover bg-white rounded-2xl p-6 shadow-sm border border-gray-100 cursor-default">
              <div className="flex items-center gap-2 mb-1">
                <Activity size={16} className="text-[#1B4F8A]" />
                <h2 className="text-lg font-semibold text-gray-800">近 7 天連線趨勢</h2>
              </div>
              <p className="text-sm text-gray-400">每日連線次數</p>
              <CssBarChart data={dailyTrend} />
              {dailyTrend.length === 0 && (
                <p className="text-gray-400 text-sm text-center py-6">暫無資料</p>
              )}
            </div>

            {/* Quick Summary */}
            <div className="card-hover bg-white rounded-2xl p-6 shadow-sm border border-gray-100 cursor-default">
              <div className="flex items-center gap-2 mb-4">
                <BarChart2 size={16} className="text-[#1B4F8A]" />
                <h2 className="text-lg font-semibold text-gray-800">快速摘要</h2>
              </div>
              <dl className="space-y-4">
                {[
                  ["活躍站點", `${stats?.active_hotspots ?? 0} 個`],
                  ["統計期間", `近 ${stats?.period_days ?? 30} 天`],
                  ["平台抽成", "30%"],
                  ["我的分潤", "70%"],
                ].map(([label, val]) => (
                  <div key={String(label)} className="flex justify-between items-center text-sm">
                    <dt className="text-gray-500">{label}</dt>
                    <dd className="font-semibold text-gray-900">{String(val)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>

          {/* Site status cards */}
          {hotspots.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-gray-800">我的站點狀態</h2>
                <Link href="/dashboard/hotspots" className="text-sm hover:underline font-medium flex items-center gap-1" style={{ color: "var(--color-brand-green)" }}>
                  查看全部 <ArrowRight size={14} />
                </Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                {hotspots.map((hs) => (
                  <div key={hs.id} className="card-hover bg-white rounded-xl p-4 border border-gray-100 shadow-sm cursor-default">
                    <div className="flex items-center gap-2 mb-3">
                      <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${hs.is_active ? "bg-emerald-500" : "bg-gray-300"}`} />
                      <p className="font-semibold text-gray-900 text-sm truncate">{hs.name}</p>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">今日連線</span>
                        <span className="font-semibold text-gray-800">{hs.today_connections.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">本月收入</span>
                        <span className="font-semibold text-emerald-600">${parseFloat(hs.monthly_revenue_usd ?? "0").toFixed(4)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
