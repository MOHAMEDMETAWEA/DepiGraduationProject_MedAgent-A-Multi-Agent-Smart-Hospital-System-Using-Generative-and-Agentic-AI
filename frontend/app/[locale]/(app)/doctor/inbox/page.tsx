"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Calendar,
  ClipboardList,
  Download,
  Eye,
  FilterX,
  Search,
  User,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { apiRequest } from "@/lib/api/client";
import { extractChiefComplaint } from "@/lib/handoff/markdown";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "@/src/i18n/navigation";

type HandoffStatus = "new" | "acknowledged" | "in_progress" | "reviewed" | "closed";

type Handoff = {
  id: string;
  conversation_id: string;
  patient_user_id: string;
  patient_name: string | null;
  status: HandoffStatus;
  priority: number;
  target_specialty: string | null;
  target_language: string | null;
  auto_routed: boolean;
  sent_at: string | null;
  acknowledged_at: string | null;
  reviewed_at: string | null;
  closed_at: string | null;
  doctor_private_notes: string | null;
  summary_markdown: string;
  created_at: string;
};

type InboxCounts = {
  new: number;
  acknowledged: number;
  in_progress: number;
  reviewed: number;
  closed: number;
  total: number;
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const TAB_KEYS = ["all", "new", "acknowledged", "in_progress", "reviewed", "closed"] as const;
type TabKey = (typeof TAB_KEYS)[number];

type TriageLevel = "emergency" | "urgent" | "routine";

const PRIORITY_TO_TRIAGE: Record<number, TriageLevel> = {
  100: "emergency",
  70: "urgent",
  30: "routine",
};

const TRIAGE_BAR: Record<TriageLevel, string> = {
  emergency: "bg-[var(--emergency)]",
  urgent: "bg-[var(--urgent)]",
  routine: "bg-[var(--routine)]",
};

function priorityBadge(priority: number, label: string) {
  const triage = PRIORITY_TO_TRIAGE[priority];
  if (!triage || !label) return null;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
        triage === "emergency"
          ? "badge-emergency"
          : triage === "urgent"
            ? "badge-urgent"
            : "badge-routine"
      }`}
    >
      {label}
    </span>
  );
}

function statusBadge(status: HandoffStatus, label: string) {
  const palette =
    status === "new"
      ? "bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300"
      : status === "acknowledged"
        ? "bg-cyan-50 text-cyan-700 dark:bg-cyan-950/60 dark:text-cyan-300"
        : status === "in_progress"
          ? "bg-violet-50 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300"
          : status === "reviewed"
            ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
            : "bg-base-2 text-ink-3";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${palette}`}>
      {label}
    </span>
  );
}

export default function DoctorInboxPage() {
  const t = useTranslations("doctor.inbox");
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);

  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pdfNotice, setPdfNotice] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<TabKey>("all");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [triageLevel, setTriageLevel] = useState<"" | TriageLevel>("");
  const [language, setLanguage] = useState<"" | "ar" | "en">("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [sort, setSort] = useState<"priority" | "sent_at" | "created_at">("priority");

  const [counts, setCounts] = useState<InboxCounts>({
    new: 0,
    acknowledged: 0,
    in_progress: 0,
    reviewed: 0,
    closed: 0,
    total: 0,
  });

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setSearchQuery(searchInput.trim()), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchInput]);

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", "20");
    params.set("sort", sort);
    if (activeTab !== "all") params.set("status", activeTab);
    if (triageLevel) params.set("triage_level", triageLevel);
    if (language) params.set("language", language);
    if (searchQuery) params.set("q", searchQuery);
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    return params.toString();
  }, [page, sort, activeTab, triageLevel, language, searchQuery, fromDate, toDate]);

  const loadList = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    const res = await apiRequest<{ items: Handoff[]; total: number }>(
      `/handoffs/doctor/inbox?${queryString}`,
      { token: accessToken },
    );
    if (res.data) {
      setHandoffs(res.data.items);
      setTotal(res.data.total);
    } else {
      setLoadError(res.error || "load_failed");
    }
    setLoading(false);
  }, [queryString, accessToken]);

  const loadCounts = useCallback(async () => {
    const res = await apiRequest<InboxCounts>(`/handoffs/doctor/inbox/count`, { token: accessToken });
    if (res.data) setCounts(res.data);
  }, [accessToken]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPage(1);
  }, [activeTab, triageLevel, language, searchQuery, fromDate, toDate, sort]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadList();
  }, [loadList]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadCounts();
  }, [loadCounts]);

  const downloadPdf = async (handoffId: string) => {
    const token = accessToken;
    if (!token) return;
    setPdfNotice(null);
    const res = await fetch(`${API}/handoffs/${handoffId}/pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      setPdfNotice(t("loadFailed"));
      return;
    }
    const contentType = res.headers.get("content-type") || "";
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    if (contentType.startsWith("application/pdf")) {
      const a = document.createElement("a");
      a.href = url;
      a.download = `handoff_${handoffId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      return;
    }

    setPdfNotice(t("pdfUnavailableToast"));
    const win = window.open(url, "_blank", "noopener,noreferrer");
    if (win) {
      const cleanup = () => URL.revokeObjectURL(url);
      win.addEventListener("load", () => {
        try {
          win.focus();
          win.print();
        } catch {
          // ignore — user can print manually
        }
        win.addEventListener("afterprint", cleanup, { once: true });
      });
      setTimeout(cleanup, 60_000);
    } else {
      URL.revokeObjectURL(url);
    }
  };

  const tabBadge = (key: TabKey): number =>
    key === "all" ? counts.total : (counts[key as Exclude<TabKey, "all">] ?? 0);

  const triageLabel = (priority: number): string => {
    const level = PRIORITY_TO_TRIAGE[priority];
    if (!level) return "";
    return t(`priority.${level}`);
  };

  const hasFilters =
    activeTab !== "all" ||
    !!triageLevel ||
    !!language ||
    !!fromDate ||
    !!toDate ||
    !!searchInput.trim() ||
    sort !== "priority";

  const clearFilters = () => {
    setActiveTab("all");
    setTriageLevel("");
    setLanguage("");
    setFromDate("");
    setToDate("");
    setSearchInput("");
    setSort("priority");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 p-6"
    >
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground sm:text-3xl">
          {t("title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-line pb-3">
        {TAB_KEYS.map((key) => {
          const isActive = activeTab === key;
          const badge = tabBadge(key);
          return (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "bg-base-2 text-ink-2 hover:bg-line"
              }`}
            >
              <span>{t(`tabs.${key}`)}</span>
              {badge > 0 && (
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold tabular-nums ${
                    isActive ? "bg-white/20 text-primary-foreground" : "bg-card text-ink-2"
                  }`}
                >
                  {badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="space-y-3 p-4">
          <div className="relative">
            <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-4" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={t("searchPlaceholder")}
              className="w-full rounded-lg border border-line bg-card py-2 ps-10 pe-4 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <FilterField label={t("priority.label")}>
              <select
                value={triageLevel}
                onChange={(e) => setTriageLevel(e.target.value as "" | TriageLevel)}
                className="rounded-lg border border-line bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
              >
                <option value="">{t("anyTriage")}</option>
                <option value="emergency">{t("priority.emergency")}</option>
                <option value="urgent">{t("priority.urgent")}</option>
                <option value="routine">{t("priority.routine")}</option>
              </select>
            </FilterField>

            <FilterField label={t("language.ar") + " / " + t("language.en")}>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as "" | "ar" | "en")}
                className="rounded-lg border border-line bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
              >
                <option value="">{t("anyLanguage")}</option>
                <option value="ar">{t("language.ar")}</option>
                <option value="en">{t("language.en")}</option>
              </select>
            </FilterField>

            <FilterField label={t("fromDate")}>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="rounded-lg border border-line bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
              />
            </FilterField>

            <FilterField label={t("toDate")}>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="rounded-lg border border-line bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
              />
            </FilterField>

            <FilterField label={t("sort.label")}>
              <select
                value={sort}
                onChange={(e) =>
                  setSort(e.target.value as "priority" | "sent_at" | "created_at")
                }
                className="rounded-lg border border-line bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
              >
                <option value="priority">{t("sort.priority")}</option>
                <option value="sent_at">{t("sort.sent_at")}</option>
                <option value="created_at">{t("sort.created_at")}</option>
              </select>
            </FilterField>

            {hasFilters && (
              <button
                onClick={clearFilters}
                className="ms-auto inline-flex items-center gap-1.5 rounded-lg bg-base-2 px-3 py-2 text-sm font-medium text-ink-2 transition-colors hover:bg-line"
              >
                <FilterX className="h-4 w-4" />
                {t("clearFilters")}
              </button>
            )}
          </div>
        </CardContent>
      </Card>

      {pdfNotice && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p className="flex-1">{pdfNotice}</p>
          <button
            onClick={() => setPdfNotice(null)}
            className="text-xs font-medium underline-offset-2 hover:underline"
          >
            ✕
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : loadError ? (
        <Card>
          <CardContent className="space-y-3 py-16 text-center">
            <AlertTriangle className="mx-auto h-10 w-10 text-amber-500" />
            <p className="text-sm text-ink-3">{t("loadFailed")}</p>
            <button
              onClick={() => {
                loadList();
                loadCounts();
              }}
              className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
            >
              {t("retry")}
            </button>
          </CardContent>
        </Card>
      ) : handoffs.length === 0 ? (
        <Card>
          <CardContent className="py-20 text-center">
            <ClipboardList className="mx-auto h-12 w-12 text-ink-4" />
            <h3 className="mt-4 text-lg font-semibold text-ink-2">
              {counts.total === 0 ? t("empty") : t("noMatches")}
            </h3>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {handoffs.map((h) => {
            const triage = PRIORITY_TO_TRIAGE[h.priority];
            const preview = extractChiefComplaint(h.summary_markdown);
            const sentDate = h.sent_at || h.created_at;
            return (
              <Card
                key={h.id}
                className="overflow-hidden transition-colors hover:border-primary/40"
              >
                <CardContent className="p-0">
                  <div className="flex items-stretch">
                    <div
                      className={`w-1 flex-shrink-0 ${triage ? TRIAGE_BAR[triage] : "bg-line"}`}
                    />
                    <div className="flex flex-1 flex-col gap-3 p-5 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0 flex-1 space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          {priorityBadge(h.priority, triageLabel(h.priority))}
                          {statusBadge(h.status || "new", t(`status.${h.status || "new"}`))}
                          {h.target_language && (
                            <span className="rounded-full bg-base-2 px-2 py-0.5 text-[10px] font-semibold text-ink-3 uppercase">
                              {h.target_language}
                            </span>
                          )}
                          {h.auto_routed && (
                            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300">
                              auto
                            </span>
                          )}
                        </div>

                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-4">
                            {t("chiefComplaint")}
                          </p>
                          <p className="mt-0.5 line-clamp-2 text-sm font-medium text-foreground">
                            {preview || t("noPreview")}
                          </p>
                        </div>

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-4">
                          <span className="inline-flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5" />
                            {sentDate
                              ? new Date(sentDate).toLocaleDateString(undefined, {
                                  year: "numeric",
                                  month: "short",
                                  day: "numeric",
                                })
                              : "—"}
                          </span>
                          <span className="inline-flex items-center gap-1.5">
                            <User className="h-3.5 w-3.5" />
                            {h.patient_name ? (
                              <>
                                <span className="font-medium text-ink-3">
                                  {h.patient_name}
                                </span>
                                <span className="font-mono text-ink-4">
                                  · {h.patient_user_id.slice(0, 8)}
                                </span>
                              </>
                            ) : (
                              <span className="font-mono">
                                {h.patient_user_id.slice(0, 8)}
                              </span>
                            )}
                          </span>
                        </div>
                      </div>

                      <div className="flex flex-shrink-0 items-center gap-2 sm:flex-col sm:items-stretch lg:flex-row">
                        <button
                          onClick={() => router.push(`/doctor/handoff/${h.id}`)}
                          className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
                        >
                          <Eye className="h-4 w-4" />
                          {t("view")}
                        </button>
                        <button
                          onClick={() => downloadPdf(h.id)}
                          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-line bg-card px-4 py-2 text-sm font-semibold text-ink-2 transition-colors hover:border-primary/40 hover:text-primary"
                        >
                          <Download className="h-4 w-4" />
                          {t("downloadPdf")}
                        </button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}

          {total > 20 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
                className="rounded-full bg-base-2 px-4 py-2 text-sm font-medium text-ink-3 transition-colors hover:bg-line disabled:opacity-40"
              >
                {t("pagination.prev")}
              </button>
              <span className="text-sm tabular-nums text-ink-4">
                {t("pagination.pageOf", { page, total: Math.ceil(total / 20) })}
              </span>
              <button
                disabled={page * 20 >= total}
                onClick={() => setPage(page + 1)}
                className="rounded-full bg-base-2 px-4 py-2 text-sm font-medium text-ink-3 transition-colors hover:bg-line disabled:opacity-40"
              >
                {t("pagination.next")}
              </button>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-ink-3">
      <span className="text-[10px] uppercase tracking-wide">{label}</span>
      {children}
    </label>
  );
}
