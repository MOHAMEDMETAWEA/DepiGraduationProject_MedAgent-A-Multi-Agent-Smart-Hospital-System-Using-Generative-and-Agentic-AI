"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "@/src/i18n/navigation";
import { useEffect } from "react";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const router = useRouter();

  useEffect(() => {
    if (isHydrated && !accessToken) {
      router.push("/login");
    }
  }, [isHydrated, accessToken, router]);

  if (!isHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!accessToken) return null;

  return <AppShell>{children}</AppShell>;
}
