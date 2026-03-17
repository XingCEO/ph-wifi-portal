"use client";

import { useEffect, useState } from "react";
import { Wifi, Plus, Loader2, CheckCircle, XCircle, ChevronRight } from "lucide-react";

interface Hotspot {
  id: number;
  name: string;
  location: string;
  ap_mac: string;
  site_name: string;
  is_active: boolean;
  connections_count: number;
  revenue_usd: string;
  created_at: string;
}

interface ProvisionResult {
  success: boolean;
  hotspot_id: number;
  ap_mac: string;
  portal_url: string;
  setup_instructions: string[];
  omada_configured: boolean;
}

export default function HotspotsPage() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [provisionResult, setProvisionResult] = useState<ProvisionResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    ap_mac: "",
    hotspot_name: "",
    location: "",
    site_name: "Default",
  });

  const fetchHotspots = async () => {
    const token = localStorage.getItem("saas_token");
    if (!token) return;
    try {
      const res = await fetch("/api/dashboard/hotspots", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load");
      setHotspots(await res.json());
    } catch {
      setError("無法載入站點資料");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHotspots();
  }, []);

  const handleProvision = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    const token = localStorage.getItem("saas_token");
    try {
      const res = await fetch("/api/dashboard/provision", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "佈建失敗");
      setProvisionResult(data);
      setShowForm(false);
      fetchHotspots();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "未知錯誤");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">站點管理</h1>
          <p className="text-gray-500 mt-1">管理你的 WiFi 存取點</p>
        </div>
        <button
          onClick={() => { setShowForm(true); setProvisionResult(null); setError(""); }}
          className="flex items-center gap-2 bg-[#1B4F8A] text-white font-semibold px-4 py-2 rounded-xl hover:bg-[#2563EB] transition-colors"
        >
          <Plus size={18} />
          新增站點
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
          {error}
        </div>
      )}

      {/* Provision Result */}
      {provisionResult && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="text-green-600" size={20} />
            <h3 className="font-semibold text-green-800">站點已成功登錄！</h3>
          </div>
          <p className="text-sm text-green-700 mb-3">
            AP MAC：<code className="bg-green-100 px-1 rounded">{provisionResult.ap_mac}</code>
            {" "}— Portal URL：<code className="bg-green-100 px-1 rounded text-xs">{provisionResult.portal_url}</code>
          </p>
          <h4 className="font-medium text-green-800 mb-2 text-sm">設定步驟：</h4>
          <ol className="space-y-1">
            {provisionResult.setup_instructions.map((step, i) => (
              <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                <ChevronRight size={14} className="mt-0.5 flex-shrink-0" />
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Add Hotspot Form */}
      {showForm && (
        <div className="mb-6 bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-gray-800 mb-4">新增站點</h3>
          <form onSubmit={handleProvision} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  EAP / AP MAC 位址 *
                </label>
                <input
                  type="text"
                  placeholder="AA:BB:CC:DD:EE:FF"
                  value={form.ap_mac}
                  onChange={(e) => setForm({ ...form, ap_mac: e.target.value })}
                  required
                  pattern="^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$"
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1B4F8A] focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  站點名稱 *
                </label>
                <input
                  type="text"
                  placeholder="我的咖啡廳"
                  value={form.hotspot_name}
                  onChange={(e) => setForm({ ...form, hotspot_name: e.target.value })}
                  required
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1B4F8A] focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  地點 *
                </label>
                <input
                  type="text"
                  placeholder="123 Main St, Manila"
                  value={form.location}
                  onChange={(e) => setForm({ ...form, location: e.target.value })}
                  required
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1B4F8A] focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Omada 站點名稱
                </label>
                <input
                  type="text"
                  placeholder="Default"
                  value={form.site_name}
                  onChange={(e) => setForm({ ...form, site_name: e.target.value })}
                  className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1B4F8A] focus:border-transparent"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-2 bg-[#1B4F8A] text-white font-semibold px-5 py-2.5 rounded-xl hover:bg-[#2563EB] disabled:opacity-60 transition-colors"
              >
                {submitting ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                登錄並取得設定教學
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-5 py-2.5 rounded-xl border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Hotspots List */}
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="animate-spin text-[#1B4F8A]" size={28} />
        </div>
      ) : hotspots.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-gray-100">
          <Wifi className="mx-auto text-gray-300" size={48} />
          <p className="mt-3 text-gray-500">尚無站點。</p>
          <p className="text-sm text-gray-400 mt-1">點擊「新增站點」開始使用。</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {hotspots.map((hs) => (
            <div key={hs.id} className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${hs.is_active ? "bg-green-500" : "bg-gray-300"}`} />
                  <h3 className="font-semibold text-gray-900">{hs.name}</h3>
                </div>
                {hs.is_active ? (
                  <CheckCircle size={16} className="text-green-500 flex-shrink-0" />
                ) : (
                  <XCircle size={16} className="text-gray-400 flex-shrink-0" />
                )}
              </div>
              <p className="text-sm text-gray-500 mb-3">{hs.location}</p>
              <p className="text-xs font-mono text-gray-400 bg-gray-50 px-2 py-1 rounded-lg mb-3">
                {hs.ap_mac}
              </p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-gray-400 text-xs">連線次數（30天）</p>
                  <p className="font-semibold text-gray-800 mt-0.5">{hs.connections_count.toLocaleString()}</p>
                </div>
                <div className="bg-emerald-50 rounded-xl p-3">
                  <p className="text-gray-400 text-xs">收入（30天）</p>
                  <p className="font-semibold text-emerald-700 mt-0.5">${parseFloat(hs.revenue_usd).toFixed(4)}</p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                  hs.is_active
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-500"
                }`}>
                  {hs.is_active ? "運作中" : "已停用"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
