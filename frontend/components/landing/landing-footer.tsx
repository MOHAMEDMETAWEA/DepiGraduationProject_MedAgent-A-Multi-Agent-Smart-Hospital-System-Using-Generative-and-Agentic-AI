import { BrandLogo } from "@/components/layout/brand-logo";

const FOOTER_LINKS = [
  {
    title: "Product",
    links: ["Features", "How it works", "Triage levels"],
  },
  {
    title: "Trust",
    links: ["Safety", "Privacy", "Disclaimer"],
  },
];

export function LandingFooter() {
  return (
    <footer className="border-t border-border bg-card/40 px-4 py-12 sm:px-6">
      <div className="mx-auto max-w-5xl">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.5fr_1fr_1fr]">
          <div>
            <BrandLogo size="md" href={null} />
            <p className="mt-3 max-w-xs text-sm leading-relaxed text-muted-foreground">
              Bilingual AI medical triage built for Arabic and English speakers.
            </p>
          </div>
          {FOOTER_LINKS.map((col) => (
            <div key={col.title}>
              <h6 className="mb-3 text-xs font-bold uppercase tracking-wider text-foreground">
                {col.title}
              </h6>
              <ul className="flex flex-col gap-2">
                {col.links.map((l) => (
                  <li key={l}>
                    <span className="cursor-default text-sm text-muted-foreground">
                      {l}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-10 flex flex-col items-start justify-between gap-3 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center">
          <span>
            For educational use only. Not medical advice. © {new Date().getFullYear()} MedAgent.
          </span>
          <span className="font-mono">Cairo · العربية / EN</span>
        </div>
      </div>
    </footer>
  );
}
