"use client";

import { useEffect, useState } from "react";
import { Loader2, Users, Wifi, DollarSign, TrendingUp, Building2, Activity, MapPin, Megaphone } from "lucide-react";
import { superadminFetch } from "./layout";
import { toast } from "../components/Toast";

interface PlatformStats {
  total_saas_users: number;
  total_organizations: number;
  total_hotspots: number;
  active_hotspots: number;
  total_connections_all_time: number;
  total_revenue_usd: string;
  monthly_revenue_usd: string;
  new_users_this_month: number;
  new_orgs_this_month: number;
}

interface DailyRevenue {
  date: string;
  revenue_usd: string;
  ad_views: number;
}

interface ActivityLog {
  id: number;
  action: string;
  target: string;
  admin_user: string;
  created_at: string;
}

function StatCard({
  title,
  value,
  sub,
  icon: Icon,
  color,
}: {
  title: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">{title}</p>
          <p className="mt-1.5 text-2xl font-bold text-white">{value}</p>
          {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
        </div>
        <div className={`p-2.5 rounded-xl ${color}`}>
          <Icon size={18} className="text-white" />
        </div>
      </div>
    </div>
  );
}

function CssBarChart({ data }: { data: DailyRevenue[] }) {
  if (!data.length) return null;
  const maxRev = Math.max(...data.map((d) => parseFloat(d.revenue_usd)), 0.001);

  return (
    <div className="flex items-end gap-1 h-32 mt-3">
      {data.map((d, i) => {
        const pct = (parseFloat(d.revenue_usd) / maxRev) * 100;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              className="w-full bg-amber-500/70 hover:bg-amber-400 rounded-t transition-all"
              style={{ height: `${Math.max(pct, 3)}%` }}
            />
            <span className="text-gray-600 text-xs hidden sm:block truncate w-full text-center">
              {d.date.slice(5)}
            </span>
            {/* Tooltip */}
            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs rounded px-2 py-1 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
              ${parseFloat(d.revenue_usd).toFixed(4)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function SuperAdminDashboard() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [dailyRevenue, setDailyRevenue] = useState<DailyRevenue[]>([]);
  const [activityLog, setActivityLog] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [statsRes, dailyRes, activityRes] = await Promise.all([
          superadminFetch("/api/superadmin/stats"),
          superadminFetch("/api/superadmin/ads/daily?days=7"),
          superadminFetch("/api/superadmin/activity"),
        ]);
        if (!statsRes.ok) throw new Error("Failed to load stats");
        setStats(await statsRes.json());
        if (dailyRes.ok) setDailyRevenue(await dailyRes.json());
        if (activityRes.ok) setActivityLog(await activityRes.json());
      } catch {
        toast("error", "無法載入平台統計資料");
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
        <h1 className="text-2xl font-bold text-white">平台總覽</h1>
        <p className="text-gray-500 mt-1 text-sm">即時平台指標</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
        <StatCard
          title="總用戶數"
          value={(stats?.total_saas_users ?? 0).toLocaleString()}
          sub={`本月新增 +${stats?.new_users_this_month ?? 0}`}
          icon={Users}
          color="bg-blue-600"
        />
        <StatCard
          title="組織數"
          value={(stats?.total_organizations ?? 0).toLocaleString()}
          sub={`本月新增 +${stats?.new_orgs_this_month ?? 0}`}
          icon={Building2}
          color="bg-violet-600"
        />
        <StatCard
          title="站點總數"
          value={(stats?.total_hotspots ?? 0).toLocaleString()}
          sub={`活躍 ${stats?.active_hotspots ?? 0} 個`}
          icon={Wifi}
          color="bg-emerald-600"
        />
        <StatCard
          title="累計連線次數"
          value={(stats?.total_connections_all_time ?? 0).toLocaleString()}
          sub="歷史總計"
          icon={Activity}
          color="bg-cyan-600"
        />
        <StatCard
          title="累計收入"
          value={`$${parseFloat(stats?.total_revenue_usd ?? "0").toFixed(2)}`}
          sub="歷史總計（稅前）"
          icon={DollarSign}
          color="bg-amber-500"
        />
        <StatCard
          title="本月收入"
          value={`$${parseFloat(stats?.monthly_revenue_usd ?? "0").toFixed(2)}`}
          sub="本月迄今"
          icon={TrendingUp}
          color="bg-orange-600"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Revenue trend chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h2 className="font-semibold text-white mb-1">近 7 天收入趨勢</h2>
          <p className="text-xs text-gray-500 mb-2">每日廣告收入（USD）</p>
          <CssBarChart data={dailyRevenue} />
          {dailyRevenue.length === 0 && (
            <p className="text-gray-600 text-xs text-center py-8">暫無收入資料</p>
          )}
        </div>

        {/* Platform Health */}
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5">
          <h2 className="font-semibold text-amber-400 mb-3">平台健康狀態</h2>
          <div className="space-y-2 text-sm">
            {[
              ["活躍站點", `${stats?.active_hotspots ?? 0} / ${stats?.total_hotspots ?? 0}`],
              ["本月新用戶", stats?.new_users_this_month ?? 0],
              ["本月新組織", stats?.new_orgs_this_month ?? 0],
              ["累計連線次數", (stats?.total_connections_all_time ?? 0).toLocaleString()],
            ].map(([label, val]) => (
              <div key={String(label)} className="flex justify-between">
                <span className="text-gray-500">{label}</span>
                <span className="font-medium text-white">{String(val)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick links + Activity log */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h2 className="font-semibold text-white mb-3">快速操作</h2>
          <div className="space-y-2">
            {[
              { href: "/superadmin/users", label: "查看所有用戶", icon: Users },
              { href: "/superadmin/sites", label: "站點詳細管理", icon: MapPin },
              { href: "/superadmin/ads", label: "廣告管理", icon: Megaphone },
              { href: "/superadmin/revenue", label: "收入分析報表", icon: DollarSign },
              { href: "/superadmin/plans", label: "方案管理", icon: TrendingUp },
            ].map(({ href, label, icon: Icon }) => (
              <a
                key={href}
                href={href}
                className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
              >
                <Icon size={15} className="text-amber-400" />
                {label}
              </a>
            ))}
          </div>
        </div>

        {/* Recent activity */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h2 className="font-semibold text-white mb-3">最近操作記錄</h2>
          {activityLog.length === 0 ? (
            <p className="text-gray-600 text-xs">暫無操作記錄</p>
          ) : (
            <div className="space-y-2">
              {activityLog.slice(0, 10).map((log) => (
                <div key={log.id} className="flex items-start gap-2 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="text-gray-300 font-medium">{log.action}</span>
                    {log.target && <span className="text-gray-500"> — {log.target}</span>}
                    <div className="text-gray-600 mt-0.5">
                      {log.admin_user} · {new Date(log.created_at).toLocaleString("zh-TW", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
