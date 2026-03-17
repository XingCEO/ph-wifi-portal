"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, Search, MapPin, ChevronLeft, ChevronRight, Activity, Eye, DollarSign, Power } from "lucide-react";
import { superadminFetch } from "../layout";
import { toast } from "../../components/Toast";

interface SiteDetail {
  id: number;
  name: string;
  location: string;
  ap_mac: string;
  is_active: boolean;
  org_id: number | null;
  org_name: string | null;
  today_connections: number;
  connections_30d: number;
  ad_views_30d: number;
  revenue_30d_usd: string;
  last_activity: string | null;
  controller_connected: boolean;
  created_at: string;
}

const PAGE_SIZE = 20;

export default function SuperAdminSitesPage() {
  const [sites, setSites] = useState<SiteDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const fetchSites = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (search) params.set("search", search);
      const res = await superadminFetch(`/api/superadmin/sites?${params}`);
      if (!res.ok) throw new Error("Failed to load");
      setSites(await res.json());
    } catch {
      toast("error", "無法載入站點資料");
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { fetchSites(); }, [fetchSites]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const handleToggle = async (site: SiteDetail) => {
    setTogglingId(site.id);
    try {
      const res = await superadminFetch(`/api/superadmin/sites/${site.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !site.is_active }),
      });
      if (!res.ok) throw new Error("Failed to update");
      const updated: SiteDetail = await res.json();
      setSites((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      toast("success", `站點已${updated.is_active ? "啟用" : "停用"}`);
    } catch {
      toast("error", "更新站點狀態失敗");
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">站點管理</h1>
          <p className="text-gray-500 text-sm mt-0.5">所有站點詳細資訊與健康監控</p>
        </div>
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="依名稱或地點搜尋..."
              className="bg-gray-800 border border-gray-700 rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-amber-500/40 w-64"
            />
          </div>
          <button type="submit" className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-gray-900 text-sm font-semibold rounded-xl transition-colors">
            搜尋
          </button>
        </form>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <Loader2 className="animate-spin text-amber-400" size={28} />
          </div>
        ) : sites.length === 0 ? (
          <div className="text-center py-16">
            <MapPin size={32} className="text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">找不到站點</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-900/60">
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">站點</th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">所屬組織</th>
                    <th className="text-right px-5 py-3 text-gray-500 font-medium">
                      <div className="flex items-center justify-end gap-1"><Activity size={13} />今日連線</div>
                    </th>
                    <th className="text-right px-5 py-3 text-gray-500 font-medium">
                      <div className="flex items-center justify-end gap-1"><Eye size={13} />廣告（30天）</div>
                    </th>
                    <th className="text-right px-5 py-3 text-gray-500 font-medium">
                      <div className="flex items-center justify-end gap-1"><DollarSign size={13} />收入（30天）</div>
                    </th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">Controller</th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">上線狀態</th>
                    <th className="text-right px-5 py-3 text-gray-500 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {sites.map((site) => (
                    <tr key={site.id} className="border-t border-gray-800 hover:bg-gray-800/40 transition-colors">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full shrink-0 ${site.is_active ? "bg-emerald-400" : "bg-gray-600"}`} />
                          <div>
                            <p className="font-medium text-white">{site.name}</p>
                            <p className="text-gray-500 text-xs">{site.location}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-gray-400 text-xs">
                        {site.org_name || "—"}
                      </td>
                      <td className="px-5 py-3.5 text-right text-white font-medium">
                        {site.today_connections.toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5 text-right text-gray-300">
                        {site.ad_views_30d.toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5 text-right text-amber-400 font-medium">
                        ${parseFloat(site.revenue_30d_usd).toFixed(4)}
                      </td>
                      <td className="px-5 py-3.5">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          site.controller_connected
                            ? "bg-emerald-900/40 text-emerald-400"
                            : "bg-yellow-900/40 text-yellow-400"
                        }`}>
                          {site.controller_connected ? "已連線" : "未連線"}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          site.is_active
                            ? "bg-emerald-900/40 text-emerald-400"
                            : "bg-gray-700 text-gray-400"
                        }`}>
                          {site.is_active ? "運作中" : "已停用"}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => handleToggle(site)}
                          disabled={togglingId === site.id}
                          title={site.is_active ? "停用站點" : "啟用站點"}
                          className={`p-1.5 rounded-lg text-xs font-medium transition-colors border ${
                            site.is_active
                              ? "bg-red-900/30 text-red-400 hover:bg-red-900/50 border-red-800"
                              : "bg-emerald-900/30 text-emerald-400 hover:bg-emerald-900/50 border-emerald-800"
                          } disabled:opacity-50`}
                        >
                          {togglingId === site.id
                            ? <Loader2 size={14} className="animate-spin" />
                            : <Power size={14} />
                          }
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between px-5 py-3 border-t border-gray-800">
              <p className="text-xs text-gray-500">第 {page} 頁 · {sites.length} 筆結果</p>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="p-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-white disabled:opacity-40 transition-colors">
                  <ChevronLeft size={16} />
                </button>
                <button onClick={() => setPage((p) => p + 1)} disabled={sites.length < PAGE_SIZE}
                  className="p-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-white disabled:opacity-40 transition-colors">
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
