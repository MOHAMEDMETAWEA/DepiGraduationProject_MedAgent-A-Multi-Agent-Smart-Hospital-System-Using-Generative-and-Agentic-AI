"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";

import { BrandLogo } from "@/components/layout/brand-logo";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { ThemeToggle } from "@/components/layout/theme-toggle";

type Props = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
  maxWidth?: "sm" | "md" | "lg";
};

const widthClass = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
};

export function AuthShell({ title, subtitle, children, footer, maxWidth = "md" }: Props) {
  return (
    <div className="relative flex min-h-screen flex-col">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-mesh" />

      <header className="flex items-center justify-between px-4 py-4 sm:px-6">
        <BrandLogo size="md" />
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 pb-12 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className={`w-full ${widthClass[maxWidth]}`}
        >
          <div className="mb-8 text-center">
            <h1 className="font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl">{title}</h1>
            {subtitle && <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>}
          </div>

          <div className="rounded-[24px] border border-border bg-card/80 p-6 shadow-[var(--shadow-1)] backdrop-blur-md sm:p-7">
            {children}
          </div>

          {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
        </motion.div>
      </main>
    </div>
  );
}
