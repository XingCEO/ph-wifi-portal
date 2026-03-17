"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Loader2, Lock, Eye, EyeOff, CheckCircle } from "lucide-react";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const t = searchParams.get("token");
    if (t) setToken(t);
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setError("Passwords don't match");
      return;
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Reset failed");
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: "var(--color-warm-white)" }}>
      <div className="absolute top-0 left-0 w-[400px] h-[400px] bg-gradient-to-br from-[#2d6a4f]/[0.04] to-transparent rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-4" style={{ background: "var(--color-brand-green)" }}>
            <Lock size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>
            Reset Password
          </h1>
          <p className="text-gray-500 mt-1 text-sm">Enter your new password below</p>
        </div>

        <div className="glass-card rounded-2xl p-8">
          {success ? (
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-green-100 rounded-xl mb-4">
                <CheckCircle size={24} className="text-green-600" />
              </div>
              <h2 className="font-semibold text-gray-900 mb-2">Password reset!</h2>
              <p className="text-sm text-gray-500 mb-5">Your password has been changed successfully.</p>
              <Link
                href="/login"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-white text-sm font-semibold transition-all hover:bg-[#40916c]"
                style={{ background: "var(--color-brand-green)" }}
              >
                Continue to Login
              </Link>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm">
                  {error}
                </div>
              )}

              {!token && (
                <div className="mb-4 bg-amber-50 border border-amber-200 text-amber-700 rounded-xl p-3 text-sm">
                  No reset token found. Please use the link from your email.
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Reset Token</label>
                  <input
                    type="text"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    required
                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f]/30 focus:border-[#2d6a4f] font-mono"
                    placeholder="Paste your reset token"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">New Password</label>
                  <div className="relative">
                    <input
                      type={showPass ? "text" : "password"}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f]/30 focus:border-[#2d6a4f] pr-11"
                      placeholder="At least 8 characters"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPass(!showPass)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Confirm Password</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2d6a4f]/30 focus:border-[#2d6a4f]"
                    placeholder="Repeat new password"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || !token}
                  className="w-full py-3 rounded-xl text-white font-semibold text-sm disabled:opacity-60 transition-all flex items-center justify-center gap-2 hover:bg-[#40916c]"
                  style={{ background: "var(--color-brand-green)" }}
                >
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <Lock size={16} />}
                  {loading ? "Resetting..." : "Reset Password"}
                </button>
              </form>

              <div className="mt-5 text-center">
                <Link href="/login" className="text-sm text-gray-500 hover:text-gray-700 transition-colors">
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

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
