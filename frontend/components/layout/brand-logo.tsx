import { Stethoscope } from "lucide-react";
import { Link } from "@/src/i18n/navigation";
import { cn } from "@/lib/utils";

export function BrandLogo({ size = "md", href = "/" }: { size?: "sm" | "md" | "lg"; href?: string | null }) {
  const dim = size === "sm" ? "h-7 w-7" : size === "lg" ? "h-10 w-10" : "h-9 w-9";
  const iconSize = size === "sm" ? "h-4 w-4" : size === "lg" ? "h-5 w-5" : "h-4.5 w-4.5";
  const text = size === "sm" ? "text-sm" : size === "lg" ? "text-xl" : "text-base";

  const inner = (
    <span className="flex items-center gap-2.5">
      <span className={cn("brand-mark relative grid place-items-center overflow-hidden rounded-xl text-white", dim)}>
        <Stethoscope className={cn("relative z-10", iconSize)} />
      </span>
      <span className={cn("font-display font-bold tracking-tight text-foreground", text)}>MedAgent</span>
    </span>
  );

  if (href === null) return inner;
  return (
    <Link href={href} className="inline-flex items-center no-underline">
      {inner}
    </Link>
  );
}
