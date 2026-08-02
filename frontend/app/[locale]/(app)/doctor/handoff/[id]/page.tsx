"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  Download,
  ListChecks,
  Lock,
  Play,
  Printer,
  Square,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { Fragment, use, useCallback, useEffect, useRef, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ToastViewport, useToasts } from "@/components/ui/toast";
import { apiRequest } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "@/src/i18n/navigation";

type HandoffStatus = "new" | "acknowledged" | "in_progress" | "reviewed" | "closed";

const STATUS_ORDER: HandoffStatus[] = [
  "new",
  "acknowledged",
  "in_progress",
  "reviewed",
  "closed",
];

const AUTOSAVE_DELAY_MS = 1500;

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
  updated_at: string;
};

const STATUS_TRANSITIONS: Record<HandoffStatus, HandoffStatus[]> = {
  new: ["acknowledged", "in_progress", "reviewed", "closed"],
  acknowledged: ["in_progress", "reviewed", "closed"],
  in_progress: ["reviewed", "closed"],
  reviewed: ["closed"],
  closed: [],
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function DoctorHandoffDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("doctor");
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const [handoff, setHandoff] = useState<Handoff | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [savedNotes, setSavedNotes] = useState(false);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState<HandoffStatus | null>(null);

  // B5: unified toast stack — replaces 3 inline `<Notice>` slots (status /
  // notes / pdf) with a single dismissible viewport. Inline error text under
  // the relevant control is kept for accessibility (announces nearer the
  // form), but global / stale events are surfaced as toasts.
  const [toasts, pushToast, dismissToast] = useToasts();
  const [statusError, setStatusError] = useState<string | null>(null);

  // B7: refs + flags for debounced autosave of notes
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initialNotesRef = useRef<string>("");
  const handoffIdRef = useRef<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    const res = await apiRequest<Handoff>(`/handoffs/${id}`, { token: accessToken });
    if (res.data) {
      setHandoff(res.data);
      const loadedNotes = res.data.doctor_private_notes || "";
      setNotes(loadedNotes);
      // Snapshot of server state — autosave only fires when notes diverge.
      initialNotesRef.current = loadedNotes;
      handoffIdRef.current = res.data.id;
      if (loadedNotes) {
        setSavedNotes(true);
        setLastSavedAt(null);
      }
    } else {
      setLoadError(res.error || "load_failed");
    }
    setLoading(false);
  }, [id, accessToken]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  // Programmatic save — used by both manual button and autosave.
  const handoffUpdatedAt = handoff?.updated_at;
  const saveNotes = useCallback(
    async (value: string) => {
      const handoffId = handoffIdRef.current;
      if (!handoffId) return;
      setSavingNotes(true);
      setNotesError(null);
      // B3: include If-Unmodified-Since so concurrent edits surface as 412.
      const headers: Record<string, string> = {};
      if (handoffUpdatedAt) {
        headers["If-Unmodified-Since"] = new Date(handoffUpdatedAt).toUTCString();
      }
      const res = await apiRequest(`/handoffs/${handoffId}/review`, {
        method: "POST",
        body: { notes: value },
        token: accessToken,
        headers,
      });
      setSavingNotes(false);
      if (res.error || res.status >= 400) {
        if (res.status === 412) {
          setNotesError(t("handoff.actions.staleError"));
          await load();
        } else {
          setNotesError(t("handoff.notes.saveError"));
        }
        return;
      }
      setSavedNotes(true);
      setLastSavedAt(new Date());
      initialNotesRef.current = value;
    },
    [accessToken, handoffUpdatedAt, load, t],
  );

  const handleSaveNotes = () => {
    if (!handoff) return;
    // Manual save cancels any pending autosave to avoid double-write.
    if (autosaveTimerRef.current) {
      clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }
    saveNotes(notes);
  };

  // B7: debounced autosave — fires AUTOSAVE_DELAY_MS after the last keystroke,
  // only if the value diverges from the last server snapshot.
  useEffect(() => {
    if (!handoff) return;
    if (notes === initialNotesRef.current) return;
    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    autosaveTimerRef.current = setTimeout(() => {
      saveNotes(notes);
    }, AUTOSAVE_DELAY_MS);
    return () => {
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    };
  }, [notes, handoff, saveNotes]);

  const transitionTo = async (next: HandoffStatus) => {
    if (!handoff) return;
    setStatusError(null);
    setUpdatingStatus(next);

    // B1: Optimistic update — apply the new status immediately + pre-fill the
    // timestamp that the backend would set, so the timeline reflects reality
    // before the round-trip finishes.
    const snapshot = handoff;
    const now = new Date().toISOString();
    setHandoff({
      ...handoff,
      status: next,
      acknowledged_at:
        (next === "acknowledged" || next === "in_progress") && !handoff.acknowledged_at
          ? now
          : handoff.acknowledged_at,
      reviewed_at:
        next === "reviewed" && !handoff.reviewed_at ? now : handoff.reviewed_at,
      closed_at: next === "closed" && !handoff.closed_at ? now : handoff.closed_at,
    });

    // B3: send the row's last-known timestamp as an If-Unmodified-Since header
    // so the backend can return 412 if another writer beat us to it.
    const ifUnmodifiedSince = new Date(handoff.updated_at).toUTCString();
    const res = await apiRequest<{ status: HandoffStatus }>(
      `/handoffs/${handoff.id}/status`,
      {
        method: "PATCH",
        body: { status: next },
        token: accessToken,
        headers: { "If-Unmodified-Since": ifUnmodifiedSince },
      },
    );
    setUpdatingStatus(null);
    if (res.error || res.status >= 400) {
      // B1: Rollback the optimistic state.
      setHandoff(snapshot);
      // B3 (frontend half): handle stale state from concurrent update.
      if (res.status === 412) {
        setStatusError(t("handoff.actions.staleError"));
        // Refetch to recover the canonical state.
        await load();
      } else {
        setStatusError(t("handoff.actions.transitionError"));
      }
      return;
    }
    // We don't await load() here — the optimistic state already matches.
  };

  const handleDownloadOrPrint = async () => {
    if (!handoff || !accessToken) return;
    const res = await fetch(`${API}/handoffs/${handoff.id}/pdf`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!res.ok) {
      pushToast({ tone: "error", message: t("inbox.loadFailed") });
      return;
    }
    const contentType = res.headers.get("content-type") || "";
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    if (contentType.startsWith("application/pdf")) {
      const a = document.createElement("a");
      a.href = url;
      a.download = `handoff_${handoff.id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      return;
    }
    pushToast({ tone: "warning", message: t("inbox.pdfUnavailableToast") });
    const win = window.open(url, "_blank", "noopener,noreferrer");
    if (win) {
      win.addEventListener("load", () => {
        try {
          win.focus();
          win.print();
        } catch {
          // ignore
        }
        win.addEventListener(
          "afterprint",
          () => URL.revokeObjectURL(url),
          { once: true },
        );
      });
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } else {
      URL.revokeObjectURL(url);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (loadError || !handoff) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-6 text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <div>
          <p className="font-semibold text-foreground">
            {loadError ? t("inbox.loadFailed") : "Handoff not found"}
          </p>
          <p className="mt-1 text-sm text-ink-3">ID: <span className="font-mono">{id}</span></p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => router.push("/doctor/inbox")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-base-2 px-4 py-2 text-sm font-semibold text-ink-2 hover:bg-line"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("handoff.backToInbox")}
          </button>
          <button
            onClick={load}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90"
          >
            {t("inbox.retry")}
          </button>
        </div>
      </div>
    );
  }

  const status = handoff.status || "new";
  const allowed = STATUS_TRANSITIONS[status] ?? [];
  const canTransition = (target: HandoffStatus) => allowed.includes(target);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 p-6 print:p-0 print:space-y-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <button
          onClick={() => router.push("/doctor/inbox")}
          className="inline-flex items-center gap-2 text-sm font-medium text-ink-3 transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("handoff.backToInbox")}
        </button>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-card px-3 py-2 text-sm font-semibold text-ink-2 transition-colors hover:border-primary/40 hover:text-primary"
          >
            <Printer className="h-4 w-4" />
            {t("inbox.print")}
          </button>
          <button
            onClick={handleDownloadOrPrint}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
          >
            <Download className="h-4 w-4" />
            {t("inbox.downloadPdf")}
          </button>
        </div>
      </div>

      <div>
        <h1 className="font-display text-2xl font-bold text-foreground sm:text-3xl">
          {t("handoff.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {new Date(handoff.created_at).toLocaleDateString()} · Sent:{" "}
          {handoff.sent_at ? new Date(handoff.sent_at).toLocaleString() : "—"} ·{" "}
          <span className="font-medium text-foreground">
            {t(`inbox.status.${handoff.status || "new"}`)}
          </span>
        </p>
      </div>

      {/* B6: Status timeline — shows the case's path through the workflow */}
      <StatusTimeline
        status={status}
        sentAt={handoff.sent_at}
        acknowledgedAt={handoff.acknowledged_at}
        reviewedAt={handoff.reviewed_at}
        closedAt={handoff.closed_at}
        labels={{
          new: t("handoff.timeline.new"),
          acknowledged: t("handoff.timeline.acknowledged"),
          in_progress: t("handoff.timeline.in_progress"),
          reviewed: t("handoff.timeline.reviewed"),
          closed: t("handoff.timeline.closed"),
        }}
      />

      {/* Workflow actions */}
      <Card className="print:hidden">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListChecks className="h-5 w-5" />
            {t("handoff.actions.title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <ActionButton
              icon={<CheckCircle className="h-4 w-4" />}
              label={t("handoff.actions.acknowledge")}
              disabled={!canTransition("acknowledged")}
              loading={updatingStatus === "acknowledged"}
              onClick={() => transitionTo("acknowledged")}
              disabledReason={t("handoff.actions.disabledReason")}
              loadingReason={t("handoff.actions.loadingReason")}
            />
            <ActionButton
              icon={<Play className="h-4 w-4" />}
              label={t("handoff.actions.start")}
              disabled={!canTransition("in_progress")}
              loading={updatingStatus === "in_progress"}
              onClick={() => transitionTo("in_progress")}
              disabledReason={t("handoff.actions.disabledReason")}
              loadingReason={t("handoff.actions.loadingReason")}
            />
            <ActionButton
              icon={<CheckCircle className="h-4 w-4" />}
              label={t("handoff.actions.markReviewed")}
              disabled={!canTransition("reviewed")}
              loading={updatingStatus === "reviewed"}
              onClick={() => transitionTo("reviewed")}
              disabledReason={t("handoff.actions.disabledReason")}
              loadingReason={t("handoff.actions.loadingReason")}
            />
            <ActionButton
              icon={<Square className="h-4 w-4" />}
              label={t("handoff.actions.close")}
              disabled={!canTransition("closed")}
              loading={updatingStatus === "closed"}
              onClick={() => transitionTo("closed")}
              disabledReason={t("handoff.actions.disabledReason")}
              loadingReason={t("handoff.actions.loadingReason")}
            />
          </div>
          {statusError && <p className="text-sm text-red-600">{statusError}</p>}
          {handoff.status === "closed" && (
            <p className="inline-flex items-center gap-1.5 text-sm text-ink-4">
              <Lock className="h-3.5 w-3.5" />
              {t("inbox.status.closed")}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Patient info */}
      <Card>
        <CardHeader>
          <CardTitle>{t("handoff.patientInfo")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-4">
                {t("handoff.patientName")}
              </p>
              <p className="font-medium text-ink-2">
                {handoff.patient_name || (
                  <span className="italic text-ink-4">{t("handoff.unknownPatient")}</span>
                )}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-4">
                {t("handoff.patientId")}
              </p>
              <p className="font-mono text-ink-2">{handoff.patient_user_id}</p>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-4">
                {t("handoff.conversationId")}
              </p>
              <p className="font-mono text-ink-2">{handoff.conversation_id}</p>
            </div>
            {handoff.target_specialty && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-4">
                  {t("handoff.targetSpecialty")}
                </p>
                <p className="font-medium text-ink-2">{handoff.target_specialty}</p>
              </div>
            )}
            {handoff.target_language && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-4">
                  {t("handoff.language")}
                </p>
                <p className="font-medium uppercase text-ink-2">{handoff.target_language}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle>{t("handoff.summary")}</CardTitle>
        </CardHeader>
        <CardContent>
          {handoff.summary_markdown ? (
            <div className="whitespace-pre-wrap text-sm text-ink-2 leading-relaxed max-w-none">
              {handoff.summary_markdown}
            </div>
          ) : (
            <p className="text-sm text-ink-4">No summary available</p>
          )}
        </CardContent>
      </Card>

      {/* Private notes */}
      <Card className="print:hidden">
        <CardHeader>
          <CardTitle>{t("inbox.notes")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            value={notes}
            onChange={(e) => {
              setNotes(e.target.value);
              if (savedNotes) setSavedNotes(false);
              if (notesError) setNotesError(null);
            }}
            placeholder={t("inbox.notesPlaceholder")}
            rows={4}
            className="w-full rounded-xl border border-line bg-card p-4 text-sm text-foreground outline-none focus:border-primary"
          />
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleSaveNotes}
              disabled={savingNotes}
              className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {savingNotes ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              {t("inbox.saveNotes")}
            </button>
            {/* B7: dynamic status — saving / saved at HH:MM / error / autosave hint */}
            {savingNotes && (
              <span className="text-sm font-medium text-ink-3">
                {t("handoff.notes.saving")}
              </span>
            )}
            {!savingNotes && savedNotes && !notesError && (
              <span className="text-sm font-medium text-emerald-600">
                {lastSavedAt
                  ? t("handoff.notes.savedAt", {
                      time: lastSavedAt.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      }),
                    })
                  : t("inbox.saved")}
              </span>
            )}
            {notesError && (
              <span className="text-sm font-medium text-red-600">{notesError}</span>
            )}
            {!savingNotes && !savedNotes && !notesError && (
              <span className="text-xs text-ink-4">
                {t("handoff.notes.autosaveHint")}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* B5: stack of dismissible toasts (PDF errors, etc.) */}
      <ToastViewport toasts={toasts} onDismiss={dismissToast} />
    </motion.div>
  );
}

function ActionButton({
  icon,
  label,
  disabled,
  loading,
  onClick,
  disabledReason,
  loadingReason,
}: {
  icon: React.ReactNode;
  label: string;
  disabled: boolean;
  loading: boolean;
  onClick: () => void;
  disabledReason: string;
  loadingReason: string;
}) {
  // B2: distinct visuals for disabled vs loading.
  //   - disabled (transition not allowed): muted gray, no spinner, tooltip
  //   - loading (in-flight): primary tint, spinner, tooltip
  //   - active: primary tint with hover
  const title = loading ? loadingReason : disabled ? disabledReason : undefined;
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      title={title}
      aria-disabled={disabled || loading}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition-colors",
        loading && "bg-primary-tint text-primary cursor-progress",
        !loading && disabled && "bg-base-2 text-ink-4 cursor-not-allowed",
        !loading && !disabled && "bg-primary-tint text-primary hover:bg-primary/10",
      )}
    >
      {loading ? (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      ) : (
        icon
      )}
      {label}
    </button>
  );
}

// B6: Compact horizontal status timeline. Highlights the current step and
// surfaces the timestamps from sent_at / acknowledged_at / reviewed_at / closed_at.
function StatusTimeline({
  status,
  sentAt,
  acknowledgedAt,
  reviewedAt,
  closedAt,
  labels,
}: {
  status: HandoffStatus;
  sentAt: string | null;
  acknowledgedAt: string | null;
  reviewedAt: string | null;
  closedAt: string | null;
  labels: Record<HandoffStatus, string>;
}) {
  const steps: { key: HandoffStatus; at: string | null }[] = [
    { key: "new", at: sentAt },
    { key: "acknowledged", at: acknowledgedAt },
    { key: "in_progress", at: acknowledgedAt },
    { key: "reviewed", at: reviewedAt },
    { key: "closed", at: closedAt },
  ];
  const currentIdx = STATUS_ORDER.indexOf(status);

  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-1 print:hidden">
      {steps.map((step, idx) => {
        const isCurrent = idx === currentIdx;
        const reached = idx <= currentIdx;
        return (
          <Fragment key={step.key}>
            <div
              className={cn(
                "flex flex-col items-start gap-0.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-colors flex-shrink-0",
                isCurrent && "bg-primary text-primary-foreground shadow-sm",
                !isCurrent && reached && "bg-primary-tint text-primary",
                !reached && "bg-base-2 text-ink-4",
              )}
            >
              <span>{labels[step.key]}</span>
              {step.at && (
                <span className="text-[10px] font-normal opacity-75">
                  {new Date(step.at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              )}
            </div>
            {idx < steps.length - 1 && (
              <div
                className={cn(
                  "h-0.5 w-3 flex-shrink-0 rounded transition-colors",
                  idx < currentIdx ? "bg-primary" : "bg-line",
                )}
              />
            )}
          </Fragment>
        );
      })}
    </div>
  );
}
