"use client";

import type { ChatEvent } from "@/lib/api/chat";
import { AlertTriangle, CheckCircle, Clock } from "lucide-react";
import { useTranslations } from "next-intl";

type TriageState = {
  level: string | null;
  score: number | null;
  reasoning: string | null;
  redFlags: boolean;
};

// Color values come from CSS tokens (--emergency / --urgent / --routine in globals.css)
// so theme switches and brand re-skins flow through here automatically.
const config = {
  emergency: { color: "var(--emergency)", bg: "bg-red-50 dark:bg-red-950/30", icon: AlertTriangle, labelKey: "emergency", actionKey: "emergencyAction" },
  urgent: { color: "var(--urgent)", bg: "bg-amber-50 dark:bg-amber-950/30", icon: Clock, labelKey: "urgent", actionKey: "urgentAction" },
  routine: { color: "var(--routine)", bg: "bg-emerald-50 dark:bg-emerald-950/30", icon: CheckCircle, labelKey: "routine", actionKey: "routineAction" },
};

export function triageFromEvents(events?: ChatEvent[]): TriageState {
  const triage = events?.find((e) => e.type === "triage");
  const redFlag = events?.some((e) => e.type === "red_flag");
  return {
    level: redFlag ? "emergency" : (triage?.data?.level as string) || null,
    score: triage?.data?.score as number || null,
    reasoning: (triage?.data?.reasoning as string) || null,
    redFlags: !!redFlag,
  };
}

type Props = {
  state: TriageState;
  collapsed?: boolean;
  onToggle?: () => void;
};

export function TriagePanel({ state, collapsed, onToggle }: Props) {
  const t = useTranslations("chat");
  if (!state.level) return null;

  const c = config[state.level as keyof typeof config] || config.routine;

  return (
    <div className="border-b border-line-2 p-4">
      <button onClick={onToggle} className="w-full flex items-center justify-between text-left">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ background: c.color }} />
          <span className="text-sm font-semibold" style={{ color: c.color }}>{t(c.labelKey)}</span>
        </div>
        <span className="text-xs text-ink-4">{collapsed ? "Show" : "Hide"} details</span>
      </button>

      {!collapsed && (
        <div className="mt-3 space-y-2">
          {state.score !== null && (
            <div className="flex items-center gap-3">
              <span className="text-xs text-ink-4">{t("triageScore")}</span>
              <div className="flex-1 h-1.5 rounded-full bg-line overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${state.score}%`, background: c.color }} />
              </div>
              <span className="text-xs font-semibold text-ink-2">{state.score}/100</span>
            </div>
          )}
          {state.reasoning && (
            <p className="text-xs text-ink-3 leading-relaxed">{state.reasoning}</p>
          )}
          <div className={`text-xs font-semibold px-3 py-2 rounded-lg flex items-center gap-2 ${c.bg}`} style={{ color: c.color }}>
            <c.icon className="h-3.5 w-3.5" />
            {t(c.actionKey)}
          </div>
        </div>
      )}
    </div>
  );
}
