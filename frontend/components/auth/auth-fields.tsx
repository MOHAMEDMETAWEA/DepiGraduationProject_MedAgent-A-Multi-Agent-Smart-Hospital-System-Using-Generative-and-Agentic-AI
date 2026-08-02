import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";
import { ComponentProps, forwardRef } from "react";

type FieldProps = ComponentProps<"input"> & {
  label: string;
  error?: string;
  icon?: LucideIcon;
};

export const AuthField = forwardRef<HTMLInputElement, FieldProps>(function AuthField(
  { label, error, icon: Icon, className, ...props },
  ref,
) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-foreground">{label}</label>
      <div className="relative">
        {Icon && (
          <Icon
            aria-hidden
            className="pointer-events-none absolute start-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          />
        )}
        <Input ref={ref} className={cn(Icon && "ps-10", className)} {...props} />
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
});

type SubmitProps = ComponentProps<"button"> & {
  loading?: boolean;
  loadingLabel?: string;
};

export function AuthSubmit({ children, loading, loadingLabel, disabled, className, ...props }: SubmitProps) {
  return (
    <button
      type="submit"
      disabled={loading || disabled}
      className={cn(
        "btn-primary inline-flex h-11 w-full items-center justify-center gap-2 rounded-full px-4 text-sm font-semibold",
        className,
      )}
      {...props}
    >
      {loading ? (
        <>
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          {loadingLabel ?? "Loading…"}
        </>
      ) : (
        children
      )}
    </button>
  );
}

export function AuthAlert({ children, tone = "error" }: { children: React.ReactNode; tone?: "error" | "success" }) {
  const cls =
    tone === "error"
      ? "border-destructive/30 bg-destructive/10 text-destructive"
      : "border-emerald-500/30 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400";
  return (
    <div className={cn("mb-4 rounded-xl border px-4 py-2.5 text-sm", cls)}>{children}</div>
  );
}
