"use client";

import { useEffect, useState } from "react";
import { Loader2, Users, Wifi, DollarSign, TrendingUp, Building2, Activity } from "lucide-react";
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

export default function SuperAdminDashboard() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await superadminFetch("/api/superadmin/stats");
        if (!res.ok) throw new Error("Failed to load");
        setStats(await res.json());
      } catch {
        toast("error", "Failed to load platform stats");
      } finally {
        setLoading(false);
      }
    };
    fetch();
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
        <h1 className="text-2xl font-bold text-white">Platform Overview</h1>
        <p className="text-gray-500 mt-1 text-sm">Real-time platform metrics</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
        <StatCard
          title="Total Users"
          value={(stats?.total_saas_users ?? 0).toLocaleString()}
          sub={`+${stats?.new_users_this_month ?? 0} this month`}
          icon={Users}
          color="bg-blue-600"
        />
        <StatCard
          title="Organizations"
          value={(stats?.total_organizations ?? 0).toLocaleString()}
          sub={`+${stats?.new_orgs_this_month ?? 0} this month`}
          icon={Building2}
          color="bg-violet-600"
        />
        <StatCard
          title="Total Hotspots"
          value={(stats?.total_hotspots ?? 0).toLocaleString()}
          sub={`${stats?.active_hotspots ?? 0} active`}
          icon={Wifi}
          color="bg-emerald-600"
        />
        <StatCard
          title="Total Connections"
          value={(stats?.total_connections_all_time ?? 0).toLocaleString()}
          sub="All time"
          icon={Activity}
          color="bg-cyan-600"
        />
        <StatCard
          title="Total Revenue"
          value={`$${parseFloat(stats?.total_revenue_usd ?? "0").toFixed(2)}`}
          sub="All time (gross)"
          icon={DollarSign}
          color="bg-amber-500"
        />
        <StatCard
          title="Monthly Revenue"
          value={`$${parseFloat(stats?.monthly_revenue_usd ?? "0").toFixed(2)}`}
          sub="This month"
          icon={TrendingUp}
          color="bg-orange-600"
        />
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
          <h2 className="font-semibold text-white mb-3">Quick Actions</h2>
          <div className="space-y-2">
            {[
              { href: "/superadmin/users", label: "View all users", icon: Users },
              { href: "/superadmin/hotspots", label: "View all hotspots", icon: Wifi },
              { href: "/superadmin/revenue", label: "Revenue report", icon: DollarSign },
              { href: "/superadmin/plans", label: "Manage plans", icon: TrendingUp },
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

        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5">
          <h2 className="font-semibold text-amber-400 mb-2">Platform Health</h2>
          <div className="space-y-2 text-sm">
            {[
              ["Active hotspots", `${stats?.active_hotspots ?? 0} / ${stats?.total_hotspots ?? 0}`],
              ["New users (month)", stats?.new_users_this_month ?? 0],
              ["New orgs (month)", stats?.new_orgs_this_month ?? 0],
              ["Total connections", (stats?.total_connections_all_time ?? 0).toLocaleString()],
            ].map(([label, val]) => (
              <div key={String(label)} className="flex justify-between">
                <span className="text-gray-500">{label}</span>
                <span className="font-medium text-white">{String(val)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
