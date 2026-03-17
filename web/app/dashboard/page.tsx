"use client";

import { useEffect, useState } from "react";
import { Wifi, Eye, DollarSign, TrendingUp, Loader2 } from "lucide-react";

interface Stats {
  total_connections: number;
  total_ad_views: number;
  total_revenue_usd: string;
  partner_revenue_usd: string;
  active_hotspots: number;
  period_days: number;
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

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchStats = async () => {
      const token = localStorage.getItem("saas_token");
      if (!token) return;
      try {
        const res = await fetch("/api/dashboard/stats", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to load stats");
        const data = await res.json();
        setStats(data);
      } catch {
        setError("Could not load dashboard data");
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
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
        <h1 className="text-2xl font-bold text-gray-900">Dashboard Overview</h1>
        <p className="text-gray-500 mt-1">
          Last {stats?.period_days ?? 30} days performance
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <StatCard
          title="Total Connections"
          value={(stats?.total_connections ?? 0).toLocaleString()}
          sub="WiFi sessions granted"
          icon={Wifi}
          color="bg-blue-500"
        />
        <StatCard
          title="Ad Views"
          value={(stats?.total_ad_views ?? 0).toLocaleString()}
          sub="Completed ad views"
          icon={Eye}
          color="bg-[#2d6a4f]"
        />
        <StatCard
          title="Total Revenue"
          value={`$${parseFloat(stats?.total_revenue_usd ?? "0").toFixed(2)}`}
          sub="USD (gross)"
          icon={TrendingUp}
          color="bg-amber-500"
        />
        <StatCard
          title="Your Earnings"
          value={`$${parseFloat(stats?.partner_revenue_usd ?? "0").toFixed(2)}`}
          sub="Your 70% share"
          icon={DollarSign}
          color="bg-emerald-600"
        />
      </div>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Quick Summary</h2>
          <dl className="space-y-3">
            {[
              ["Active Hotspots", stats?.active_hotspots ?? 0],
              ["Revenue Period", `${stats?.period_days ?? 30} days`],
              ["Platform Cut", "30%"],
              ["Your Share", "70%"],
            ].map(([label, val]) => (
              <div key={String(label)} className="flex justify-between text-sm">
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium text-gray-900">{String(val)}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="bg-[#2d6a4f] rounded-2xl p-6 text-white">
          <h2 className="text-lg font-semibold mb-2">Get Started</h2>
          <p className="text-white/80 text-sm mb-4">
            Add your first hotspot to start earning from WiFi ads.
          </p>
          <a
            href="/dashboard/hotspots"
            className="inline-flex items-center gap-2 bg-white text-[#2d6a4f] font-semibold text-sm px-4 py-2 rounded-xl hover:bg-gray-50 transition-colors"
          >
            <Wifi size={16} />
            Manage Hotspots
          </a>
        </div>
      </div>
    </div>
  );
}
