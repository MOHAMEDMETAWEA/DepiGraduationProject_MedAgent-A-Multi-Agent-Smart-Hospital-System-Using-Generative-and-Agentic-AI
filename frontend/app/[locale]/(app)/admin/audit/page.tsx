"use client";

import { motion } from "framer-motion";
import { CheckCircle2, FileText, Search, ShieldAlert, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { adminApi, type AuditLogEntry, type AuditVerifyResult } from "@/lib/api/admin";

const PAGE_SIZE = 50;

export default function AdminAuditPage() {
  const t = useTranslations("admin.audit");
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");
  const [verifyResult, setVerifyResult] = useState<AuditVerifyResult | null>(null);
  const [verifying, setVerifying] = useState(false);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    const res = await adminApi.getAuditLogs({ action: actionFilter || undefined, page: p });
    if (res.data) {
      setLogs(res.data.items);
      setTotal(res.data.total);
    }
    setLoading(false);
  }, [actionFilter]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(page); }, [page, load]);

  const handleVerify = async () => {
    setVerifying(true);
    const res = await adminApi.verifyAuditChain();
    if (res.data) setVerifyResult(res.data);
    setVerifying(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 p-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground sm:text-3xl">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>
        <button
          onClick={handleVerify}
          disabled={verifying}
          className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          <ShieldCheck className="h-4 w-4" />
          {verifying ? t("verifying") : t("verifyChain")}
        </button>
      </div>

      {/* Chain verification result */}
      {verifyResult && (
        <div className={`rounded-2xl border p-4 ${
          verifyResult.ok
            ? "border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950"
            : "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950"
        }`}>
          <div className="flex items-center gap-2">
            {verifyResult.ok ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-red-600" />
            )}
            <span className={`text-sm font-semibold ${verifyResult.ok ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"}`}>
              {verifyResult.ok
                ? `${t("chainOk")} (${verifyResult.last_sequence} records)`
                : `${t("chainBroken")} #${verifyResult.broken_at}`}
            </span>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-2 rounded-2xl border border-line bg-white px-4 py-2.5 dark:bg-slate-900">
        <Search className="h-4 w-4 text-ink-4" />
        <input
          type="text"
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          placeholder={t("filterAction")}
          className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-ink-4"
        />
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="h-6 w-6 animate-spin rounded-full border-3 border-primary border-t-transparent" />
            </div>
          ) : logs.length === 0 ? (
            <div className="py-20 text-center">
              <FileText className="mx-auto h-10 w-10 text-ink-4" />
              <p className="mt-3 text-sm text-ink-3">No audit logs found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs font-semibold uppercase tracking-wide text-ink-3">
                    <th className="px-5 py-3">#</th>
                    <th className="px-5 py-3">Action</th>
                    <th className="px-5 py-3">Resource</th>
                    <th className="px-5 py-3">User ID</th>
                    <th className="px-5 py-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="border-b border-line last:border-0 hover:bg-slate-50 dark:hover:bg-slate-900/50">
                      <td className="px-5 py-3 font-mono text-xs text-ink-3">{log.sequence}</td>
                      <td className="px-5 py-3">
                        <span className="rounded-full bg-base-2 px-2 py-0.5 text-xs font-medium text-ink-2">
                          {log.action}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-ink-3">{log.resource_type || "—"}</td>
                      <td className="px-5 py-3 font-mono text-xs text-ink-4">
                        {log.user_id ? log.user_id.slice(0, 8) + "..." : "system"}
                      </td>
                      <td className="px-5 py-3 text-xs text-ink-4">
                        {new Date(log.created_at).toLocaleString()}
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
