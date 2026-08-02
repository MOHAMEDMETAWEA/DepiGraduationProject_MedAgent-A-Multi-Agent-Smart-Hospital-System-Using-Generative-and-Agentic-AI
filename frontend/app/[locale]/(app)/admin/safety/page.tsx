"use client";

import { motion } from "framer-motion";
import { AlertTriangle, BarChart3, MessageSquareWarning, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { adminApi, type SafetyIncident, type SafetyStats } from "@/lib/api/admin";
import { useRouter } from "@/src/i18n/navigation";

const triageColors: Record<string, string> = {
  emergency: "bg-red-100 text-red-700",
  urgent: "bg-orange-100 text-orange-700",
  routine: "bg-emerald-100 text-emerald-700",
};

export default function AdminSafetyPage() {
  const t = useTranslations("admin.safety");
  const router = useRouter();
  const [incidents, setIncidents] = useState<SafetyIncident[]>([]);
  const [stats, setStats] = useState<SafetyStats | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [incRes, statsRes] = await Promise.all([
      adminApi.getSafetyIncidents(),
      adminApi.getSafetyStats(),
    ]);
    if (incRes.data) setIncidents(incRes.data.items);
    if (statsRes.data) setStats(statsRes.data);
    setLoading(false);
  }, []);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [load]);

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
        <button onClick={load} className="rounded-full p-2 hover:bg-slate-100 dark:hover:bg-slate-800">
          <RefreshCw className="h-4 w-4 text-ink-3" />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : (
        <>
          {/* Stats grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">{t("hallucinationRate")}</p>
                <p className="mt-1 font-display text-2xl font-bold text-foreground">
                  {stats?.hallucination_rate != null ? `${(stats.hallucination_rate * 100).toFixed(1)}%` : "—"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">{t("citationRate")}</p>
                <p className="mt-1 font-display text-2xl font-bold text-foreground">
                  {stats?.citation_rate != null ? `${(stats.citation_rate * 100).toFixed(1)}%` : "—"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">{t("triageInconsistencies")}</p>
                <p className="mt-1 font-display text-2xl font-bold text-foreground">
                  {stats?.triage_inconsistencies ?? "—"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground">{t("rewrites")}</p>
                <p className="mt-1 font-display text-2xl font-bold text-foreground">
                  {stats?.forbidden_phrase_rewrites_total ?? "—"}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Uncertainty distribution */}
          {stats?.uncertainty_distribution && Object.keys(stats.uncertainty_distribution).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  {t("uncertainty")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                  {Object.entries(stats.uncertainty_distribution).map(([band, count]) => (
                    <div key={band} className="flex items-center gap-2">
                      <span className={`inline-block h-3 w-3 rounded-full ${
                        band === "high" ? "bg-red-500" : band === "medium" ? "bg-orange-500" : "bg-emerald-500"
                      }`} />
                      <span className="text-sm capitalize text-ink-2">{band}</span>
                      <span className="text-sm font-semibold text-foreground">{count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Flagged conversations */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500" />
                {t("flaggedConversations")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {incidents.length === 0 ? (
                <div className="py-10 text-center">
                  <MessageSquareWarning className="mx-auto h-10 w-10 text-ink-4" />
                  <p className="mt-3 text-sm text-ink-3">{t("noFlagged")}</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {incidents.map((inc) => (
                    <button
                      key={inc.id}
                      onClick={() => router.push(`/chat/${inc.id}`)}
                      className="flex w-full items-center justify-between rounded-xl border border-line p-4 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-900/50"
                    >
                      <div>
                        <p className="font-medium text-foreground">{inc.title || "Untitled"}</p>
                        <p className="mt-0.5 text-xs text-ink-4">
                          {new Date(inc.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      {inc.triage_level && (
                        <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${triageColors[inc.triage_level] || "bg-slate-100 text-slate-600"}`}>
                          {inc.triage_level}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </motion.div>
  );
}
