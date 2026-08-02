"use client";

import { FEATURES } from "@/lib/data/landing";

export function FeatureGrid() {
  return (
    <section className="px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-5xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="display text-[clamp(1.5rem,2.5vw,2.25rem)] leading-tight tracking-tight text-foreground">
            Why patients trust MedAgent
          </h2>
          <p className="mt-3 text-base leading-relaxed text-muted-foreground sm:text-lg">
            Built for accuracy, designed for your peace of mind.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-3">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="rounded-xl border border-border bg-card p-6 shadow-[var(--shadow-1)] transition-colors hover:border-primary/20"
              >
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-primary/20 bg-primary-tint text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="font-display text-base font-semibold text-foreground">
                  {f.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {f.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
