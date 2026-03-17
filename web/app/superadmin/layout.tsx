"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Wifi,
  DollarSign,
  CreditCard,
  ShieldCheck,
  LogOut,
  Menu,
  X,
  AlertTriangle,
  Megaphone,
  MapPin,
} from "lucide-react";
import { ToastContainer } from "../components/Toast";

// Store superadmin credentials in localStorage (Base64 encoded)
export function getSuperAdminAuth(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("superadmin_auth");
}

export function setSuperAdminAuth(username: string, password: string) {
  const creds = btoa(`${username}:${password}`);
  localStorage.setItem("superadmin_auth", creds);
}

export function clearSuperAdminAuth() {
  localStorage.removeItem("superadmin_auth");
}

export async function superadminFetch(url: string, options: RequestInit = {}) {
  const auth = getSuperAdminAuth();
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: auth ? `Basic ${auth}` : "",
      "Content-Type": "application/json",
    },
  });
}

export default function SuperAdminLayout({ children }: { children: React.ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const auth = getSuperAdminAuth();
    if (auth) setIsLoggedIn(true);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError("");
    setSuperAdminAuth(loginUsername, loginPassword);
    try {
      const res = await superadminFetch("/api/superadmin/stats");
      if (res.status === 401) {
        clearSuperAdminAuth();
        setLoginError("帳號或密碼錯誤");
        return;
      }
      setIsLoggedIn(true);
    } catch {
      clearSuperAdminAuth();
      setLoginError("連線失敗，請稍後再試");
    }
  };

  const handleLogout = () => {
    clearSuperAdminAuth();
    setIsLoggedIn(false);
    setLoginUsername("");
    setLoginPassword("");
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-gray-950">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 bg-amber-500 rounded-2xl mb-4">
              <ShieldCheck size={24} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">超級管理員</h1>
            <p className="text-gray-400 mt-1 text-sm">平台控制後台</p>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">
            {loginError && (
              <div className="mb-4 flex items-center gap-2 bg-red-900/30 border border-red-800 text-red-400 rounded-xl p-3 text-sm">
                <AlertTriangle size={16} className="shrink-0" />
                {loginError}
              </div>
            )}
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">帳號</label>
                <input
                  type="text"
                  required
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/40 focus:border-amber-500 transition-all"
                  placeholder="admin"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">密碼</label>
                <input
                  type="password"
                  required
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/40 focus:border-amber-500 transition-all"
                  placeholder="••••••••"
                />
              </div>
              <button
                type="submit"
                className="w-full bg-amber-500 hover:bg-amber-400 text-gray-900 font-semibold py-3 rounded-xl transition-colors text-sm"
              >
                登入控制後台
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  const navItems = [
    { href: "/superadmin", label: "總覽", icon: LayoutDashboard },
    { href: "/superadmin/users", label: "用戶管理", icon: Users },
    { href: "/superadmin/sites", label: "站點管理", icon: MapPin },
    { href: "/superadmin/hotspots", label: "熱點列表", icon: Wifi },
    { href: "/superadmin/ads", label: "廣告管理", icon: Megaphone },
    { href: "/superadmin/revenue", label: "收入分析", icon: DollarSign },
    { href: "/superadmin/plans", label: "方案管理", icon: CreditCard },
  ];

  return (
    <div className="min-h-screen flex bg-gray-950">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 border-r border-gray-800 transform transition-transform duration-200
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0 lg:static lg:inset-0`}
      >
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <ShieldCheck size={20} className="text-amber-400" />
            <div>
              <p className="font-bold text-white text-sm">超級管理員</p>
              <p className="text-xs text-gray-500">平台控制</p>
            </div>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-500 hover:text-white">
            <X size={20} />
          </button>
        </div>

        <nav className="mt-4 px-3 space-y-0.5">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all
                  ${isActive
                    ? "bg-amber-500/15 text-amber-400 border border-amber-500/20"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                  }`}
              >
                <Icon size={17} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-800">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors w-full px-3 py-2 rounded-xl hover:bg-gray-800"
          >
            <LogOut size={16} />
            登出
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden flex items-center h-14 px-4 bg-gray-900 border-b border-gray-800">
          <button onClick={() => setSidebarOpen(true)} className="p-2 text-gray-400 hover:text-white">
            <Menu size={20} />
          </button>
          <span className="ml-3 text-sm font-semibold text-amber-400 flex items-center gap-1.5">
            <ShieldCheck size={16} /> 超級管理員
          </span>
        </header>

        <main className="flex-1 p-6 lg:p-8 overflow-auto">{children}</main>
      </div>

      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      <ToastContainer />
    </div>
  );
}
