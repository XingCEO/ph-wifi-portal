"use client";

import { useEffect, useState } from "react";
import { DollarSign, Loader2, Calendar, CheckCircle, Clock } from "lucide-react";

interface RevenueSplit {
  id: number;
  hotspot_id: number | null;
  period_start: string;
  period_end: string;
  total_revenue_usd: string;
  partner_pct: string;
  partner_amount_usd: string;
  ad_views_count: number;
  status: string;
  created_at: string;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("zh-TW", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function RevenuePage() {
  const [splits, setSplits] = useState<RevenueSplit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchRevenue = async () => {
      const token = localStorage.getItem("saas_token");
      if (!token) return;
      try {
        const res = await fetch("/api/dashboard/revenue?limit=24", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to load");
        setSplits(await res.json());
      } catch {
        setError("無法載入收入資料");
      } finally {
        setLoading(false);
      }
    };
    fetchRevenue();
  }, []);

  const totalEarned = splits
    .filter((s) => s.status === "paid")
    .reduce((sum, s) => sum + parseFloat(s.partner_amount_usd), 0);

  const totalPending = splits
    .filter((s) => s.status === "pending")
    .reduce((sum, s) => sum + parseFloat(s.partner_amount_usd), 0);

  const STATUS_LABELS: Record<string, string> = {
    paid: "已付款",
    pending: "待處理",
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">收入分析</h1>
        <p className="text-gray-500 mt-1">廣告收益分潤與付款記錄</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-emerald-100 p-2 rounded-xl">
              <CheckCircle size={20} className="text-emerald-600" />
            </div>
            <p className="text-gray-500 font-medium text-sm">已付款總計</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">${totalEarned.toFixed(4)}</p>
          <p className="text-sm text-gray-400 mt-1">USD</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-amber-100 p-2 rounded-xl">
              <Clock size={20} className="text-amber-600" />
            </div>
            <p className="text-gray-500 font-medium text-sm">待結算</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">${totalPending.toFixed(4)}</p>
          <p className="text-sm text-gray-400 mt-1">USD（尚未結算）</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="animate-spin text-[#1B4F8A]" size={28} />
        </div>
      ) : splits.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-gray-100">
          <DollarSign className="mx-auto text-gray-300" size={48} />
          <p className="mt-3 text-gray-500">尚無收入記錄。</p>
          <p className="text-sm text-gray-400 mt-1">
            廣告觀看次數累積後，每月自動生成收益分潤記錄。
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-6 py-3 text-gray-500 font-medium">期間</th>
                <th className="text-right px-6 py-3 text-gray-500 font-medium">廣告觀看</th>
                <th className="text-right px-6 py-3 text-gray-500 font-medium">總收入</th>
                <th className="text-right px-6 py-3 text-gray-500 font-medium">我的分潤</th>
                <th className="text-center px-6 py-3 text-gray-500 font-medium">狀態</th>
              </tr>
            </thead>
            <tbody>
              {splits.map((s) => (
                <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Calendar size={14} className="text-gray-400" />
                      <span className="text-gray-700">
                        {formatDate(s.period_start)} — {formatDate(s.period_end)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right text-gray-700">
                    {s.ad_views_count.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-right text-gray-700">
                    ${parseFloat(s.total_revenue_usd).toFixed(4)}
                  </td>
                  <td className="px-6 py-4 text-right font-semibold text-gray-900">
                    ${parseFloat(s.partner_amount_usd).toFixed(4)}
                    <span className="text-xs text-gray-400 font-normal ml-1">
                      ({parseFloat(s.partner_pct).toFixed(0)}%)
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium
                        ${s.status === "paid"
                          ? "bg-green-100 text-green-700"
                          : "bg-amber-100 text-amber-700"
                        }`}
                    >
                      {s.status === "paid" ? (
                        <CheckCircle size={12} />
                      ) : (
                        <Clock size={12} />
                      )}
                      {STATUS_LABELS[s.status] ?? s.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
