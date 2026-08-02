"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { CheckCircle2, Lock, Mail, Stethoscope, User } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { AuthAlert, AuthField, AuthSubmit } from "@/components/auth/auth-fields";
import { AuthShell } from "@/components/auth/auth-shell";
import { authApi } from "@/lib/api/auth";
import { Link } from "@/src/i18n/navigation";

const registerSchema = z.object({
  full_name: z.string().min(1),
  email: z.string().email(),
  password: z.string().min(8),
  role: z.enum(["patient", "doctor"]),
  license_number: z.string().optional(),
  specialty: z.string().optional(),
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const t = useTranslations("auth.register");
  const locale = useLocale();
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { isSubmitting, errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: "patient" },
  });

  const role = useWatch({ control, name: "role" });

  const onSubmit = async (data: RegisterForm) => {
    setError("");
    const res = await authApi.register({ ...data, locale });
    if (res.error) {
      setError(res.error);
      return;
    }
    setSuccess(true);
  };

  if (success) {
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
    <AuthShell
      title={t("title")}
      subtitle={t("subtitle")}
      maxWidth="md"
      footer={
        <span>
          {t("haveAccount")}{" "}
          <Link href="/login" className="font-semibold text-primary hover:underline">
            {t("signIn")}
          </Link>
        </span>
      }
    >
      {error && <AuthAlert>{error}</AuthAlert>}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <AuthField
          label={t("fullName")}
          placeholder={t("fullNamePlaceholder")}
          icon={User}
          autoComplete="name"
          error={errors.full_name?.message}
          {...register("full_name")}
        />

        <AuthField
          label={t("email")}
          type="email"
          placeholder={t("emailPlaceholder")}
          icon={Mail}
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />

        <AuthField
          label={t("password")}
          type="password"
          placeholder={t("passwordPlaceholder")}
          icon={Lock}
          autoComplete="new-password"
          error={errors.password?.message}
          {...register("password")}
        />

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">{t("role")}</label>
          <div className="grid grid-cols-2 gap-2">
            {(["patient", "doctor"] as const).map((r) => {
              const active = role === r;
              return (
                <label
                  key={r}
                  className={`flex h-11 cursor-pointer items-center justify-center gap-2 rounded-xl border px-4 text-sm font-semibold transition-all ${
                    active
                      ? "border-primary bg-primary-tint text-primary shadow-[inset_0_0_0_1px_rgb(11_95_255/0.3)]"
                      : "border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground"
                  }`}
                >
                  <input type="radio" value={r} className="sr-only" {...register("role")} />
                  {r === "patient" ? <User className="h-4 w-4" /> : <Stethoscope className="h-4 w-4" />}
                  {t(r)}
                </label>
              );
            })}
          </div>
        </div>

        {role === "doctor" && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="space-y-4 overflow-hidden"
          >
            <AuthField label={t("licenseNumber")} placeholder={t("licenseNumberPlaceholder")} {...register("license_number")} />
            <AuthField label={t("specialty")} placeholder={t("specialtyPlaceholder")} {...register("specialty")} />
          </motion.div>
        )}

        <AuthSubmit loading={isSubmitting} loadingLabel={t("submitting")}>
          {t("submit")}
        </AuthSubmit>
      </form>
    </AuthShell>
  );
}
