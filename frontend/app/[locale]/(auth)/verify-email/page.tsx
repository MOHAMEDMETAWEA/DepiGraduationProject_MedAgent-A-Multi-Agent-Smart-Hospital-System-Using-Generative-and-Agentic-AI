"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { authApi } from "@/lib/api/auth";
import { Link } from "@/src/i18n/navigation";

type Status = "loading" | "success" | "error";

export default function VerifyEmailPage() {
  const t = useTranslations("auth.verify");
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<Status>("loading");

  // Verify the email token on mount. Both branches (missing token error +
  // async API result) require flipping local status state from an effect.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      return;
    }
    authApi.verifyEmail(token).then((res) => {
      setStatus(res.error ? "error" : "success");
    });
  }, [searchParams]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const config = {
    loading: {
      Icon: Loader2,
      iconClass: "animate-spin text-primary",
      bgClass: "bg-primary-tint",
      title: t("loadingTitle"),
      desc: t("loadingDesc"),
    },
    success: {
      Icon: CheckCircle2,
      iconClass: "text-emerald-500",
      bgClass: "bg-emerald-500/15",
      title: t("successTitle"),
      desc: t("successDesc"),
    },
    error: {
      Icon: XCircle,
      iconClass: "text-destructive",
      bgClass: "bg-destructive/10",
      title: t("errorTitle"),
      desc: t("errorDesc"),
    },
  }[status];

  const { Icon } = config;

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-mesh" />
      <motion.div
        key={status}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="text-center"
      >
        <div className={`mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl ${config.bgClass}`}>
          <Icon className={`h-8 w-8 ${config.iconClass}`} />
        </div>
        <h1 className="font-display text-2xl font-bold text-foreground">{config.title}</h1>
        <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">{config.desc}</p>
        {status !== "loading" && (
          <Link
            href="/login"
            className="btn-primary mt-7 inline-flex h-11 items-center justify-center rounded-full px-6 text-sm font-semibold no-underline"
          >
            {t("cta")}
          </Link>
        )}
      </motion.div>
    </div>
  );
}
