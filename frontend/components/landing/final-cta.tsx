"use client";

import { ArrowRight } from "lucide-react";
import { useLocale } from "next-intl";

import { Link } from "@/src/i18n/navigation";

export function FinalCta() {
  const locale = useLocale();
  const isRtl = locale === "ar";

  return (
    <section className="px-4 pb-16 pt-8 sm:px-6 sm:pb-24">
      <div className="mx-auto max-w-5xl">
        <div className="mx-auto max-w-2xl rounded-2xl border border-border bg-card p-8 text-center shadow-[var(--shadow-1)] sm:p-12">
          <h2 className="display text-[clamp(1.75rem,3vw,2.5rem)] leading-tight tracking-tight text-foreground">
            Get help understanding your symptoms.
          </h2>
          <p className="mx-auto mt-3 max-w-md text-base leading-relaxed text-muted-foreground sm:text-lg">
            Free to use. No credit card required. Start a triage conversation in Arabic or English.
          </p>
          <div className="mt-8">
            <Link
              href="/register"
              className="btn-primary inline-flex h-12 items-center justify-center gap-2 rounded-full px-7 text-[15px] font-semibold"
            >
              Start a free triage
              <ArrowRight className={`h-4 w-4 ${isRtl ? "rtl-flip" : ""}`} />
            </Link>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Not a replacement for professional medical care.
          </p>
        </div>
      </div>
    </section>
  );
}
