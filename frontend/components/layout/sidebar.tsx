"use client";

import {
  ClipboardList,
  FileCheck,
  FileText,
  HelpCircle,
  LayoutDashboard,
  LucideIcon,
  MessageSquare,
  Shield,
  Users,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { BrandLogo } from "@/components/layout/brand-logo";
import { cn } from "@/lib/utils";
import { Link, usePathname } from "@/src/i18n/navigation";
import { useAuthStore } from "@/store/auth";

type NavLink = { href: string; labelKey: string; icon: LucideIcon };

const PATIENT_LINKS: NavLink[] = [
  { href: "/chat", labelKey: "chat", icon: MessageSquare },
  { href: "/support/faq", labelKey: "support", icon: HelpCircle },
];

const DOCTOR_LINKS: NavLink[] = [
  { href: "/doctor/inbox", labelKey: "inbox", icon: ClipboardList },
  { href: "/support/faq", labelKey: "support", icon: HelpCircle },
];

const ADMIN_LINKS: NavLink[] = [
  { href: "/admin/dashboard", labelKey: "dashboard", icon: LayoutDashboard },
  { href: "/admin/users", labelKey: "users", icon: Users },
  { href: "/admin/doctors", labelKey: "doctorsPending", icon: FileCheck },
  { href: "/admin/safety", labelKey: "safety", icon: Shield },
  { href: "/admin/audit", labelKey: "audit", icon: FileText },
];

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const role = useAuthStore((s) => s.user?.role || "patient");
  const t = useTranslations("nav");

  const links = role === "admin" ? ADMIN_LINKS : role === "doctor" ? DOCTOR_LINKS : PATIENT_LINKS;

  return (
    <nav className="flex flex-col gap-0.5 px-3 py-2">
      {links.map(({ href, labelKey, icon: Icon }) => {
        const isActive = pathname === href || pathname.startsWith(href + "/");
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
              isActive
                ? "bg-primary-tint text-primary shadow-[inset_0_0_0_1px_rgb(11_95_255/0.15)]"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground",
            )}
          >
            <Icon className={cn("h-4 w-4 shrink-0", isActive && "text-primary")} />
            {t(labelKey)}
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-e border-sidebar-border bg-sidebar md:flex">
      <div className="flex h-16 items-center px-5">
        <BrandLogo size="md" href={null} />
      </div>
      <SidebarNav />
    </aside>
  );
}
