"use client";

import { useEffect, useState } from "react";
import { Loader2, Plus, CreditCard, Users } from "lucide-react";
import { superadminFetch } from "../layout";
import { toast } from "../../components/Toast";

interface Plan {
  name: string;
  monthly_fee_usd: string;
  revenue_share_pct: string;
  max_hotspots: number;
  description: string | null;
  active_subscribers: number;
}

export default function SuperAdminPlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form state
  const [formName, setFormName] = useState("");
  const [formFee, setFormFee] = useState("");
  const [formShare, setFormShare] = useState("70");
  const [formHotspots, setFormHotspots] = useState("1");
  const [formDesc, setFormDesc] = useState("");

  const fetchPlans = async () => {
    try {
      const res = await superadminFetch("/api/superadmin/plans");
      if (!res.ok) throw new Error("Failed to load");
      setPlans(await res.json());
    } catch {
      toast("error", "Failed to load plans");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPlans(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName || !formFee || !formShare || !formHotspots) {
      toast("error", "Please fill all required fields");
      return;
    }
    setSaving(true);
    try {
      const res = await superadminFetch("/api/superadmin/plans", {
        method: "POST",
        body: JSON.stringify({
          name: formName.toLowerCase().replace(/\s+/g, "-"),
          monthly_fee_usd: parseFloat(formFee),
          revenue_share_pct: parseFloat(formShare),
          max_hotspots: parseInt(formHotspots),
          description: formDesc || null,
        }),
      });
      if (!res.ok) throw new Error("Failed to create plan");
      toast("success", "Plan saved!");
      setShowForm(false);
      setFormName(""); setFormFee(""); setFormShare("70"); setFormHotspots("1"); setFormDesc("");
      await fetchPlans();
    } catch {
      toast("error", "Failed to save plan");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Subscription Plans</h1>
          <p className="text-gray-500 text-sm mt-0.5">Manage platform pricing tiers</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-gray-900 text-sm font-semibold rounded-xl transition-colors"
        >
          <Plus size={16} />
          New Plan
        </button>
      </div>

      {/* New Plan Form */}
      {showForm && (
        <div className="bg-gray-900 border border-amber-500/30 rounded-2xl p-6 mb-6">
          <h2 className="font-semibold text-white mb-4">Create / Update Plan</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Plan Name *</label>
              <input
                type="text"
                required
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. pro"
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/40"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Monthly Fee (USD) *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                required
                value={formFee}
                onChange={(e) => setFormFee(e.target.value)}
                placeholder="29.99"
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/40"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Revenue Share % *</label>
              <input
                type="number"
                step="1"
                min="0"
                max="100"
                required
                value={formShare}
                onChange={(e) => setFormShare(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/40"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Max Hotspots *</label>
              <input
                type="number"
                min="1"
                required
                value={formHotspots}
                onChange={(e) => setFormHotspots(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/40"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-400 mb-1">Description</label>
              <input
                type="text"
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                placeholder="Optional description..."
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/40"
              />
            </div>
            <div className="col-span-2 flex gap-3">
              <button
                type="submit"
                disabled={saving}
                className="px-5 py-2 bg-amber-500 hover:bg-amber-400 text-gray-900 text-sm font-semibold rounded-xl disabled:opacity-60 flex items-center gap-2"
              >
                {saving ? <Loader2 size={15} className="animate-spin" /> : null}
                Save Plan
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-5 py-2 bg-gray-800 text-gray-400 hover:text-white text-sm font-medium rounded-xl"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="animate-spin text-amber-400" size={28} />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map((plan) => (
            <div key={plan.name} className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-2 rounded-xl bg-amber-500/15">
                  <CreditCard size={16} className="text-amber-400" />
                </div>
                <h3 className="font-bold text-white capitalize">{plan.name}</h3>
              </div>

              <p className="text-2xl font-bold text-amber-400 mb-1">
                ${parseFloat(plan.monthly_fee_usd).toFixed(2)}
                <span className="text-sm font-normal text-gray-500">/mo</span>
              </p>

              <div className="space-y-1.5 text-sm mt-3 mb-4">
                <div className="flex justify-between">
                  <span className="text-gray-500">Hotspots</span>
                  <span className="text-white font-medium">{plan.max_hotspots}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Revenue share</span>
                  <span className="text-emerald-400 font-medium">{plan.revenue_share_pct}%</span>
                </div>
              </div>

              {plan.description && (
                <p className="text-xs text-gray-500 mb-3">{plan.description}</p>
              )}

              <div className="flex items-center gap-1.5 text-xs text-gray-500 pt-3 border-t border-gray-800">
                <Users size={12} />
                <span>{plan.active_subscribers} active subscriber{plan.active_subscribers !== 1 ? "s" : ""}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
