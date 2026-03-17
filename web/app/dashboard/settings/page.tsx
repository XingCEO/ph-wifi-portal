"use client";

import { useEffect, useState } from "react";
import { Loader2, User, Lock, Save } from "lucide-react";
import { toast } from "../../components/Toast";

interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_verified: boolean;
  created_at: string;
}

function InputField({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  disabled,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f]/30 focus:border-[#2d6a4f] transition-all disabled:bg-gray-50 disabled:text-gray-400"
      />
    </div>
  );
}

const ROLE_LABELS: Record<string, string> = {
  owner: "擁有者",
  admin: "管理員",
  member: "成員",
};

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingPass, setSavingPass] = useState(false);

  // Profile form
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");

  // Password form
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  useEffect(() => {
    const fetchProfile = async () => {
      const token = localStorage.getItem("saas_token");
      if (!token) { window.location.href = "/login"; return; }
      try {
        const res = await fetch("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) throw new Error("Failed to load");
        const data: UserProfile = await res.json();
        setProfile(data);
        setFullName(data.full_name);
        setEmail(data.email);
      } catch {
        toast("error", "無法載入個人資料");
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const token = localStorage.getItem("saas_token");
    try {
      const res = await fetch("/api/auth/profile", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ full_name: fullName, email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "更新失敗");
      setProfile(data);
      localStorage.setItem("saas_user_name", data.full_name);
      toast("success", "個人資料已更新！");
    } catch (err: unknown) {
      toast("error", err instanceof Error ? err.message : "更新失敗");
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast("error", "新密碼不一致");
      return;
    }
    if (newPassword.length < 8) {
      toast("error", "密碼至少需要 8 個字元");
      return;
    }
    setSavingPass(true);
    const token = localStorage.getItem("saas_token");
    try {
      const res = await fetch("/api/auth/profile", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "更改密碼失敗");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast("success", "密碼已成功更改！");
    } catch (err: unknown) {
      toast("error", err instanceof Error ? err.message : "更改密碼失敗");
    } finally {
      setSavingPass(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-[#2d6a4f]" size={32} />
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>
          帳號設定
        </h1>
        <p className="text-gray-500 mt-1 text-sm">管理你的個人資料與安全設定</p>
      </div>

      {/* Profile */}
      <div className="glass-card rounded-2xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2 rounded-xl bg-[#2d6a4f]/10">
            <User size={18} className="text-[#2d6a4f]" />
          </div>
          <h2 className="font-semibold text-gray-800">個人資料</h2>
        </div>

        <form onSubmit={handleSaveProfile} className="space-y-4">
          <InputField
            label="姓名"
            value={fullName}
            onChange={setFullName}
            placeholder="你的姓名"
          />
          <InputField
            label="電子信箱"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="you@company.com"
          />
          <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 rounded-xl p-3">
            <span>角色：</span>
            <span className="font-medium text-gray-700">{ROLE_LABELS[profile?.role ?? ""] ?? profile?.role}</span>
            <span className="ml-2">·</span>
            <span>驗證：</span>
            <span className={`font-medium ${profile?.is_verified ? "text-green-600" : "text-amber-600"}`}>
              {profile?.is_verified ? "已驗證" : "待驗證"}
            </span>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#2d6a4f] text-white text-sm font-semibold rounded-xl hover:bg-[#40916c] disabled:opacity-60 transition-all"
          >
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
            {saving ? "儲存中..." : "儲存變更"}
          </button>
        </form>
      </div>

      {/* Password */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2 rounded-xl bg-amber-50">
            <Lock size={18} className="text-amber-600" />
          </div>
          <h2 className="font-semibold text-gray-800">更改密碼</h2>
        </div>

        <form onSubmit={handleChangePassword} className="space-y-4">
          <InputField
            label="目前密碼"
            type="password"
            value={currentPassword}
            onChange={setCurrentPassword}
            placeholder="你的目前密碼"
          />
          <InputField
            label="新密碼"
            type="password"
            value={newPassword}
            onChange={setNewPassword}
            placeholder="至少 8 個字元"
          />
          <InputField
            label="確認新密碼"
            type="password"
            value={confirmPassword}
            onChange={setConfirmPassword}
            placeholder="再次輸入新密碼"
          />
          <button
            type="submit"
            disabled={savingPass || !currentPassword || !newPassword || !confirmPassword}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-600 text-white text-sm font-semibold rounded-xl hover:bg-amber-700 disabled:opacity-60 transition-all"
          >
            {savingPass ? <Loader2 size={16} className="animate-spin" /> : <Lock size={16} />}
            {savingPass ? "更改中..." : "更改密碼"}
          </button>
        </form>
      </div>
    </div>
  );
}
