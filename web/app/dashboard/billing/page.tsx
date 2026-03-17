"use client";

import { useEffect, useState } from "react";
import { Loader2, CreditCard, Zap, CheckCircle } from "lucide-react";
import { toast } from "../../components/Toast";

interface Subscription {
  plan: string;
  status: string;
  monthly_fee_usd: string;
  revenue_share_pct: string;
  max_hotspots: number;
  starts_at: string;
  ends_at: string | null;
}

interface BillingRecord {
  id: number;
  period: string;
  plan: string;
  amount_usd: string;
  status: string;
  created_at: string;
}

const PLANS = [
  { name: "free",       label: "免費",   price: "$0/月",     hotspots: 1,   share: "70%", color: "gray" },
  { name: "starter",    label: "入門",   price: "$9.99/月",  hotspots: 3,   share: "75%", color: "blue" },
  { name: "pro",        label: "專業",   price: "$29.99/月", hotspots: 10,  share: "80%", color: "green", popular: true },
  { name: "enterprise", label: "企業",   price: "$99.99/月", hotspots: 100, share: "85%", color: "purple" },
];

const PLAN_LABELS: Record<string, string> = {
  free: "免費", starter: "入門", pro: "專業", enterprise: "企業",
};

const STATUS_LABELS: Record<string, string> = {
  active: "使用中", inactive: "已停用", paid: "已付款", pending: "待處理",
};

function PlanCard({
  plan,
  current,
  onUpgrade,
  upgrading,
}: {
  plan: typeof PLANS[0];
  current: string;
  onUpgrade: (name: string) => void;
  upgrading: boolean;
}) {
  const isActive = current === plan.name;
  const colorMap: Record<string, string> = {
    gray:   "border-gray-200 bg-white",
    blue:   "border-blue-200 bg-blue-50/30",
    green:  "border-[#2d6a4f]/30 bg-[#2d6a4f]/5",
    purple: "border-purple-200 bg-purple-50/30",
  };
  const btnColorMap: Record<string, string> = {
    gray:   "bg-gray-700 hover:bg-gray-800",
    blue:   "bg-blue-600 hover:bg-blue-700",
    green:  "bg-[#2d6a4f] hover:bg-[#40916c]",
    purple: "bg-purple-700 hover:bg-purple-800",
  };

  return (
    <div className={`card-hover relative rounded-2xl border p-5 transition-all ${colorMap[plan.color]} ${isActive ? "ring-2 ring-[#2d6a4f]" : ""}`}>
      {plan.popular && (
        <span className="absolute -top-2.5 left-4 bg-[#2d6a4f] text-white text-[11px] font-bold px-2.5 py-0.5 rounded-full">
          推薦
        </span>
      )}
      {isActive && (
        <div className="absolute top-3 right-3 flex items-center gap-1 text-[#2d6a4f] text-xs font-semibold">
          <CheckCircle size={14} />
          目前方案
        </div>
      )}
      <p className="font-bold text-gray-900" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>{plan.label}</p>
      <p className="text-2xl font-bold mt-1 mb-3 text-gray-900">{plan.price}</p>
      <ul className="text-sm text-gray-600 space-y-1 mb-4">
        <li>✓ {plan.hotspots} 個站點</li>
        <li>✓ {plan.share} 收益分潤</li>
        <li>✓ 完整數據分析</li>
      </ul>
      <button
        onClick={() => onUpgrade(plan.name)}
        disabled={isActive || upgrading}
        className={`btn-scale w-full py-2 text-sm font-semibold rounded-xl text-white transition-all disabled:opacity-50 disabled:cursor-default ${btnColorMap[plan.color]}`}
      >
        {isActive ? "目前方案" : "升級"}
      </button>
    </div>
  );
}

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [billing, setBilling] = useState<BillingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);

  const fetchData = async () => {
    const token = localStorage.getItem("saas_token");
    if (!token) { window.location.href = "/login"; return; }
    try {
      const [subRes, billRes] = await Promise.all([
        fetch("/api/dashboard/subscription", { headers: { Authorization: `Bearer ${token}` } }),
        fetch("/api/dashboard/billing", { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (subRes.ok) setSubscription(await subRes.json());
      if (billRes.ok) setBilling(await billRes.json());
    } catch {
      toast("error", "無法載入帳單資料");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleUpgrade = async (plan: string) => {
    setUpgrading(true);
    const token = localStorage.getItem("saas_token");
    try {
      const res = await fetch("/api/auth/upgrade", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ plan }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "升級失敗");
      toast("success", `已成功升級至${PLAN_LABELS[plan] ?? plan}方案！`);
      await fetchData();
    } catch (err: unknown) {
      toast("error", err instanceof Error ? err.message : "升級失敗");
    } finally {
      setUpgrading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-[#2d6a4f]" size={32} />
      </div>
    );
  }

  const currentPlan = subscription?.plan || "free";

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>
          訂閱與帳單
        </h1>
        <p className="text-gray-500 mt-1 text-sm">管理你的訂閱方案與付款記錄</p>
      </div>

      {/* Current Plan Banner */}
      {subscription && (
        <div className="glass-card rounded-2xl p-5 mb-6 flex items-center gap-4">
          <div className="p-3 rounded-xl bg-[#2d6a4f]/10">
            <Zap size={20} className="text-[#2d6a4f]" />
          </div>
          <div className="flex-1">
            <p className="font-semibold text-gray-900">{PLAN_LABELS[currentPlan] ?? currentPlan}方案</p>
            <p className="text-sm text-gray-500">
              {subscription.max_hotspots} 個站點 · {subscription.revenue_share_pct}% 收益分潤
              {subscription.monthly_fee_usd !== "0.00" && ` · $${subscription.monthly_fee_usd}/月`}
            </p>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700">
            {STATUS_LABELS[subscription.status] ?? subscription.status}
          </span>
        </div>
      )}

      {/* Plan Selection */}
      <h2 className="font-semibold text-gray-800 mb-3">選擇方案</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        {PLANS.map((plan) => (
          <PlanCard
            key={plan.name}
            plan={plan}
            current={currentPlan}
            onUpgrade={handleUpgrade}
            upgrading={upgrading}
          />
        ))}
      </div>

      {/* Billing History */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
          <CreditCard size={18} className="text-gray-500" />
          <h2 className="font-semibold text-gray-800">付款記錄</h2>
        </div>
        {billing.length === 0 ? (
          <div className="px-5 py-10 text-center text-gray-400 text-sm">
            尚無付款記錄
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50/50">
                <th className="text-left px-5 py-3 text-gray-500 font-medium">期間</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">方案</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">金額</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">狀態</th>
              </tr>
            </thead>
            <tbody>
              {billing.map((b) => (
                <tr key={b.id} className="border-t border-gray-100 hover:bg-gray-50/50 transition-colors">
                  <td className="px-5 py-3 text-gray-700">{b.period}</td>
                  <td className="px-5 py-3 text-gray-700">{PLAN_LABELS[b.plan] ?? b.plan}</td>
                  <td className="px-5 py-3 text-gray-700">${b.amount_usd}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      b.status === "paid" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
                    }`}>
                      {STATUS_LABELS[b.status] ?? b.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
