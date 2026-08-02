"use client";

import { STEPS } from "@/lib/data/landing";

export function HowItWorks() {
  return (
    <section id="how" className="px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-5xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="display text-[clamp(1.5rem,2.5vw,2.25rem)] leading-tight tracking-tight text-foreground">
            How it works
          </h2>
          <p className="mt-3 text-base leading-relaxed text-muted-foreground sm:text-lg">
            Three simple steps to a clearer next step.
          </p>
        </div>

        <div className="relative mt-12 grid gap-8 sm:grid-cols-3">
          {/* Connecting line — desktop only */}
          <div
            aria-hidden
            className="absolute start-0 end-0 top-8 hidden h-px bg-border sm:block"
          />

          {STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={i} className="relative z-10 flex flex-col items-center text-center">
                <div className="mb-4 grid h-16 w-16 place-items-center rounded-full border border-border bg-card shadow-[var(--shadow-1)]">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-display text-base font-semibold text-foreground">
                  {step.title}
                </h3>
                <p className="mt-1.5 max-w-[16rem] text-sm leading-relaxed text-muted-foreground">
                  {step.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
