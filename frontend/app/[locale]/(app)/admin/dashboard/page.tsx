"use client";

import { motion } from "framer-motion";
import { Activity, AlertTriangle, Clock, ShieldCheck, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { adminApi, type DashboardStats } from "@/lib/api/admin";

export default function AdminDashboardPage() {
  const t = useTranslations("admin.dashboard");
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const res = await adminApi.getDashboard();
    if (res.data) setStats(res.data);
    setLoading(false);
  }, []);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const cards = [
    { label: t("totalUsers"), value: stats?.total_users ?? 0, icon: Users, color: "text-blue-600 bg-blue-50 dark:bg-blue-950" },
    { label: t("activeToday"), value: stats?.active_today ?? 0, icon: Activity, color: "text-emerald-600 bg-emerald-50 dark:bg-emerald-950" },
    { label: t("safetyIncidents"), value: stats?.safety_incidents_this_week ?? 0, icon: AlertTriangle, color: stats?.safety_incidents_this_week ? "text-red-600 bg-red-50 dark:bg-red-950" : "text-slate-600 bg-slate-50 dark:bg-slate-900" },
    { label: t("pendingDoctors"), value: stats?.pending_doctors ?? 0, icon: Clock, color: stats?.pending_doctors ? "text-orange-600 bg-orange-50 dark:bg-orange-950" : "text-slate-600 bg-slate-50 dark:bg-slate-900" },
  ];

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

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="overflow-hidden">
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{label}</p>
                  <p className="mt-1 font-display text-3xl font-bold text-foreground">{value.toLocaleString()}</p>
                </div>
                <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${color}`}>
                  <Icon className="h-5 w-5" />
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* System health */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-emerald-600" />
            {t("systemHealth")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-950">
            <span className="flex h-3 w-3 rounded-full bg-emerald-500" />
            <span className="text-sm font-medium text-emerald-700 dark:text-emerald-300">{t("healthy")}</span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
