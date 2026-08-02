"use client";

import { SAFETY_GATES } from "@/lib/data/landing";

export function SafetySection() {
  return (
    <section id="trust" className="px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-5xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="display text-[clamp(1.5rem,2.5vw,2.25rem)] leading-tight tracking-tight text-foreground">
            Your safety comes first
          </h2>
          <p className="mt-3 text-base leading-relaxed text-muted-foreground sm:text-lg">
            Every response passes through multiple safety checks before it reaches you.
          </p>
        </div>

        {/* Timeline */}
        <div className="relative mt-12">
          {/* Horizontal line — desktop */}
          <div
            aria-hidden
            className="absolute start-0 end-0 top-5 hidden h-px bg-border sm:block"
          />

          <div className="grid gap-6 sm:grid-cols-5">
            {SAFETY_GATES.map((gate, i) => (
              <div key={gate} className="relative z-10 flex flex-col items-center text-center">
                <div className="grid h-10 w-10 place-items-center rounded-full border border-border bg-card font-display text-sm font-bold text-primary shadow-[var(--shadow-1)]">
                  {String(i + 1).padStart(2, "0")}
                </div>
                <p className="mt-3 text-sm font-medium text-foreground">{gate}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mx-auto mt-12 max-w-2xl text-center">
          <p className="text-xs leading-relaxed text-muted-foreground">
            MedAgent is an educational decision-support tool. It does not replace a licensed clinician and is not certified for regulated healthcare use. If you are experiencing a medical emergency, call your local emergency number immediately.
          </p>
        </div>
      </div>
    </section>
  );
}
