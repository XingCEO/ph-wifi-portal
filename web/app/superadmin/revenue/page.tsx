"use client";

import { useEffect, useState } from "react";
import { Loader2, DollarSign, TrendingUp, Eye, Activity } from "lucide-react";
import { superadminFetch } from "../layout";
import { toast } from "../../components/Toast";

interface RevenueEntry {
  period: string;
  total_revenue_usd: string;
  partner_payout_usd: string;
  platform_revenue_usd: string;
  ad_views_count: number;
  connection_count: number;
}

type Period = "daily" | "weekly" | "monthly";

export default function SuperAdminRevenuePage() {
  const [data, setData] = useState<RevenueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<Period>("monthly");
  const [limit, setLimit] = useState(12);

  const fetchRevenue = async (p: Period, l: number) => {
    setLoading(true);
    try {
      const res = await superadminFetch(`/api/superadmin/revenue?period=${p}&limit=${l}`);
      if (!res.ok) throw new Error("Failed to load");
      setData(await res.json());
    } catch {
      toast("error", "Failed to load revenue data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRevenue(period, limit); }, [period, limit]);

  const totals = data.reduce(
    (acc, row) => ({
      revenue: acc.revenue + parseFloat(row.total_revenue_usd),
      partner: acc.partner + parseFloat(row.partner_payout_usd),
      platform: acc.platform + parseFloat(row.platform_revenue_usd),
      views: acc.views + row.ad_views_count,
      conns: acc.conns + row.connection_count,
    }),
    { revenue: 0, partner: 0, platform: 0, views: 0, conns: 0 }
  );

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Revenue Report</h1>
          <p className="text-gray-500 text-sm mt-0.5">Platform-wide earnings breakdown</p>
        </div>
        <div className="flex gap-2">
          {(["daily", "weekly", "monthly"] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-xl transition-colors capitalize ${
                period === p
                  ? "bg-amber-500 text-gray-900"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {p}
            </button>
          ))}
          <select
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value))}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded-xl px-2 py-1.5 focus:outline-none"
          >
            <option value={7}>7</option>
            <option value={12}>12</option>
            <option value={30}>30</option>
          </select>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Revenue", value: `$${totals.revenue.toFixed(2)}`, icon: DollarSign, color: "text-amber-400" },
          { label: "Platform Kept", value: `$${totals.platform.toFixed(2)}`, icon: TrendingUp, color: "text-orange-400" },
          { label: "Partner Payout", value: `$${totals.partner.toFixed(2)}`, icon: DollarSign, color: "text-emerald-400" },
          { label: "Ad Views", value: totals.views.toLocaleString(), icon: Eye, color: "text-blue-400" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <Icon size={15} className={color} />
              <p className="text-xs text-gray-500">{label}</p>
            </div>
            <p className={`text-xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <Loader2 className="animate-spin text-amber-400" size={28} />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 bg-gray-900/60">
                  <th className="text-left px-5 py-3 text-gray-500 font-medium">Period</th>
                  <th className="text-right px-5 py-3 text-gray-500 font-medium">Total Revenue</th>
                  <th className="text-right px-5 py-3 text-gray-500 font-medium">Platform (30%)</th>
                  <th className="text-right px-5 py-3 text-gray-500 font-medium">Partner Payout</th>
                  <th className="text-right px-5 py-3 text-gray-500 font-medium">Ad Views</th>
                  <th className="text-right px-5 py-3 text-gray-500 font-medium">Connections</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={i} className="border-t border-gray-800 hover:bg-gray-800/30 transition-colors">
                    <td className="px-5 py-3 font-medium text-white">{row.period}</td>
                    <td className="px-5 py-3 text-right text-amber-400 font-medium">
                      ${parseFloat(row.total_revenue_usd).toFixed(4)}
                    </td>
                    <td className="px-5 py-3 text-right text-orange-400">
                      ${parseFloat(row.platform_revenue_usd).toFixed(4)}
                    </td>
                    <td className="px-5 py-3 text-right text-emerald-400">
                      ${parseFloat(row.partner_payout_usd).toFixed(4)}
                    </td>
                    <td className="px-5 py-3 text-right text-gray-300">{row.ad_views_count.toLocaleString()}</td>
                    <td className="px-5 py-3 text-right text-gray-300">{row.connection_count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-gray-700 bg-gray-800/50">
                  <td className="px-5 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Totals</td>
                  <td className="px-5 py-3 text-right font-bold text-amber-400">${totals.revenue.toFixed(4)}</td>
                  <td className="px-5 py-3 text-right font-bold text-orange-400">${totals.platform.toFixed(4)}</td>
                  <td className="px-5 py-3 text-right font-bold text-emerald-400">${totals.partner.toFixed(4)}</td>
                  <td className="px-5 py-3 text-right font-bold text-gray-300">{totals.views.toLocaleString()}</td>
                  <td className="px-5 py-3 text-right font-bold text-gray-300">{totals.conns.toLocaleString()}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
