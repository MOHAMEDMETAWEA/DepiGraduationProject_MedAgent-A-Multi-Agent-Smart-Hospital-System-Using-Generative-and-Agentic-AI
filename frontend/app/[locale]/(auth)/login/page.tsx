"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Lock, Mail } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthAlert, AuthField, AuthSubmit } from "@/components/auth/auth-fields";
import { AuthShell } from "@/components/auth/auth-shell";
import { authApi } from "@/lib/api/auth";
import { Link, useRouter } from "@/src/i18n/navigation";
import { useAuthStore } from "@/store/auth";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const t = useTranslations("auth.login");
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [error, setError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (data: LoginForm) => {
    setError("");
    const res = await authApi.login(data);
    if (res.error) {
      setError(res.error);
      return;
    }
    setAuth(res.data!.user, res.data!.access_token, res.data!.refresh_token);
    router.push("/chat");
  };

  return (
    <AuthShell
      title={t("title")}
      subtitle={t("subtitle")}
      footer={
        <span>
          {t("noAccount")}{" "}
          <Link href="/register" className="font-semibold text-primary hover:underline">
            {t("createAccount")}
          </Link>
        </span>
      }
    >
      {error && <AuthAlert>{error}</AuthAlert>}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />

        <div className="flex justify-end">
          <Link href="/forgot-password" className="text-sm font-medium text-primary hover:underline">
            {t("forgotPassword")}
          </Link>
        </div>

        <AuthSubmit loading={isSubmitting} loadingLabel={t("submitting")}>
          {t("submit")}
        </AuthSubmit>
      </form>
    </AuthShell>
  );
}
