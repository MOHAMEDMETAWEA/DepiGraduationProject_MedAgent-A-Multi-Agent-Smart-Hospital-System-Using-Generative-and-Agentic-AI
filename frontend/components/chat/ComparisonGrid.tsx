"use client";

import type { ChatEvent } from "@/lib/api/chat";
import { Clock, Zap, AlertTriangle, Activity, Stethoscope } from "lucide-react";

export type ModelResult = {
  model: string;
  modelLabel: string;
  response: string;
  events: ChatEvent[];
  latencyMs: number;
  tokenCount: number;
  triageLevel: string | null;
  redFlag: boolean;
  error?: string;
};

type Props = {
  results: ModelResult[];
  streaming?: boolean;
};

const triageBadge: Record<string, string> = {
  emergency: "bg-red-100 text-red-700 border-red-200",
  urgent: "bg-amber-100 text-amber-700 border-amber-200",
  routine: "bg-emerald-100 text-emerald-700 border-emerald-200",
};

const triageColor: Record<string, string> = {
  emergency: "border-l-red-500",
  urgent: "border-l-amber-500",
  routine: "border-l-emerald-500",
};

export function ComparisonGrid({ results, streaming }: Props) {
  if (results.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-3">
      {results.map((r, i) => (
        <ModelCard key={i} result={r} loading={streaming && !r.response && !r.error} />
      ))}
    </div>
  );
}

function ModelCard({ result, loading }: { result: ModelResult; loading?: boolean }) {
  const triage = result.triageLevel;

  return (
    <div className={`flex flex-col rounded-xl border border-border bg-card overflow-hidden shadow-sm ${
      triage ? triageColor[triage] || "" : ""
    } ${triage ? "border-l-2" : ""}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-muted/40 border-b border-border">
        <div className="flex items-center gap-1.5 min-w-0">
          <Stethoscope className="h-3 w-3 text-muted-foreground flex-shrink-0" />
          <span className="text-[11px] font-semibold text-foreground truncate">
            {result.modelLabel}
          </span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {result.redFlag && (
            <AlertTriangle className="h-3 w-3 text-red-500" />
          )}
          {triage && (
            <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full border ${triageBadge[triage] || "bg-muted"}`}>
              {triage}
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 px-3 py-2.5 min-h-[80px]">
        {loading ? (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce" />
            <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "0.15s" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "0.3s" }} />
          </div>
        ) : result.error ? (
          <p className="text-[12px] text-red-500">{result.error}</p>
        ) : (
          <p className="text-[12px] leading-relaxed text-foreground whitespace-pre-wrap">
            {result.response || "—"}
          </p>
        )}
      </div>

      {/* Footer — metrics */}
      <div className="flex items-center gap-3 px-3 py-1.5 border-t border-border/60 bg-muted/30 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <Clock className="h-2.5 w-2.5" />
          {result.latencyMs > 0 ? `${(result.latencyMs / 1000).toFixed(1)}s` : "—"}
        </span>
        <span className="flex items-center gap-1">
          <Zap className="h-2.5 w-2.5" />
          {result.tokenCount > 0 ? `${result.tokenCount} tok` : "—"}
        </span>
        {triage && (
          <span className="flex items-center gap-1 ml-auto">
            <Activity className="h-2.5 w-2.5" />
            {triage}
          </span>
        )}
      </div>
    </div>
  );
}
