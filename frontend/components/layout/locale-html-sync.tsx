"use client";

import { useEffect } from "react";

/**
 * Keeps <html lang> and <html dir> in sync with the current locale during
 * client-side navigation. The root layout sets the initial SSR values, but
 * doesn't re-render when the locale changes — so without this component,
 * switching from /  ↔ /en leaves the previous direction stuck on <html>.
 */
export function LocaleHtmlSync({ locale }: { locale: string }) {
  useEffect(() => {
    const dir = locale === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = locale;
    document.documentElement.dir = dir;
  }, [locale]);

  return null;
}
