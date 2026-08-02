"use client";

/**
 * Red-flag watch list — surfaces dangerous signals to monitor for.
 *
 * Renders only when the backend emits a `watch_signals` event AND the case is
 * urgent or emergency. We deliberately do NOT use `useTranslations` here —
 * label language follows the *patient's* locale (passed via prop), not the
 * URL locale, so an Arabic conversation never gets an English heading.
 */

import { AlertTriangle } from "lucide-react";

interface WatchSignalsCardProps {
  signals: string[];
  language?: "ar" | "en";
}

const LABELS: Record<
  "ar" | "en",
  { title: string; disclaimer: string }
> = {
  ar: {
    title: "علامات تستدعي طوارئ فورية:",
    disclaimer:
      "هذه إشارات عامة — حالتك قد تنطوي على مخاطر إضافية. عند الشك، اطلب الرعاية الطبية.",
  },
  en: {
    title: "Seek emergency care immediately if you develop:",
    disclaimer:
      "These are general warning signs — your case may carry additional risks. When in doubt, seek care.",
  },
};

export function WatchSignalsCard({ signals, language = "ar" }: WatchSignalsCardProps) {
  const labels = LABELS[language];
  if (!signals || signals.length === 0) return null;

  return (
    <div className="rounded-xl border-2 border-red-300/70 bg-red-50/60 shadow-sm overflow-hidden dark:border-red-800/60 dark:bg-red-950/30">
      <div className="flex items-center gap-2 px-4 py-2.5 bg-red-100/70 dark:bg-red-950/60">
        <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0" />
        <span className="text-[13px] font-semibold text-red-900 dark:text-red-100">
          {labels.title}
        </span>
      </div>
      <ul className="px-4 py-3 space-y-1.5">
        {signals.map((s, i) => (
          <li
            key={i}
            className="flex items-start gap-2 text-[13px] text-red-900 dark:text-red-100"
          >
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />
            <span className="flex-1 leading-relaxed">{s}</span>
          </li>
        ))}
      </ul>
      <p className="px-4 pb-3 text-[11px] text-red-700/80 dark:text-red-300/80 italic">
        {labels.disclaimer}
      </p>
    </div>
  );
}
