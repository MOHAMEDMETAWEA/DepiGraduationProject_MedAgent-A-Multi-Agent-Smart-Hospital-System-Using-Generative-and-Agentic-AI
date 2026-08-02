"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/src/i18n/navigation";
import { Globe } from "lucide-react";
import { useTransition } from "react";

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("language");
  const [isPending, startTransition] = useTransition();

  const switchLocale = () => {
    const newLocale = locale === "ar" ? "en" : "ar";
    startTransition(() => {
      router.replace(pathname, { locale: newLocale });
    });
  };

  return (
    <button
      type="button"
      onClick={switchLocale}
      disabled={isPending}
      aria-label={t("switch")}
      className="inline-flex h-9 items-center gap-1.5 rounded-full border border-border bg-card px-3 text-sm font-semibold text-foreground transition-colors hover:border-primary hover:bg-primary-tint hover:text-primary disabled:opacity-50"
    >
      <Globe className="h-4 w-4" />
      <span className="tabular-nums">{locale === "ar" ? "EN" : "ع"}</span>
    </button>
  );
}
