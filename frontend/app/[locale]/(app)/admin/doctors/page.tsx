"use client";

import { motion } from "framer-motion";
import { Ban, CheckCircle, Stethoscope, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { adminApi, type PendingDoctor } from "@/lib/api/admin";

export default function AdminDoctorsPage() {
  const t = useTranslations("admin.doctors");
  const [doctors, setDoctors] = useState<PendingDoctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.getPendingDoctors();
    if (res.data) setDoctors(res.data.items);
    setLoading(false);
  }, []);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [load]);

  const handleApprove = async (doctorId: string) => {
    const res = await adminApi.approveDoctor(doctorId);
    if (res.data?.approved) {
      setMessage(t("approved"));
      load();
    }
  };

  const handleReject = async () => {
    if (!rejectId) return;
    await adminApi.rejectDoctor(rejectId, rejectReason);
    setMessage(t("rejected"));
    setRejectId(null);
    setRejectReason("");
    load();
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

      {message && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">
          {message}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : doctors.length === 0 ? (
        <Card>
          <CardContent className="py-20 text-center">
            <Stethoscope className="mx-auto h-12 w-12 text-ink-4" />
            <h3 className="mt-4 text-lg font-semibold text-ink-2">{t("empty")}</h3>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {doctors.map((d) => (
            <Card key={d.id} className="overflow-hidden">
              <CardContent className="p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-semibold text-foreground">{d.license_number}</p>
                    <p className="text-sm text-muted-foreground">{d.specialty}</p>
                    <p className="mt-1 text-xs text-ink-4">ID: {d.user_id}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleApprove(d.id)}
                      className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700 transition-colors hover:bg-emerald-100 dark:bg-emerald-950 dark:text-emerald-300 dark:hover:bg-emerald-900"
                    >
                      <CheckCircle className="h-4 w-4" />
                      {t("approve")}
                    </button>
                    <button
                      onClick={() => setRejectId(d.id)}
                      className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-100 dark:bg-red-950 dark:text-red-300 dark:hover:bg-red-900"
                    >
                      <Ban className="h-4 w-4" />
                      {t("reject")}
                    </button>
                  </div>
                </div>

                {rejectId === d.id && (
                  <div className="mt-4 flex items-end gap-3 rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950">
                    <div className="flex-1">
                      <label className="mb-1 block text-xs font-semibold text-red-700 dark:text-red-300">{t("reason")}</label>
                      <input
                        type="text"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder={t("reasonPlaceholder")}
                        className="w-full rounded-xl border border-red-300 bg-white px-3 py-2 text-sm dark:bg-slate-900"
                      />
                    </div>
                    <button
                      onClick={handleReject}
                      className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
                    >
                      {t("reject")}
                    </button>
                    <button
                      onClick={() => { setRejectId(null); setRejectReason(""); }}
                      className="rounded-xl p-2 text-ink-4 hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </motion.div>
  );
}
