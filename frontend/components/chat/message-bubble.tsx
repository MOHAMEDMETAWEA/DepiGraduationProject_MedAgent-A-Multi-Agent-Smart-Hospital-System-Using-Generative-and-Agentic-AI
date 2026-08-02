"use client";

import { Activity, AlertTriangle, Stethoscope, User } from "lucide-react";
import { useTranslations } from "next-intl";

import type { ChatEvent } from "@/lib/api/chat";
import { Markdown } from "@/components/ui/markdown";
import { cn } from "@/lib/utils";

type Props = {
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  events?: ChatEvent[];
  senderName?: string;
  modelColor?: string;
  imagePreview?: string;
};

const MODEL_COLORS: Record<string, string> = {
  "Qwen 3 32B": "#10B981",
  "Qwen 2.5 72B": "#8B5CF6",
  "Allam 2 7B": "#059669",
  "Llama 3.3 70B": "#6366F1",
  "Llama 4 Scout 17B": "#4F46E5",
  "Llama 3.1 8B": "#818CF8",
  "GPT-4o": "#2563EB",
  "GPT-4o Mini": "#3B82F6",
  "GPT-4.1": "#1D4ED8",
  "Claude 3.5 Sonnet": "#D97706",
  "Gemini 2.5 Flash": "#F59E0B",
  "Gemini 2.5 Pro": "#D97706",
  "DeepSeek V3": "#0EA5E9",
  "Llama 4 Maverick": "#7C3AED",
};

const DEFAULT_COLOR = "#6B7280";

function getModelColor(name: string): string {
  return MODEL_COLORS[name] || DEFAULT_COLOR;
}

export type ReasoningStep = { tool: string; result: string };

export function buildReasoningSteps(events: ChatEvent[]): ReasoningStep[] {
  const steps: ReasoningStep[] = [];
  const seen = new Set<string>();

  for (const event of events) {
    if (event.type === "tool_result") {
      const tool = (event.data?.tool as string) || "";
      if (!tool || seen.has(tool)) continue;
      seen.add(tool);

      const result = event.data?.result as Record<string, unknown> | undefined;
      if (!result) continue;

      let summary = "";

      if (tool === "detect_red_flags") {
        const flags = result.flags;
        if (Array.isArray(flags) && flags.length > 0) {
          const flagTexts = flags.map((f: unknown) => {
            if (typeof f === "string") return f;
            if (typeof f === "object" && f !== null) return (f as Record<string, string>).text || (f as Record<string, string>).name || (f as Record<string, string>).keyword || String(f);
            return String(f);
          });
          summary = `⚠️ ${flagTexts.join("، ")}`;
        } else {
          summary = "لا توجد علامات طارئة";
        }
      } else if (tool === "score_triage") {
        const level = (result.level as string) || "?";
        const score = result.score as number || 0;
        summary = `${level} · Score ${score}`;
      } else if (tool === "retrieve_medical_knowledge") {
        const chunks = result.chunks as Array<{ title?: string }> | undefined;
        summary = chunks?.length ? `تم العثور على ${chunks.length} مصادر` : "لا توجد نتائج";
      } else if (tool === "check_medication_interactions") {
        const interactions = result.interactions as Array<unknown> | undefined;
        summary = interactions?.length ? `تم العثور على ${interactions.length} تفاعلات` : "لا توجد تفاعلات";
      } else {
        const err = result.error as string | undefined;
        summary = err ? `خطأ: ${err}` : "اكتمل";
      }

      steps.push({ tool, result: summary });
    }
  }

  return steps;
}

/**
 * Per-triage-level theming — emergency / urgent / routine each gets its own
 * accent stack (background, border, icon tint, text). Keeping this in one
 * map so designers can tweak the palette without hunting through JSX.
 */
const TRIAGE_THEMES: Record<
  "emergency" | "urgent" | "routine",
  {
    bg: string;
    border: string;
    icon: string;
    label: string;
    bodyBg: string;
    dot: string;
  }
> = {
  emergency: {
    bg: "bg-gradient-to-l from-red-600 to-rose-600",
    border: "border-red-300 dark:border-red-700",
    icon: "text-red-100",
    label: "text-white",
    bodyBg: "bg-red-50 dark:bg-red-950/30",
    dot: "bg-red-500",
  },
  urgent: {
    bg: "bg-gradient-to-l from-amber-500 to-orange-500",
    border: "border-amber-300 dark:border-amber-700",
    icon: "text-amber-50",
    label: "text-white",
    bodyBg: "bg-amber-50 dark:bg-amber-950/30",
    dot: "bg-amber-500",
  },
  routine: {
    bg: "bg-gradient-to-l from-emerald-500 to-teal-500",
    border: "border-emerald-300 dark:border-emerald-700",
    icon: "text-emerald-50",
    label: "text-white",
    bodyBg: "bg-emerald-50 dark:bg-emerald-950/30",
    dot: "bg-emerald-500",
  },
};

export function MessageBubble({ role, content, events, senderName, modelColor, imagePreview }: Props) {
  const t = useTranslations("chat");
  const isUser = role === "user";
  const triageEvent = events?.find((e) => e.type === "triage");
  const hasTriage = !!triageEvent;
  const hasRedFlag = events?.some((e) => e.type === "red_flag");

  const triageLevel = (triageEvent?.data?.level as string | undefined)?.toLowerCase();
  const theme =
    triageLevel === "emergency" || triageLevel === "urgent" || triageLevel === "routine"
      ? TRIAGE_THEMES[triageLevel]
      : null;
  const triageScore = triageEvent?.data?.score;

  const initials = senderName ? senderName.split(" ").map((s) => s[0]).join("").slice(0, 2).toUpperCase() : "";
  const color = modelColor || getModelColor(senderName || "");



  return (
    <div className={cn("flex gap-3 mb-6", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={cn(
          "flex-shrink-0 grid place-items-center w-9 h-9 rounded-xl text-[11px] font-bold text-white shadow-sm",
        )}
        style={{ background: isUser ? "linear-gradient(135deg, #4B5563, #374151)" : `linear-gradient(135deg, ${color}, ${color}dd)` }}
      >
        {isUser ? (
          senderName ? initials : <User className="h-4 w-4" />
        ) : (
          <Stethoscope className="h-4 w-4" />
        )}
      </div>

      {/* Content */}
      <div className="max-w-[80%] space-y-2.5">
        {/* Sender name */}
        {senderName && !isUser && (
          <p className="text-xs font-semibold px-1" style={{ color }}>{senderName}</p>
        )}

        {/* Red flag alert — full-bleed emergency banner */}
        {hasRedFlag && (
          <div className="flex items-center gap-2.5 text-[13px] font-semibold text-white rounded-xl px-4 py-3 shadow-md bg-gradient-to-l from-red-600 to-rose-700">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {t("emergency")}
          </div>
        )}

        {/* Attached image preview (user only) */}
        {isUser && imagePreview && (
          <div className="overflow-hidden rounded-2xl rounded-br-md border border-border max-w-[260px] shadow-sm">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imagePreview} alt="Uploaded medical image" className="w-full h-auto object-cover max-h-[260px]" />
          </div>
        )}

        {/* Message text — user messages render as plain text (their literal
            words shouldn't get reinterpreted as markdown — a patient typing
            `**` shouldn't get bolded). Assistant messages flow through the
            Markdown component so the `### / **bold** / 1. lists` the LLM
            now emits actually render as a doctor-note shape instead of
            showing raw `###` characters to the patient. */}
        {content && (
          <div
            className={cn(
              "px-4 py-3 text-sm leading-relaxed shadow-sm",
              isUser
                ? "rounded-2xl rounded-br-md bg-[#374151] text-white"
                : "rounded-2xl rounded-bl-md bg-card border border-border text-foreground"
            )}
          >
            {isUser ? (
              <span className="whitespace-pre-wrap">{content}</span>
            ) : (
              <Markdown>{content}</Markdown>
            )}
          </div>
        )}

        {/* Triage card — colored by urgency level (emergency / urgent / routine).
            UX2: shows a "لماذا؟" list of detected flags + scorer reasoning. */}
        {hasTriage && theme && (
          <div
            className={cn(
              "rounded-xl overflow-hidden border shadow-sm",
              theme.border,
            )}
          >
            <div
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 text-[12px] font-semibold",
                theme.bg,
                theme.label,
              )}
            >
              <Activity className={cn("h-3.5 w-3.5", theme.icon)} />
              <span>
                {triageLevel ? t(`triage.${triageLevel}`) : t("triage.routine")}
              </span>
              {triageScore !== undefined && triageScore !== null && (
                <span className="ms-auto tabular-nums font-bold">
                  {t("triage.scorePrefix")} {String(triageScore)}
                </span>
              )}
            </div>
            <div className={cn("p-4 text-[13px] text-foreground/80", theme.bodyBg)}>
              <p>
                {String(
                  triageEvent?.data?.reasoning || t("triage.assessmentComplete"),
                )}
              </p>
              {/* The previous "Why?" bullet list was removed — it duplicated
                  either the patient's own words or this same reasoning line.
                  Real explainability needs scorer-derived facts (not keyword
                  echo); leaving the section blank is honest until we have that. */}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex gap-3 mb-6">
      <div className="flex-shrink-0 grid place-items-center w-9 h-9 rounded-xl text-[11px] font-bold text-white shadow-sm" style={{ background: "linear-gradient(135deg, #6B7280, #9CA3AF)" }}>
        <Stethoscope className="h-4 w-4" />
      </div>
      <div className="rounded-2xl rounded-bl-md bg-card border border-border px-4 py-3 shadow-sm">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-[typing_1.4s_ease-in-out_infinite_both]" style={{ animationDelay: `${-0.32 + i * 0.16}s` }} />
          ))}
        </div>
      </div>
    </div>
  );
}
