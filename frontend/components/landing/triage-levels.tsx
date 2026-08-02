"use client";

import { TRIAGE } from "@/lib/data/landing";

export function TriageLevels() {
  return (
    <section id="triage" className="px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-5xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="display text-[clamp(1.5rem,2.5vw,2.25rem)] leading-tight tracking-tight text-foreground">
            Get the right level of care
          </h2>
          <p className="mt-3 text-base leading-relaxed text-muted-foreground sm:text-lg">
            Every symptom gets a clear urgency rating so you know exactly what to do next.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-3">
          {TRIAGE.map((t) => (
            <div
              key={t.level}
              className="relative overflow-hidden rounded-xl border border-border bg-card p-6 shadow-[var(--shadow-1)]"
            >
              {/* Color indicator */}
              <div className={`absolute start-0 top-0 h-full w-1 ${t.barColor}`} />

              <div className="ps-3">
                <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${t.textColor} ${t.bgColor}`}>
                  {t.level}
                </span>
                <h3 className="mt-3 font-display text-lg font-semibold tracking-tight text-foreground">
                  {t.headline}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {t.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
