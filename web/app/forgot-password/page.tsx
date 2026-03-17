"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, ArrowLeft, Mail, CheckCircle } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resetToken, setResetToken] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setResetToken(data.reset_token);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: "var(--color-warm-white)" }}>
      {/* Background accents */}
      <div className="absolute top-0 left-0 w-[400px] h-[400px] bg-gradient-to-br from-[#2d6a4f]/[0.04] to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[300px] h-[300px] bg-gradient-to-tl from-[#e9a319]/[0.04] to-transparent rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-4" style={{ background: "var(--color-brand-green)" }}>
            <svg viewBox="0 0 24 24" fill="none" className="w-7 h-7 text-white" stroke="currentColor" strokeWidth="2">
              <path d="M1.5 8.5C5.5 4.5 18.5 4.5 22.5 8.5" strokeLinecap="round"/>
              <path d="M5 12C7.5 9.5 16.5 9.5 19 12" strokeLinecap="round"/>
              <path d="M8.5 15.5C10 14 14 14 15.5 15.5" strokeLinecap="round"/>
              <circle cx="12" cy="19" r="1.5" fill="currentColor"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>
            Forgot Password
          </h1>
          <p className="text-gray-500 mt-1 text-sm">
            Enter your email and we&apos;ll send a reset link
          </p>
        </div>

        <div className="glass-card rounded-2xl p-8">
          {resetToken ? (
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-green-100 rounded-xl mb-4">
                <CheckCircle size={24} className="text-green-600" />
              </div>
              <h2 className="font-semibold text-gray-900 mb-2">Request sent!</h2>
              <p className="text-sm text-gray-500 mb-6">
                If this email is registered, a reset link has been sent.
              </p>

              {/* Dev mode: show token */}
              {resetToken !== "no-user-found" && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-4 text-left">
                  <p className="text-xs font-semibold text-amber-700 mb-1">🛠 Development Mode — Reset Token:</p>
                  <p className="text-xs font-mono text-amber-800 break-all">{resetToken}</p>
                  <Link
                    href={`/reset-password?token=${resetToken}`}
                    className="mt-2 inline-block text-xs font-semibold text-amber-700 hover:underline"
                  >
                    → Use this token to reset password
                  </Link>
                </div>
              )}

              <Link href="/login" className="inline-flex items-center gap-2 text-sm font-medium text-[#2d6a4f] hover:underline">
                <ArrowLeft size={14} />
                Back to login
              </Link>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Email Address</label>
                  <div className="relative">
                    <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full border border-gray-200 rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f]/30 focus:border-[#2d6a4f] transition-all"
                      placeholder="you@company.com"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 rounded-xl text-white font-semibold text-sm hover:bg-[#40916c] disabled:opacity-60 transition-all flex items-center justify-center gap-2"
                  style={{ background: "var(--color-brand-green)" }}
                >
                  {loading ? <Loader2 size={16} className="animate-spin" /> : null}
                  {loading ? "Sending..." : "Send Reset Link"}
                </button>
              </form>

              <div className="mt-5 text-center">
                <Link href="/login" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                  <ArrowLeft size={14} />
                  Back to login
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
