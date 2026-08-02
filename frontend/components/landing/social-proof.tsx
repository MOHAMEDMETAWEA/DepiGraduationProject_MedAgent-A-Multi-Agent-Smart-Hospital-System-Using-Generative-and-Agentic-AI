"use client";

import { Shield, Users, Lock } from "lucide-react";

const PROOFS = [
  { icon: Users, label: "Trusted by patients across Egypt" },
  { icon: Shield, label: "Clinician-reviewed guidance" },
  { icon: Lock, label: "Your data stays private" },
];

export function SocialProof() {
  return (
    <section className="border-y border-border bg-card/40 px-4 py-8 sm:px-6">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-center gap-6 sm:flex-row sm:gap-10">
        {PROOFS.map((p) => {
          const Icon = p.icon;
          return (
            <div key={p.label} className="flex items-center gap-2.5 text-sm text-muted-foreground">
              <Icon className="h-4 w-4 text-primary" />
              <span className="font-medium">{p.label}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
