"use client";

import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, HelpCircle, Info } from "lucide-react";

type ConfidenceLevel = "high" | "medium" | "low" | "none";

interface ConfidenceBadgeProps {
  band: ConfidenceLevel;
  className?: string;
}

const badgeConfig: Record<
  ConfidenceLevel,
  {
    icon: typeof Info;
    label: string;
    className: string;
  }
> = {
  high: {
    icon: CheckCircle2,
    label: "High confidence",
    className: "text-emerald-600 bg-emerald-50 border-emerald-200 dark:text-emerald-400 dark:bg-emerald-950/30 dark:border-emerald-800/50",
  },
  medium: {
    icon: HelpCircle,
    label: "Medium confidence",
    className: "text-amber-600 bg-amber-50 border-amber-200 dark:text-amber-400 dark:bg-amber-950/30 dark:border-amber-800/50",
  },
  low: {
    icon: AlertTriangle,
    label: "Low confidence",
    className: "text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-950/30 dark:border-red-800/50",
  },
  none: {
    icon: Info,
    label: "",
    className: "hidden",
  },
};

export function ConfidenceBadge({ band, className }: ConfidenceBadgeProps) {
  const config = badgeConfig[band];
  const Icon = config.icon;

  if (band === "high" || band === "none") return null;

  return (
    <span
      role="status"
      aria-label={config.label}
      className={cn(
        "inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] font-semibold rounded-full border",
        config.className,
        className,
      )}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      <span>{config.label}</span>
    </span>
  );
}
