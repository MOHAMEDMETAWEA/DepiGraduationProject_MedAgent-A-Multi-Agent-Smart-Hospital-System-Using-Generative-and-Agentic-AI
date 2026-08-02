"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/layout/theme-provider";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const t = useTranslations("theme");
  const [mounted, setMounted] = useState(false);

  // Hydration guard: render an invisible placeholder during SSR to avoid
  // theme-icon flash. setMounted in effect is the standard React pattern here.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div aria-hidden className="h-9 w-9" />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={t("toggle")}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card text-foreground transition-colors hover:border-primary hover:bg-primary-tint hover:text-primary"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
