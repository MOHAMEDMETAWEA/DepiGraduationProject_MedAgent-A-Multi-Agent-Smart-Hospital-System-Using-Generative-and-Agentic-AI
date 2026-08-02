"use client";

import { AlertTriangle, ChevronDown, ChevronUp, Stethoscope } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

interface Branch {
  hypothesis: string;
  probability: number;
  reasoning: string;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  recommended_action: string;
  urgency: "emergency" | "urgent" | "routine";
  color: string;
}

interface DifferentialPanelProps {
  branches: Branch[];
  /**
   * Conversation/user language — drives the panel's labels (Clinical reasoning,
   * Supporting evidence, …) independent of the URL locale. Defaults to "ar"
   * since Arabic is the platform's primary language.
   */
  language?: "ar" | "en";
}

// Static label map — chosen so the labels match the language of the AI-generated
// content (hypothesis text, reasoning, evidence) which lives in the same branch.
const LABELS: Record<
  "ar" | "en",
  {
    title: string;
    hypotheses: (count: number) => string;
    reasoning: string;
    supportingEvidence: string;
    contradictingEvidence: string;
    recommendedPrefix: string;
    likelihood: (p: number) => string;
  }
> = {
  ar: {
    title: "التشخيص التفريقي",
    hypotheses: (n) =>
      n === 0
        ? "لا توجد فرضيات"
        : n === 1
          ? "فرضية واحدة"
          : n === 2
            ? "فرضيتان"
            : `${n} فرضيات`,
    reasoning: "الاستدلال السريري",
    supportingEvidence: "أدلة مؤيدة",
    contradictingEvidence: "أدلة مخالفة",
    recommendedPrefix: "التوصية:",
    // UX1: show qualitative likelihood, not a false-precision percentage.
    // The bar chart still encodes magnitude visually.
    likelihood: (p) =>
      p >= 0.6
        ? "احتمال مرتفع"
        : p >= 0.35
          ? "احتمال متوسط"
          : p >= 0.15
            ? "ممكن"
            : "أقل احتمالاً",
  },
  en: {
    title: "Differential diagnosis",
    hypotheses: (n) => (n === 1 ? "1 hypothesis" : `${n} hypotheses`),
    reasoning: "Clinical reasoning",
    supportingEvidence: "Supporting evidence",
    contradictingEvidence: "Contradicting evidence",
    recommendedPrefix: "Recommended:",
    likelihood: (p) =>
      p >= 0.6
        ? "High likelihood"
        : p >= 0.35
          ? "Moderate likelihood"
          : p >= 0.15
            ? "Possible"
            : "Less likely",
  },
};

function BranchCard({
  branch,
  index,
  labels,
}: {
  branch: Branch;
  index: number;
  labels: (typeof LABELS)["ar"];
}) {
  const [expanded, setExpanded] = useState(index === 0);
  const pct = Math.round(branch.probability * 100);
  const likelihoodLabel = labels.likelihood(branch.probability);

  return (
    <div
      className="rounded-xl border bg-card shadow-sm overflow-hidden transition-colors"
      style={{ borderColor: `${branch.color}40` }}
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-start hover:bg-muted/50 transition-colors"
      >
        <span
          className="flex-shrink-0 w-8 h-8 rounded-full grid place-items-center text-xs font-bold text-white shadow-sm"
          style={{ backgroundColor: branch.color }}
        >
          {index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground truncate">
              {branch.hypothesis}
            </span>
            {branch.urgency === "emergency" && (
              <AlertTriangle className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />
            )}
          </div>
          {/* Confidence bar — visual cue only; no number to imply precision. */}
          <div className="mt-2 w-full h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${pct}%`,
                backgroundColor: branch.color,
              }}
              // Keep the raw % accessible to screen readers + on hover for
              // clinicians, but don't show it as a headline number.
              title={`${pct}%`}
              aria-label={`${likelihoodLabel} (${pct}%)`}
            />
          </div>
        </div>
        <span
          className="text-[11px] font-semibold flex-shrink-0 whitespace-nowrap"
          style={{ color: branch.color }}
        >
          {likelihoodLabel}
        </span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-border pt-3">
          {/* Reasoning */}
          <div>
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
              {labels.reasoning}
            </span>
            <p className="mt-1 text-[13px] leading-relaxed text-foreground">
              {branch.reasoning}
            </p>
          </div>

          {/* Supporting evidence */}
          {branch.supporting_evidence.length > 0 && (
            <div>
              <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wide">
                {labels.supportingEvidence}
              </span>
              <ul className="mt-1 space-y-0.5">
                {branch.supporting_evidence.map((e, i) => (
                  <li
                    key={i}
                    className="text-[13px] text-foreground flex items-start gap-1.5"
                  >
                    <span className="mt-1.5 w-1 h-1 rounded-full bg-emerald-500 flex-shrink-0" />
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Contradicting evidence */}
          {branch.contradicting_evidence.length > 0 && (
            <div>
              <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wide">
                {labels.contradictingEvidence}
              </span>
              <ul className="mt-1 space-y-0.5">
                {branch.contradicting_evidence.map((e, i) => (
                  <li
                    key={i}
                    className="text-[13px] text-foreground flex items-start gap-1.5"
                  >
                    <span className="mt-1.5 w-1 h-1 rounded-full bg-amber-500 flex-shrink-0" />
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommended action */}
          <div
            className={cn(
              "rounded-lg px-3 py-2 text-[13px] font-medium flex items-start gap-1.5",
            )}
            style={{
              backgroundColor: `${branch.color}15`,
              color: branch.color,
            }}
          >
            <span className="font-semibold">{labels.recommendedPrefix}</span>
            <span className="flex-1">{branch.recommended_action}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export function DifferentialPanel({ branches, language = "ar" }: DifferentialPanelProps) {
  const labels = LABELS[language];
  if (!branches || branches.length === 0) return null;

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm">
      <div className="flex items-center gap-2 px-4 py-3 bg-[linear-gradient(135deg,#4F46E5,#7C3AED)]">
        <Stethoscope className="h-4 w-4 text-white" />
        <span className="text-sm font-semibold text-white">
          {labels.title} — {labels.hypotheses(branches.length)}
        </span>
      </div>
      <div className="p-3 space-y-2">
        {branches.map((branch, i) => (
          <BranchCard key={i} branch={branch} index={i} labels={labels} />
        ))}
      </div>
    </div>
  );
}
