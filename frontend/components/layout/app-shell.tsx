"use client";

import { LogOut, Menu, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import { BrandLogo } from "@/components/layout/brand-logo";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { SidebarNav } from "@/components/layout/sidebar";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { SOSButton } from "@/components/emergency/SOSButton";
import { authApi } from "@/lib/api/auth";
import { useRouter, usePathname } from "@/src/i18n/navigation";
import { useAuthStore } from "@/store/auth";

export function AppShell({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const tCommon = useTranslations("common");
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  // Close the mobile sidebar when the route changes. This is an external
  // navigation event reaching us via pathname, not a derived value.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  const handleLogout = async () => {
    if (refreshToken) await authApi.logout(refreshToken);
    clearAuth();
    router.push("/login");
  };

  const initials = (user?.full_name ?? "U")
    .split(" ")
    .map((s) => s[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const isChatPage = pathname.endsWith("/chat") || pathname.includes("/chat/");

  return (
    <div className="flex min-h-screen bg-background">
      {/* Unified sidebar — logo + nav + history(chat only) + profile */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-e border-sidebar-border bg-sidebar md:flex">
        {/* Top: logo */}
        <div className="flex h-16 items-center px-5">
          <BrandLogo size="md" href={null} />
        </div>

        {/* Nav links */}
        <SidebarNav />

        {/* Divider */}
        <div className="mx-4 border-t border-sidebar-border" />

        {/* Middle: history slot — filled by chat page via CSS or children */}
        {isChatPage && (
          <div id="sidebar-history-slot" className="flex-1 overflow-y-auto px-2 py-1 min-h-0" />
        )}

        {/* Spacer: pushes profile to bottom when no history slot */}
        {!isChatPage && <div className="flex-1" />}

        {/* Bottom: profile */}
        <div className="border-t border-sidebar-border p-3">
          <div className="flex items-center gap-3 rounded-xl px-3 py-2.5 hover:bg-secondary transition-colors cursor-pointer" onClick={() => router.push("/profile")}>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{user?.full_name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          >
            <LogOut className="h-3.5 w-3.5" />
            {tCommon("signOut")}
          </button>
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true">
          <button type="button" aria-label="Close menu" className="absolute inset-0 bg-foreground/40 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className="relative flex h-full w-72 max-w-[80vw] flex-col border-e border-sidebar-border bg-sidebar shadow-2xl">
            <div className="flex h-16 items-center justify-between px-4">
              <BrandLogo size="md" href={null} />
              <button type="button" aria-label="Close menu" className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:text-foreground" onClick={() => setMobileOpen(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>
            <SidebarNav onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-border/60 bg-background/80 px-4 backdrop-blur-xl sm:px-6">
          <div className="flex items-center gap-3">
            <button type="button" aria-label="Open menu" className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:text-foreground md:hidden" onClick={() => setMobileOpen(true)}>
              <Menu className="h-4 w-4" />
            </button>
            <div className="md:hidden">
              <BrandLogo size="sm" href={null} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <ThemeToggle />
          </div>
        </header>

        <main className="flex-1">{children}</main>
      </div>

      <SOSButton />
    </div>
  );
}
