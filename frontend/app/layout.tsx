import type { Metadata } from "next";
import { Cairo, Inter, JetBrains_Mono } from "next/font/google";
import { getLocale } from "next-intl/server";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const cairo = Cairo({ subsets: ["arabic"], variable: "--font-cairo", display: "swap" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "MedAgent — Bilingual Medical Triage AI",
  description: "Bilingual Arabic + English medical triage AI assistant. Safe, grounded, and built for Arabic-speaking patients.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <html lang={locale} dir={dir} suppressHydrationWarning>
      <body className={`${inter.variable} ${cairo.variable} ${jetbrains.variable} min-h-screen bg-background font-sans text-foreground antialiased`}>
        {children}
      </body>
    </html>
  );
}
