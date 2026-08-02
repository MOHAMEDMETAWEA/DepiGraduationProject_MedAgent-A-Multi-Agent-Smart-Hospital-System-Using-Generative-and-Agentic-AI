"use client";

import { motion } from "framer-motion";
import { Mail, ShieldCheck, User as UserIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/store/auth";

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user);
  const t = useTranslations("profile");
  const tCommon = useTranslations("common");

  const initials = (user?.full_name ?? "U")
    .split(" ")
    .map((s) => s[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const fields: Array<{ label: string; value: string | undefined; icon: typeof Mail }> = [
    { label: t("fullName"), value: user?.full_name, icon: UserIcon },
    { label: t("email"), value: user?.email, icon: Mail },
    {
      label: t("role"),
      value: user?.role ? tCommon(user.role as "patient" | "doctor" | "admin") : undefined,
      icon: ShieldCheck,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground sm:text-3xl">{t("title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {/* Hero card */}
      <Card className="overflow-hidden">
        <div className="relative h-28 bg-mesh">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/15 via-primary/5 to-transparent" />
        </div>
        <div className="-mt-12 px-5 pb-5 sm:px-7">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <span className="brand-mark grid h-24 w-24 shrink-0 place-items-center rounded-2xl border-4 border-card text-2xl font-bold text-white">
              {initials}
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="font-display text-xl font-bold text-foreground">{user?.full_name ?? "—"}</h2>
              <p className="truncate text-sm text-muted-foreground">{user?.email ?? "—"}</p>
            </div>
            <span className="inline-flex h-8 items-center self-start rounded-full bg-primary-tint px-3 text-xs font-semibold uppercase tracking-wide text-primary sm:self-end">
              {user?.role && tCommon(user.role as "patient" | "doctor" | "admin")}
            </span>
          </div>
        </div>
      </Card>

      {/* Personal info */}
      <Card>
        <CardHeader>
          <CardTitle>{t("personalInfo")}</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2">
            {fields.map(({ label, value, icon: Icon }) => (
              <div
                key={label}
                className="flex items-start gap-3 rounded-xl border border-border bg-secondary/40 p-4"
              >
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary-tint text-primary">
                  <Icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    {label}
                  </dt>
                  <dd className="mt-0.5 truncate text-sm font-medium text-foreground">{value ?? "—"}</dd>
                </div>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </motion.div>
  );
}
