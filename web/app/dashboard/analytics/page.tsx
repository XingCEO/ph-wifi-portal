"use client";

import { useEffect, useState } from "react";
import { BarChart2, Loader2, Smartphone, Clock, TrendingUp } from "lucide-react";

interface AnalyticsData {
  hourly_distribution: HourlySlot[];
  device_types: DeviceType[];
  weekly_trend: WeeklyEntry[];
}

interface HourlySlot {
  hour: number;
  connections: number;
}

interface DeviceType {
  device_type: string;
  count: number;
  percentage: number;
}

interface WeeklyEntry {
  date: string;
  connections: number;
  ad_views: number;
}

const DEVICE_COLORS: Record<string, string> = {
  Android: "bg-green-500",
  iOS: "bg-blue-500",
  其他: "bg-gray-500",
};

const HOUR_LABELS = Array.from({ length: 24 }, (_, i) =>
  `${String(i).padStart(2, "0")}:00`
);

function HourlyChart({ data }: { data: HourlySlot[] }) {
  const maxVal = Math.max(...data.map((d) => d.connections), 1);
  return (
    <div className="flex items-end gap-0.5 h-28 mt-3">
      {data.map((d) => {
        const pct = (d.connections / maxVal) * 100;
        return (
          <div key={d.hour} className="flex-1 flex flex-col items-center gap-0.5 group relative">
            <div
              className="w-full rounded-sm transition-all"
              style={{
                height: `${Math.max(pct, 3)}%`,
                background: "var(--color-brand-green)",
                opacity: d.connections > 0 ? 0.7 : 0.15,
              }}
            />
            {d.hour % 6 === 0 && (
              <span className="text-gray-400 text-xs">{d.hour}h</span>
            )}
            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs rounded px-2 py-1 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-10 transition-opacity">
              {HOUR_LABELS[d.hour]}: {d.connections} 次
            </div>
          </div>
        );
      })}
    </div>
  );
}

function WeeklyChart({ data }: { data: WeeklyEntry[] }) {
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
            <span className="text-gray-400 text-xs hidden sm:block">{d.date.slice(5)}</span>
            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs rounded px-2 py-1 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-10 transition-opacity">
              {d.connections} 連線 / {d.ad_views} 廣告
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchAnalytics = async () => {
      const token = localStorage.getItem("saas_token");
      if (!token) return;
      try {
        const res = await fetch("/api/dashboard/analytics", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to load");
        setData(await res.json());
      } catch {
        setError("無法載入分析資料");
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
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
      <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
        {error}
      </div>
    );
  }

  const totalConnections = data?.weekly_trend.reduce((s, d) => s + d.connections, 0) ?? 0;
  const peakHour = data?.hourly_distribution.reduce((a, b) => a.connections > b.connections ? a : b, { hour: 0, connections: 0 });

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-2">
          <BarChart2 size={24} className="text-[#2d6a4f]" />
          <h1 className="text-2xl font-bold text-gray-900">數據分析</h1>
        </div>
        <p className="text-gray-500 mt-1">連線時段、裝置分佈與流量趨勢</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={16} className="text-[#2d6a4f]" />
            <p className="text-sm text-gray-500">本週連線總計</p>
          </div>
          <p className="text-2xl font-bold text-gray-900">{totalConnections.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={16} className="text-amber-500" />
            <p className="text-sm text-gray-500">尖峰時段</p>
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {peakHour && peakHour.connections > 0
              ? `${String(peakHour.hour).padStart(2, "0")}:00`
              : "—"
            }
          </p>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Smartphone size={16} className="text-blue-500" />
            <p className="text-sm text-gray-500">主要裝置</p>
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {data?.device_types?.[0]?.device_type ?? "—"}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Hourly distribution */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <Clock size={16} className="text-amber-500" />
            <h2 className="text-lg font-semibold text-gray-800">連線時段分佈</h2>
          </div>
          <p className="text-sm text-gray-400">24 小時連線次數分佈</p>
          {data?.hourly_distribution.length ? (
            <HourlyChart data={data.hourly_distribution} />
          ) : (
            <p className="text-gray-400 text-sm text-center py-8">暫無資料</p>
          )}
        </div>

        {/* Device type distribution */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Smartphone size={16} className="text-blue-500" />
            <h2 className="text-lg font-semibold text-gray-800">裝置類型分佈</h2>
          </div>
          {data?.device_types?.length ? (
            <div className="space-y-4">
              {data.device_types.map((dt) => (
                <div key={dt.device_type}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-700">{dt.device_type}</span>
                    <span className="text-gray-500">
                      {dt.count.toLocaleString()} ({dt.percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${DEVICE_COLORS[dt.device_type] ?? "bg-gray-400"}`}
                      style={{ width: `${dt.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm text-center py-8">暫無裝置資料</p>
          )}
        </div>
      </div>

      {/* Weekly trend */}
      <div className="mt-6 bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
        <div className="flex items-center gap-2 mb-1">
          <TrendingUp size={16} className="text-[#2d6a4f]" />
          <h2 className="text-lg font-semibold text-gray-800">流量趨勢（近 7 天）</h2>
        </div>
        <p className="text-sm text-gray-400">每日連線次數</p>
        {data?.weekly_trend.length ? (
          <WeeklyChart data={data.weekly_trend} />
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">暫無趨勢資料</p>
        )}
      </div>
    </div>
  );
}
