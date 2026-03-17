"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, Search, CheckCircle, XCircle, ChevronLeft, ChevronRight } from "lucide-react";
import { superadminFetch } from "../layout";
import { toast } from "../../components/Toast";

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  organization_id: number | null;
  org_name: string | null;
  org_slug: string | null;
  plan: string | null;
  created_at: string;
}

const PAGE_SIZE = 20;

const PLAN_COLORS: Record<string, string> = {
  free: "bg-gray-700 text-gray-300",
  starter: "bg-blue-900/50 text-blue-400",
  pro: "bg-emerald-900/50 text-emerald-400",
  enterprise: "bg-purple-900/50 text-purple-400",
};

const PLAN_LABELS: Record<string, string> = {
  free: "免費",
  starter: "入門",
  pro: "專業",
  enterprise: "企業",
};

export default function SuperAdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (search) params.set("search", search);
      const res = await superadminFetch(`/api/superadmin/users?${params}`);
      if (!res.ok) throw new Error("Failed to load");
      setUsers(await res.json());
    } catch {
      toast("error", "無法載入用戶資料");
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const handleToggleActive = async (user: User) => {
    setUpdatingId(user.id);
    try {
      const res = await superadminFetch(`/api/superadmin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      if (!res.ok) throw new Error("Update failed");
      const updated: User = await res.json();
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      toast("success", `用戶已${updated.is_active ? "啟用" : "停用"}`);
    } catch {
      toast("error", "更新用戶狀態失敗");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">用戶管理</h1>
          <p className="text-gray-500 text-sm mt-0.5">所有 SaaS 平台用戶</p>
        </div>
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="搜尋電子信箱或姓名..."
              className="bg-gray-800 border border-gray-700 rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-amber-500/40 w-64"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-gray-900 text-sm font-semibold rounded-xl transition-colors"
          >
            搜尋
          </button>
        </form>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <Loader2 className="animate-spin text-amber-400" size={28} />
          </div>
        ) : users.length === 0 ? (
          <div className="text-center text-gray-500 py-16 text-sm">找不到用戶</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-900/60">
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">用戶</th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">所屬組織</th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">方案</th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">狀態</th>
                    <th className="text-left px-5 py-3 text-gray-500 font-medium">加入時間</th>
                    <th className="text-right px-5 py-3 text-gray-500 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-t border-gray-800 hover:bg-gray-800/40 transition-colors">
                      <td className="px-5 py-3.5">
                        <p className="font-medium text-white">{user.full_name}</p>
                        <p className="text-gray-500 text-xs">{user.email}</p>
                      </td>
                      <td className="px-5 py-3.5">
                        {user.org_name ? (
                          <div>
                            <p className="text-white text-xs font-medium">{user.org_name}</p>
                            <p className="text-gray-500 text-xs">{user.org_slug}</p>
                          </div>
                        ) : (
                          <span className="text-gray-600 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5">
                        {user.plan ? (
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${PLAN_COLORS[user.plan] ?? "bg-gray-700 text-gray-300"}`}>
                            {PLAN_LABELS[user.plan] ?? user.plan}
                          </span>
                        ) : <span className="text-gray-600 text-xs">—</span>}
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-1.5">
                          {user.is_active
                            ? <CheckCircle size={14} className="text-emerald-500" />
                            : <XCircle size={14} className="text-red-500" />
                          }
                          <span className={`text-xs ${user.is_active ? "text-emerald-400" : "text-red-400"}`}>
                            {user.is_active ? "啟用中" : "已停用"}
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-gray-500 text-xs">
                        {new Date(user.created_at).toLocaleDateString("zh-TW")}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => handleToggleActive(user)}
                          disabled={updatingId === user.id}
                          className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                            user.is_active
                              ? "bg-red-900/30 text-red-400 hover:bg-red-900/50 border border-red-800"
                              : "bg-emerald-900/30 text-emerald-400 hover:bg-emerald-900/50 border border-emerald-800"
                          } disabled:opacity-50`}
                        >
                          {updatingId === user.id
                            ? <Loader2 size={12} className="animate-spin" />
                            : user.is_active ? "停用" : "啟用"
                          }
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-5 py-3 border-t border-gray-800">
              <p className="text-xs text-gray-500">
                第 {page} 頁 · {users.length} 筆結果
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-white disabled:opacity-40 transition-colors"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={users.length < PAGE_SIZE}
                  className="p-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-white disabled:opacity-40 transition-colors"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
