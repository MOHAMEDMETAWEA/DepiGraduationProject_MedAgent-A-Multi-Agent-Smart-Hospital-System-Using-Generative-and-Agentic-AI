"use client";

import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle, Eye, ImageIcon, Info } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { springSmooth } from "@/lib/motion";

export interface VisionResult {
  findings: string[];
  urgency: "emergency" | "urgent" | "routine" | "none";
  confidence: number;
  disclaimer: string;
  imageUrl?: string;
  /** Raw error string from the backend when the upstream vision LLM call
   *  failed (quota, billing, 4xx). We use this to show a clear hint instead
   *  of the generic "Vision LLM unavailable" fallback. */
  error?: string;
}

interface Props {
  result: VisionResult;
  /** Locale for static labels — defaults to "en". The findings + disclaimer
   *  text is already produced in the conversation language by the backend. */
  language?: "ar" | "en";
}

// Static label maps — we deliberately do NOT use useTranslations here because
// the chat language is per-conversation, not per-URL-locale (a doctor browsing
// in English may open an Arabic patient chat).
const LABELS = {
  ar: {
    title: "تحليل الصورة",
    viewFull: "عرض كامل",
    confidence: "نسبة الثقة",
    findings: "النتائج",
    failedTitle: "فشل التحليل",
    failedHint: {
      quota: "تم تجاوز حصة الـ API المجانية. جرّب موديل تاني من الـ dropdown أو فعّل الـ billing.",
      credit: "لا يوجد رصيد على المزوّد. اشحن الـ API key أو اختر موديل مجاني.",
      auth: "مفتاح API غير صالح أو منتهي.",
      network: "تعذّر الاتصال بمزوّد الذكاء الاصطناعي. تأكّد من الاتصال.",
      generic: "الموديل ما قدرش يحلّل الصورة دلوقتي.",
    },
    urgency: {
      emergency: "مراجعة عاجلة فوراً",
      urgent: "مراجعة سريعة",
      routine: "روتيني",
      none: "لا توجد عجلة",
    },
  },
  en: {
    title: "Image Analysis",
    viewFull: "View full",
    confidence: "Confidence",
    findings: "Findings",
    failedTitle: "Analysis failed",
    failedHint: {
      quota: "Free API quota exceeded. Try a different model from the dropdown or enable billing.",
      credit: "Provider account has no credits. Top up or pick a free model.",
      auth: "API key invalid or expired.",
      network: "Could not reach the AI provider. Check your connection.",
      generic: "The model could not analyze the image right now.",
    },
    urgency: {
      emergency: "Urgent Review Needed",
      urgent: "Prompt Review",
      routine: "Routine",
      none: "No urgency detected",
    },
  },
} as const;

/** Map a raw upstream error string onto a human-friendly category. We pattern
 *  match on substrings instead of HTTP codes because different providers
 *  format their errors differently and the backend hands us the raw text. */
function classifyError(err?: string): keyof typeof LABELS.ar.failedHint {
  if (!err) return "generic";
  const lower = err.toLowerCase();
  if (lower.includes("429") || lower.includes("quota") || lower.includes("rate")) return "quota";
  if (lower.includes("402") || lower.includes("credit") || lower.includes("payment")) return "credit";
  if (lower.includes("401") || lower.includes("403") || lower.includes("api key")) return "auth";
  if (lower.includes("connect") || lower.includes("network") || lower.includes("timeout")) return "network";
  return "generic";
}

const urgencyConfig = {
  emergency: { icon: AlertTriangle, color: "text-emergency", bg: "bg-emergency/10" },
  urgent: { icon: Info, color: "text-urgent", bg: "bg-urgent/10" },
  routine: { icon: CheckCircle, color: "text-routine", bg: "bg-routine/10" },
  none: { icon: Info, color: "text-ink-3", bg: "bg-muted" },
};

export function VisionResultCard({ result, language = "en" }: Props) {
  const [showFull, setShowFull] = useState(false);
  const labels = LABELS[language];
  // When the upstream provider failed (quota, billing, auth, network) we
  // collapse the card into an error state. Showing 0% confidence + the
  // generic English "Vision LLM unavailable" fallback was confusing because
  // it looked like a clinical conclusion ("the image is fine") rather than
  // an infra failure ("the provider is down for this account").
  const hasError = Boolean(result.error);
  const errorKey = classifyError(result.error);
  const uc = hasError ? urgencyConfig.none : urgencyConfig[result.urgency];
  const urgencyLabel = hasError ? labels.failedTitle : labels.urgency[result.urgency];
  const Icon = uc.icon;
  const pct = Math.round(result.confidence * 100);

  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 8 },
        visible: { opacity: 1, y: 0 },
      }}
      initial="hidden"
      animate="visible"
      transition={springSmooth}
      className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm"
    >
      {/* Header */}
      <div className={`flex items-center gap-3 px-4 py-3 ${uc.bg}`}>
        <ImageIcon className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-semibold text-foreground">{labels.title}</span>
        <div className={`ml-auto flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${uc.bg}`}>
          <Icon className={`h-3 w-3 ${uc.color}`} />
          <span className={uc.color}>{urgencyLabel}</span>
        </div>
      </div>

      {/* Image thumbnail */}
      {result.imageUrl && (
        <div className="relative h-32 w-full">
          <Image
            src={result.imageUrl}
            alt="Analyzed"
            fill
            className="object-cover cursor-pointer"
            onClick={() => setShowFull(true)}
            unoptimized
          />
          <button
            type="button"
            onClick={() => setShowFull(true)}
            className="absolute bottom-2 right-2 flex items-center gap-1 rounded-lg bg-black/60 px-2 py-1 text-[11px] text-white"
          >
            <Eye className="h-3 w-3" /> {labels.viewFull}
          </button>
        </div>
      )}

      <div className="px-4 py-3 space-y-2.5">
        {hasError ? (
          // Failure path — replace the confidence/findings UI with a clear
          // explanation so the patient knows what went wrong and how to fix
          // it (switch model, top up credits, retry later).
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/30">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600 dark:text-amber-400" />
              <div className="flex-1 space-y-1">
                <p className="text-xs font-semibold text-amber-900 dark:text-amber-200">
                  {labels.failedHint[errorKey]}
                </p>
                {result.error && (
                  <details className="text-[10px] text-amber-800/80 dark:text-amber-300/70">
                    <summary className="cursor-pointer select-none">Technical details</summary>
                    <pre className="mt-1 whitespace-pre-wrap break-words font-mono text-[10px]">
                      {result.error.slice(0, 400)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Confidence bar */}
            <div>
              <div className="flex justify-between text-[11px] text-muted-foreground mb-1">
                <span>{labels.confidence}</span>
                <span className="tabular-nums">{pct}%</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
              </div>
            </div>

            {/* Findings */}
            {result.findings.length > 0 && (
              <div>
                <span className="text-[11px] font-semibold text-muted-foreground uppercase">{labels.findings}</span>
                <ul className="mt-1 space-y-0.5">
                  {result.findings.map((f, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-[13px] text-foreground">
                      <span className="mt-1.5 w-1 h-1 rounded-full bg-primary flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {/* Disclaimer — positioned as a small scope footer, not a screaming
            warning. The previous emergency-styled box with the alert icon
            made the whole card read like "this tool is useless, go away".
            Now it's a one-liner in muted text — present for the legal
            scope statement, invisible enough that the findings dominate. */}
        {result.disclaimer && (
          <p className="text-[10px] leading-relaxed text-muted-foreground/60 italic pt-1 border-t border-border/40">
            {result.disclaimer}
          </p>
        )}
      </div>

      {/* Full image modal */}
      {showFull && result.imageUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setShowFull(false)}
        >
          <Image
            src={result.imageUrl}
            alt="Full size"
            width={1200}
            height={1200}
            className="max-h-[90vh] max-w-full rounded-xl object-contain"
            style={{ width: "auto", height: "auto" }}
            unoptimized
          />
        </div>
      )}
    </motion.div>
  );
}
