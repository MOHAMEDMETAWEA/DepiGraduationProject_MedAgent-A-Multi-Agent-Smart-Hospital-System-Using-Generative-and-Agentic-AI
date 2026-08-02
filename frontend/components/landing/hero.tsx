"use client";

import { ArrowRight } from "lucide-react";
import { useLocale } from "next-intl";

import { Link } from "@/src/i18n/navigation";
import { TRUST_PILLS } from "@/lib/data/landing";

export function Hero() {
  const locale = useLocale();
  const isRtl = locale === "ar";

  return (
    <section className="px-4 pb-16 pt-10 sm:px-6 sm:pb-20 sm:pt-14 lg:pb-24 lg:pt-16">
      <div className="mx-auto grid max-w-5xl items-center gap-12 lg:grid-cols-2 lg:gap-16">
        {/* Text */}
        <div className="flex flex-col items-start">
          <span className="eyebrow">Free medical triage · Arabic &amp; English</span>

          <h1 className="display mt-5 text-[clamp(2.25rem,5vw,4rem)] leading-[1.08] tracking-tight text-foreground">
            Medical triage that speaks your language.
          </h1>

          <p className="mt-5 max-w-md text-base leading-relaxed text-muted-foreground sm:text-lg">
            Describe your symptoms in Arabic or English. Get evidence-based guidance and a clear next step in under a minute.
          </p>

          <div className="mt-8 w-full sm:w-auto">
            <Link
              href="/register"
              className="btn-primary inline-flex h-12 w-full items-center justify-center gap-2 rounded-full px-7 text-[15px] font-semibold sm:w-auto"
            >
              Start a free triage
              <ArrowRight className={`h-4 w-4 ${isRtl ? "rtl-flip" : ""}`} />
            </Link>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-2">
            {TRUST_PILLS.map((pill) => (
              <span
                key={pill}
                className="inline-flex items-center rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground"
              >
                {pill}
              </span>
            ))}
          </div>
        </div>

        {/* Visual — clean static chat mockup */}
        <div className="hidden lg:block">
          <div className="relative rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-1)]">
            {/* Mock chat header */}
            <div className="mb-4 flex items-center gap-3 border-b border-border pb-3">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
                M
              </span>
              <div>
                <p className="text-sm font-semibold text-foreground">MedAgent</p>
                <p className="text-xs text-muted-foreground">Medical triage assistant</p>
              </div>
            </div>

            {/* Mock messages */}
            <div className="space-y-3">
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
                  I have a sharp pain on the left side of my chest.
                </div>
              </div>
              <div className="flex justify-start">
                <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-border bg-secondary px-4 py-2.5 text-sm leading-relaxed text-foreground">
                  I understand. Is the pain worse when you breathe deeply, and have you noticed any shortness of breath?
                </div>
              </div>
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
                  Yes to both.
                </div>
              </div>
              <div className="flex justify-start">
                <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-amber-500/30 bg-amber-50 px-4 py-2.5 text-sm leading-relaxed text-foreground dark:bg-amber-950/30">
                  <span className="mb-1 block text-xs font-semibold text-amber-700 dark:text-amber-300">Urgent · Same-day care</span>
                  Please visit the emergency department today for evaluation.
                </div>
              </div>
            </div>

            {/* Mock input */}
            <div className="mt-4 rounded-xl border border-border bg-secondary px-4 py-2.5 text-sm text-muted-foreground">
              Type your symptoms...
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
