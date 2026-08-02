"use client";

import { motion } from "framer-motion";
import { Ban, CheckCircle, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { adminApi, type AdminUser } from "@/lib/api/admin";

const PAGE_SIZE = 20;

export default function AdminUsersPage() {
  const t = useTranslations("admin.users");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [roleFilter, setRoleFilter] = useState("");

  const load = useCallback(async (p: number) => {
    setLoading(true);
    const res = await adminApi.listUsers({ role: roleFilter || undefined, search: search || undefined, page: p });
    if (res.data) {
      setUsers(res.data.items);
      setTotal(res.data.total);
    }
    setLoading(false);
  }, [roleFilter, search]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(page); }, [page, load]);

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const handleToggleActive = async (userId: string, current: boolean) => {
    await adminApi.updateUser(userId, { is_active: !current });
    load(page);
  };

  const handleChangeRole = async (userId: string, newRole: string) => {
    await adminApi.updateUser(userId, { role: newRole });
    load(page);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 p-6"
    >
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground sm:text-3xl">{t("title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="flex flex-1 items-center gap-2 rounded-2xl border border-line bg-white px-4 py-2.5 dark:bg-slate-900">
          <Search className="h-4 w-4 text-ink-4" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder={t("search")}
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-ink-4"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          className="rounded-2xl border border-line bg-white px-4 py-2.5 text-sm text-foreground dark:bg-slate-900"
        >
          <option value="">{t("allRoles")}</option>
          <option value="patient">Patient</option>
          <option value="doctor">Doctor</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="h-6 w-6 animate-spin rounded-full border-3 border-primary border-t-transparent" />
            </div>
          ) : users.length === 0 ? (
            <div className="py-20 text-center text-sm text-ink-3">No users found</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs font-semibold uppercase tracking-wide text-ink-3">
                    <th className="px-5 py-3">Name</th>
                    <th className="px-5 py-3">Email</th>
                    <th className="px-5 py-3">Role</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-line last:border-0 hover:bg-slate-50 dark:hover:bg-slate-900/50">
                      <td className="px-5 py-3.5 font-medium text-foreground">{u.full_name}</td>
                      <td className="px-5 py-3.5 text-ink-3">{u.email}</td>
                      <td className="px-5 py-3.5">
                        <select
                          value={u.role}
                          onChange={(e) => handleChangeRole(u.id, e.target.value)}
                          className="rounded-lg border border-line bg-transparent px-2 py-1 text-xs font-medium"
                        >
                          <option value="patient">Patient</option>
                          <option value="doctor">Doctor</option>
                          <option value="admin">Admin</option>
                        </select>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          {u.is_active ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                              <CheckCircle className="h-3 w-3" /> Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-950 dark:text-red-300">
                              <Ban className="h-3 w-3" /> Inactive
                            </span>
                          )}
                          {u.is_email_verified ? null : (
                            <span className="rounded-full bg-orange-50 px-2 py-0.5 text-[10px] font-medium text-orange-700 dark:bg-orange-950 dark:text-orange-300">
                              Unverified
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <button
                          onClick={() => handleToggleActive(u.id, u.is_active)}
                          className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                        >
                          {u.is_active ? t("deactivate") : t("activate")}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-center gap-2">
          <button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            className="rounded-full bg-base-2 px-4 py-2 text-sm font-medium text-ink-3 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-ink-4">
            {page} / {Math.ceil(total / PAGE_SIZE)}
          </span>
          <button
            disabled={page * PAGE_SIZE >= total}
            onClick={() => setPage(page + 1)}
            className="rounded-full bg-base-2 px-4 py-2 text-sm font-medium text-ink-3 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </motion.div>
  );
}
