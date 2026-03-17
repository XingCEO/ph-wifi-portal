"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, Eye, EyeOff, CheckCircle } from "lucide-react";

export default function RegisterPage() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    org_name: "",
    org_slug: "",
  });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleOrgNameChange = (name: string) => {
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .slice(0, 40);
    setForm({ ...form, org_name: name, org_slug: slug });
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Registration failed");
      }
      localStorage.setItem("saas_token", data.access_token);
      localStorage.setItem("saas_user_name", data.full_name);
      localStorage.setItem("saas_org_name", data.org_name || "");
      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 1500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-[#faf8f5] flex items-center justify-center px-4">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <CheckCircle className="text-green-600" size={32} />
          </div>
          <h2 className="text-xl font-bold text-gray-900">Account Created!</h2>
          <p className="text-gray-500 mt-2">Redirecting to your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#faf8f5] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-[#2d6a4f] rounded-2xl mb-4">
            <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7 text-white" stroke="currentColor" strokeWidth="2">
              <path d="M1.5 8.5C5.5 4.5 18.5 4.5 22.5 8.5" strokeLinecap="round"/>
              <path d="M5 12C7.5 9.5 16.5 9.5 19 12" strokeLinecap="round"/>
              <path d="M8.5 15.5C10 14 14 14 15.5 15.5" strokeLinecap="round"/>
              <circle cx="12" cy="19" r="1.5" fill="currentColor"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Create Your Account</h1>
          <p className="text-gray-500 mt-1 text-sm">Start earning from your WiFi today</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
              <input
                type="text"
                required
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f] focus:border-transparent"
                placeholder="Juan dela Cruz"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f] focus:border-transparent"
                placeholder="you@company.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password * (min 8 chars)</label>
              <div className="relative">
                <input
                  type={showPass ? "text" : "password"}
                  required
                  minLength={8}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f] focus:border-transparent pr-11"
                  placeholder="Min 8 characters"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div className="pt-2 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Your Organization</p>

              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Name *</label>
                  <input
                    type="text"
                    required
                    value={form.org_name}
                    onChange={(e) => handleOrgNameChange(e.target.value)}
                    className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f] focus:border-transparent"
                    placeholder="My Coffee Shop"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Organization Slug *
                    <span className="ml-1 text-xs text-gray-400 font-normal">(used in URLs)</span>
                  </label>
                  <input
                    type="text"
                    required
                    pattern="^[a-z0-9\-]+$"
                    value={form.org_slug}
                    onChange={(e) => setForm({ ...form, org_slug: e.target.value.toLowerCase() })}
                    className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f] focus:border-transparent font-mono"
                    placeholder="my-coffee-shop"
                  />
                  <p className="mt-1 text-xs text-gray-400">Lowercase letters, numbers, and hyphens only</p>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#2d6a4f] text-white font-semibold py-3 rounded-xl hover:bg-[#40916c] disabled:opacity-60 transition-colors flex items-center justify-center gap-2 mt-2"
            >
              {loading && <Loader2 size={18} className="animate-spin" />}
              {loading ? "Creating account..." : "Create Free Account"}
            </button>

            <p className="text-xs text-center text-gray-400">
              Free plan: 1 hotspot, 70% revenue share. No credit card required.
            </p>
          </form>
        </div>

        <p className="text-center mt-6 text-sm text-gray-500">
          Already have an account?{" "}
          <Link href="/login" className="text-[#2d6a4f] font-semibold hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
