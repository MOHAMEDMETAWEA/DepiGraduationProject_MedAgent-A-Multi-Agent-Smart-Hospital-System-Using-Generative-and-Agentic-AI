"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { AuthAlert, AuthField, AuthSubmit } from "@/components/auth/auth-fields";
import { AuthShell } from "@/components/auth/auth-shell";
import { authApi } from "@/lib/api/auth";
import { Link } from "@/src/i18n/navigation";

export default function ResetPasswordPage() {
  const t = useTranslations("auth.reset");
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError("Missing reset token.");
      return;
    }
    setError("");
    setSubmitting(true);
    const res = await authApi.resetPassword(token, password);
    setSubmitting(false);
    if (res.error) {
      setError(res.error);
      return;
    }
    setDone(true);
  };

  if (done) {
    return (
      <div className="relative flex min-h-screen items-center justify-center px-4">
        <div className="pointer-events-none fixed inset-0 -z-10 bg-mesh" />
        <motion.div
          initial={{ scale: 0.92, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 240, damping: 22 }}
          className="text-center"
        >
          <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <h1 className="font-display text-2xl font-bold text-foreground">{t("successTitle")}</h1>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">{t("successDesc")}</p>
          <Link
            href="/login"
            className="btn-primary mt-7 inline-flex h-11 items-center justify-center rounded-full px-6 text-sm font-semibold no-underline"
          >
            {t("successCta")}
          </Link>
        </motion.div>
      </div>
    );
  }

  return (
    <AuthShell title={t("title")} subtitle={t("subtitle")}>
      {error && <AuthAlert>{error}</AuthAlert>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <AuthField
          label={t("password")}
          type="password"
          placeholder={t("passwordPlaceholder")}
          icon={Lock}
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <AuthSubmit loading={submitting} loadingLabel={t("submitting")}>
          {t("submit")}
        </AuthSubmit>
      </form>
    </AuthShell>
  );
}
