"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { Loader2, Eye, EyeOff, Wifi, TrendingUp, Users } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [leaving, setLeaving] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "登入失敗");

      localStorage.setItem("saas_token", data.access_token);
      localStorage.setItem("saas_user_name", data.full_name);
      localStorage.setItem("saas_org_name", data.org_name || "");

      // 登入成功動畫：卡片往上滑出
      setLeaving(true);
      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 320);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "登入失敗");
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex"
      style={{ background: "var(--color-warm-white)" }}
    >
      {/* ─── 左側品牌視覺（桌面版） ─── */}
      <div
        className="hidden lg:flex flex-col justify-between w-[45%] p-12 relative overflow-hidden"
        style={{ background: "var(--color-brand-green)" }}
      >
        {/* 裝飾圓圈 */}
        <div className="absolute -top-24 -left-24 w-72 h-72 bg-white/5 rounded-full" />
        <div className="absolute -bottom-32 -right-16 w-96 h-96 bg-white/5 rounded-full" />
        <div className="absolute top-1/2 -right-20 w-60 h-60 bg-white/5 rounded-full" />

        {/* Logo */}
        <div className="relative">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-9 h-9 bg-white/20 rounded-xl flex items-center justify-center">
              <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5 text-white" stroke="currentColor" strokeWidth="2">
                <path d="M1.5 8.5C5.5 4.5 18.5 4.5 22.5 8.5" strokeLinecap="round"/>
                <path d="M5 12C7.5 9.5 16.5 9.5 19 12" strokeLinecap="round"/>
                <path d="M8.5 15.5C10 14 14 14 15.5 15.5" strokeLinecap="round"/>
                <circle cx="12" cy="19" r="1.5" fill="currentColor"/>
              </svg>
            </div>
            <span className="text-white font-bold text-xl" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>
              AbotKamay WiFi
            </span>
          </div>
        </div>

        {/* 中段品牌文案 */}
        <div className="relative space-y-8">
          <div>
            <h2 className="text-4xl font-bold text-white leading-tight mb-4" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>
              讓免費 WiFi<br />成為收益來源
            </h2>
            <p className="text-white/70 text-base leading-relaxed">
              用戶連接 WiFi，觀看短片廣告，你獲得收益。<br />
              簡單、透明、自動化。
            </p>
          </div>

          <div className="space-y-4">
            {[
              { icon: Wifi, text: "一台 OC200 即可啟動" },
              { icon: TrendingUp, text: "每月自動結算收益" },
              { icon: Users, text: "70% 廣告收益直接歸你" },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3">
                <div className="w-8 h-8 bg-white/15 rounded-lg flex items-center justify-center shrink-0">
                  <Icon size={16} className="text-white" />
                </div>
                <span className="text-white/90 text-sm font-medium">{text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 底部 */}
        <div className="relative">
          <p className="text-white/40 text-xs">© 2025 AbotKamay WiFi · 菲律賓免費 WiFi 平台</p>
        </div>
      </div>

      {/* ─── 右側登入表單 ─── */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 relative">
        {/* 背景裝飾（手機版也有） */}
        <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-gradient-to-bl from-[#1B4F8A]/[0.05] to-transparent rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[200px] h-[200px] bg-gradient-to-tr from-[#F58220]/[0.05] to-transparent rounded-full blur-3xl pointer-events-none" />

        <div
          ref={cardRef}
          className={`w-full max-w-md relative ${leaving ? "animate-slide-out" : "animate-slide-up"}`}
        >
          {/* 手機版 Logo */}
          <div className="lg:hidden text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-4" style={{ background: "var(--color-brand-green)" }}>
              <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7 text-white" stroke="currentColor" strokeWidth="2">
                <path d="M1.5 8.5C5.5 4.5 18.5 4.5 22.5 8.5" strokeLinecap="round"/>
                <path d="M5 12C7.5 9.5 16.5 9.5 19 12" strokeLinecap="round"/>
                <path d="M8.5 15.5C10 14 14 14 15.5 15.5" strokeLinecap="round"/>
                <circle cx="12" cy="19" r="1.5" fill="currentColor"/>
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>
              AbotKamay WiFi
            </h1>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>
              歡迎回來
            </h2>
            <p className="text-gray-500 mt-1 text-sm">登入你的帳號，查看你的收益</p>
          </div>

          <div className="glass-card rounded-2xl p-8">
            {error && (
              <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm animate-fade-in">
                {error}
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">電子信箱</label>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-brand w-full border border-gray-200 rounded-xl px-4 py-3 text-sm"
                  placeholder="you@company.com"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-sm font-medium text-gray-700">密碼</label>
                  <Link href="/forgot-password" className="text-xs hover:underline font-medium" style={{ color: "var(--color-brand-green)" }}>
                    忘記密碼？
                  </Link>
                </div>
                <div className="relative">
                  <input
                    type={showPass ? "text" : "password"}
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input-brand w-full border border-gray-200 rounded-xl px-4 py-3 text-sm pr-11"
                    placeholder="你的密碼"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-scale w-full text-white font-semibold py-3 rounded-xl disabled:opacity-60 flex items-center justify-center gap-2"
                style={{ background: "var(--color-brand-green)" }}
              >
                {loading && <Loader2 size={18} className="animate-spin" />}
                {loading ? "登入中..." : "登入"}
              </button>
            </form>

            <div className="mt-5 pt-5 border-t border-gray-100 text-center text-sm text-gray-500">
              還沒有帳號？{" "}
              <Link href="/register" className="font-semibold hover:underline" style={{ color: "var(--color-brand-green)" }}>
                免費註冊
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
