"use client";

import { useLocale, useTranslations } from "next-intl";
import { ArrowRight, Menu, X } from "lucide-react";
import { useState } from "react";

import { BrandLogo } from "@/components/layout/brand-logo";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Link } from "@/src/i18n/navigation";

export function LandingNav() {
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const isRtl = locale === "ar";
  const [mobileOpen, setMobileOpen] = useState(false);

  const links = [
    { href: "#how", label: "How it works" },
    { href: "#triage", label: "Triage" },
    { href: "#trust", label: "Safety" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 sm:px-6">
        <BrandLogo size="md" />

        {/* Desktop links */}
        <nav className="hidden items-center gap-1 md:flex">
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Desktop actions */}
        <div className="hidden items-center gap-2 md:flex">
          <LanguageSwitcher />
          <ThemeToggle />
          <span className="mx-1 h-5 w-px bg-border" />
          <Link
            href="/login"
            className="rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            {tCommon("signIn")}
          </Link>
          <Link
            href="/register"
            className="btn-primary inline-flex h-9 items-center justify-center gap-1.5 rounded-full px-4 text-sm font-semibold"
          >
            {tCommon("getStarted")}
            <ArrowRight className={`h-3.5 w-3.5 ${isRtl ? "rtl-flip" : ""}`} />
          </Link>
        </div>

        {/* Mobile menu button */}
        <div className="flex items-center gap-2 md:hidden">
          <LanguageSwitcher />
          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-foreground"
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="border-t border-border bg-background px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-1">
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
            <div className="my-2 h-px bg-border" />
            <Link
              href="/login"
              className="rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
              {tCommon("signIn")}
            </Link>
            <Link
              href="/register"
              className="btn-primary mt-1 inline-flex h-11 items-center justify-center gap-1.5 rounded-full px-4 text-sm font-semibold"
            >
              {tCommon("getStarted")}
              <ArrowRight className={`h-3.5 w-3.5 ${isRtl ? "rtl-flip" : ""}`} />
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
