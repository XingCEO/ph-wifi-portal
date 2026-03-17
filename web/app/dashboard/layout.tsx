"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Wifi,
  DollarSign,
  Settings,
  CreditCard,
  LogOut,
  Menu,
  X,
  BarChart2,
} from "lucide-react";
import { ToastContainer } from "../components/Toast";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [userName, setUserName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const token = localStorage.getItem("saas_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
    setUserName(localStorage.getItem("saas_user_name") || "用戶");
    setOrgName(localStorage.getItem("saas_org_name") || "");
  }, []);

  const handleLogout = () => {
    setLoggingOut(true);
    setTimeout(() => {
      localStorage.removeItem("saas_token");
      localStorage.removeItem("saas_user_name");
      localStorage.removeItem("saas_org_name");
      window.location.href = "/login";
    }, 320);
  };

  const navItems = [
    { href: "/dashboard", label: "總覽", icon: LayoutDashboard },
    { href: "/dashboard/hotspots", label: "站點管理", icon: Wifi },
    { href: "/dashboard/analytics", label: "數據分析", icon: BarChart2 },
    { href: "/dashboard/revenue", label: "收入分析", icon: DollarSign },
    { href: "/dashboard/billing", label: "訂閱與帳單", icon: CreditCard },
    { href: "/dashboard/settings", label: "帳號設定", icon: Settings },
  ];

  return (
    <div
      className={`min-h-screen flex transition-opacity duration-300 ${loggingOut ? "opacity-0" : "opacity-100"}`}
      style={{ background: "var(--color-warm-white)" }}
    >
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200 ease-in-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0 lg:static lg:inset-0`}
        style={{ background: "#1B4F8A" }}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-white/20">
          <div>
            <p className="font-bold text-lg text-white" style={{ fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>AbotKamay</p>
            <p className="text-xs text-white/70 truncate max-w-[140px]">{orgName}</p>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-white/70 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Nav */}
        <nav className="mt-6 px-4 space-y-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all
                  ${isActive
                    ? "bg-white/20 text-white shadow-sm"
                    : "text-white/75 hover:bg-white/10 hover:text-white"
                  }`}
              >
                <Icon size={18} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Bottom: user + logout */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-white/20">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate max-w-[140px]">{userName}</p>
              <p className="text-xs text-white/60">擁有者</p>
            </div>
            <button
              onClick={handleLogout}
              title="登出"
              className="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors shrink-0"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar (mobile) */}
        <header className="lg:hidden flex items-center h-16 px-4 bg-white/70 backdrop-blur-xl border-b border-gray-200/50">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <Menu size={20} />
          </button>
          <p className="ml-3 font-semibold" style={{ color: "var(--color-brand-green)", fontFamily: "var(--font-plus-jakarta, sans-serif)" }}>AbotKamay</p>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6 lg:p-8">{children}</main>
      </div>

      {/* Overlay (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <ToastContainer />
    </div>
  );
}
