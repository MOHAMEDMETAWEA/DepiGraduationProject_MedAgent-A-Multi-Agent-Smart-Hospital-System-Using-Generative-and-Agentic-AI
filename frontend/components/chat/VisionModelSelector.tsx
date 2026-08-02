"use client";

import { Eye, ChevronDown, Check } from "lucide-react";
import { useEffect, useRef, useState } from "react";

/**
 * The 4 vision backends we expose in the UI. Each row is `(provider, model)`
 * because each provider only serves models on its own endpoint — sending
 * `meta-llama/...` to Gemini's API returns 404 and the call fails silently.
 *
 * Order matters: the *first* row is the default + recommended option for
 * medical imaging. Adding a row is a one-line change; the corresponding
 * backend branch is in `_create_vision_provider()`.
 */
export type VisionProviderId = "gemini" | "groq" | "openai" | "openrouter";

export type VisionOption = {
  provider: VisionProviderId;
  model: string;
  label: string;
  hint: string;
};

export const VISION_OPTIONS: VisionOption[] = [
  // Order = priority for the user. First option is the safest free path.
  // Each row is curated to actually work with the keys in backend/.env:
  // Groq (free tier active), OpenAI (paid key with credit), Gemini 1.5
  // Flash (free tier wider than 2.0/2.5 which often shows limit:0), and
  // an OpenRouter free Llama vision (no OpenRouter credit required).
  {
    provider: "groq",
    model: "meta-llama/llama-4-scout-17b-16e-instruct",
    label: "Llama 4 Scout",
    hint: "Groq · مجاني، سريع جدًا، structured output متوسط",
  },
  {
    provider: "openai",
    model: "gpt-4o",
    label: "GPT-4o",
    hint: "OpenAI · مدفوع، أعلى دقة في الطب",
  },
  {
    provider: "gemini",
    model: "gemini-1.5-flash",
    label: "Gemini 1.5 Flash",
    hint: "Google · مجاني، quota أكبر من 2.0/2.5",
  },
  {
    provider: "openrouter",
    model: "meta-llama/llama-3.2-11b-vision-instruct:free",
    label: "Llama 3.2 Vision",
    hint: "OpenRouter · مجاني تمامًا، خفيف",
  },
];

const sameOption = (a: VisionOption, b: VisionOption) =>
  a.provider === b.provider && a.model === b.model;

type Props = {
  /** One or more selected vision options. The array is guaranteed non-empty
   *  by the parent — the selector enforces that the last item can't be
   *  unchecked, so a chat always has at least one vision backend. */
  value: VisionOption[];
  onChange: (options: VisionOption[]) => void;
  disabled?: boolean;
};

/**
 * Multi-select dropdown for the vision backend used by `analyze_vision`.
 * When the user picks 2+ rows AND attaches an image, the chat page fans
 * out N parallel requests so the patient can A/B/C the same image across
 * different vision LLMs and see whose findings are most credible. We
 * forbid deselecting the last item so the conversation always has a
 * working vision backend.
 */
export function VisionModelSelector({ value, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const toggle = (opt: VisionOption) => {
    const isOn = value.some((v) => sameOption(v, opt));
    if (isOn) {
      // Refuse to drop the last selection — otherwise an attached image
      // would have no vision backend to call.
      if (value.length === 1) return;
      onChange(value.filter((v) => !sameOption(v, opt)));
    } else {
      // Preserve VISION_OPTIONS order so the same set always renders in the
      // same sequence in the dropdown and the compare panels.
      const next = [...value, opt];
      next.sort(
        (a, b) =>
          VISION_OPTIONS.findIndex((o) => sameOption(o, a)) -
          VISION_OPTIONS.findIndex((o) => sameOption(o, b)),
      );
      onChange(next);
    }
  };

  const label =
    value.length === 1
      ? value[0].label
      : value.length === VISION_OPTIONS.length
        ? `All vision (${VISION_OPTIONS.length})`
        : `${value.length} vision models`;

  const isCompare = value.length > 1;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        disabled={disabled}
        title="موديل تحليل الصور — اختر اتنين أو أكتر للمقارنة"
        className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer disabled:opacity-50"
      >
        <Eye className="h-3.5 w-3.5 text-muted-foreground/60 flex-shrink-0" />
        <span className="truncate max-w-[160px]">{label}</span>
        {isCompare && (
          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-sky-100 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300">
            Compare
          </span>
        )}
        <ChevronDown
          className={`h-3 w-3 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-2 z-50 w-72 rounded-xl border border-border bg-popover shadow-lg py-2">
          <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Vision model · اختر للمقارنة
          </div>
          {VISION_OPTIONS.map((opt) => {
            const checked = value.some((v) => sameOption(v, opt));
            const isLastChecked = checked && value.length === 1;
            return (
              <button
                key={`${opt.provider}:${opt.model}`}
                type="button"
                onClick={() => toggle(opt)}
                disabled={isLastChecked}
                title={isLastChecked ? "لازم تسيب موديل واحد على الأقل مُحدّد" : undefined}
                className="flex items-start gap-2 w-full px-3 py-2 text-left hover:bg-muted transition-colors disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span
                  className={`mt-0.5 grid place-items-center w-4 h-4 rounded border flex-shrink-0 transition-colors ${
                    checked
                      ? "bg-primary border-primary text-primary-foreground"
                      : "border-border"
                  }`}
                >
                  {checked && <Check className="h-2.5 w-2.5" />}
                </span>
                <span className="flex flex-col">
                  <span className="text-xs text-foreground">{opt.label}</span>
                  <span className="text-[10px] text-muted-foreground">{opt.hint}</span>
                </span>
              </button>
            );
          })}
          <div className="border-t border-border mt-1 pt-1">
            <button
              type="button"
              onClick={() =>
                onChange(
                  value.length === VISION_OPTIONS.length
                    ? [VISION_OPTIONS[0]]
                    : [...VISION_OPTIONS],
                )
              }
              className="flex items-center gap-2 w-full px-3 py-2 text-[11px] font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              {value.length === VISION_OPTIONS.length ? "Deselect all" : "Select all"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
