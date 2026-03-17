"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, Search, Wifi, ChevronLeft, ChevronRight } from "lucide-react";
import { superadminFetch } from "../layout";
import { toast } from "../../components/Toast";

interface Hotspot {
  id: number;
  name: string;
  location: string;
  ap_mac: string;
  is_active: boolean;
  org_id: number | null;
  org_name: string | null;
  connections_30d: number;
  revenue_30d_usd: string;
  created_at: string;
}

const PAGE_SIZE = 20;

export default function SuperAdminHotspotsPage() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);

  const fetchHotspots = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (search) params.set("search", search);
      const res = await superadminFetch(`/api/superadmin/hotspots?${params}`);
      if (!res.ok) throw new Error("Failed to load");
      setHotspots(await res.json());
    } catch {
      toast("error", "Failed to load hotspots");
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { fetchHotspots(); }, [fetchHotspots]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">All Hotspots</h1>
          <p className="text-gray-500 text-sm mt-0.5">Platform-wide hotspot overview</p>
        </div>
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search by name or location..."
              className="bg-gray-800 border border-gray-700 rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-amber-500/40 w-64"
            />
          </div>
          <button type="submit" className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-gray-900 text-sm font-semibold rounded-xl transition-colors">
            Search
          </button>
        </form>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <Loader2 className="animate-spin text-amber-400" size={28} />
          </div>
        ) : hotspots.length === 0 ? (
          <div className="text-center py-16">
            <Wifi size={32} className="text-gray-700 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No hotspots found</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-900/60">
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">Hotspot</th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">Owner</th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">AP MAC</th>
                    <th className="text-right px-5 py-3 text-gray-500 font-medium">Conn (30d)</th>
                    <th className="text-right px-5 py-3 text-gray-500 font-medium">Rev (30d)</th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {hotspots.map((hs) => (
                    <tr key={hs.id} className="border-t border-gray-800 hover:bg-gray-800/40 transition-colors">
                      <td className="px-5 py-3.5">
                        <p className="font-medium text-white">{hs.name}</p>
                        <p className="text-gray-500 text-xs">{hs.location}</p>
                      </td>
                      <td className="px-5 py-3.5">
                        <p className="text-white text-xs">{hs.org_name || "—"}</p>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-gray-400">{hs.ap_mac}</td>
                      <td className="px-5 py-3.5 text-right text-white font-medium">{hs.connections_30d.toLocaleString()}</td>
                      <td className="px-5 py-3.5 text-right text-amber-400 font-medium">${parseFloat(hs.revenue_30d_usd).toFixed(4)}</td>
                      <td className="px-5 py-3.5">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          hs.is_active ? "bg-emerald-900/40 text-emerald-400" : "bg-gray-700 text-gray-400"
                        }`}>
                          {hs.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between px-5 py-3 border-t border-gray-800">
              <p className="text-xs text-gray-500">Page {page} · {hotspots.length} results</p>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="p-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-white disabled:opacity-40 transition-colors">
                  <ChevronLeft size={16} />
                </button>
                <button onClick={() => setPage((p) => p + 1)} disabled={hotspots.length < PAGE_SIZE}
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
