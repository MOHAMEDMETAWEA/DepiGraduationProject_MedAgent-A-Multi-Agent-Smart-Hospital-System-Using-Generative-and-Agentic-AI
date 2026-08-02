"use client";

/**
 * Lightweight toast: stack of dismissible messages with auto-dismiss.
 *
 * Why not pull in a toast library?
 *   - shadcn/sonner would add another dep + global Provider.
 *   - The MedAgent footprint is small — three call sites (status/notes/pdf).
 *   - This keeps cardinality + a11y intact (role=status, polite live region).
 *
 * Usage:
 *
 *   const [toasts, push, dismiss] = useToasts();
 *
 *   push({ tone: "error", message: t("handoff.actions.staleError") });
 *
 *   return (
 *     <>
 *       ...
 *       <ToastViewport toasts={toasts} onDismiss={dismiss} />
 *     </>
 *   );
 */

import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

export type ToastTone = "info" | "success" | "error" | "warning";

export interface ToastItem {
  id: string;
  tone: ToastTone;
  message: string;
  /** Override the default 6s auto-dismiss. Set to 0 to require manual close. */
  duration?: number;
}

const DEFAULT_DURATION_MS = 6000;

let _idCounter = 0;
function nextId(): string {
  _idCounter += 1;
  return `t${Date.now()}-${_idCounter}`;
}

export function useToasts(): [
  ToastItem[],
  (item: Omit<ToastItem, "id">) => string,
  (id: string) => void,
] {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    setToasts((cur) => cur.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const push = useCallback(
    (item: Omit<ToastItem, "id">) => {
      const id = nextId();
      const next: ToastItem = { id, ...item };
      setToasts((cur) => [...cur, next]);
      const duration = item.duration ?? DEFAULT_DURATION_MS;
      if (duration > 0) {
        timersRef.current.set(
          id,
          setTimeout(() => dismiss(id), duration),
        );
      }
      return id;
    },
    [dismiss],
  );

  useEffect(() => {
    // Capture the current Map so the cleanup uses the same instance the
    // effect saw at mount (avoids the lint warning about ref drift).
    const timers = timersRef.current;
    return () => {
      for (const timer of timers.values()) clearTimeout(timer);
      timers.clear();
    };
  }, []);

  return [toasts, push, dismiss];
}

const toneIcon: Record<ToastTone, typeof Info> = {
  info: Info,
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertCircle,
};

const toneClasses: Record<ToastTone, string> = {
  info: "border-line bg-card text-foreground",
  success: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200",
  error: "border-red-300 bg-red-50 text-red-900 dark:border-red-700 dark:bg-red-950/40 dark:text-red-200",
  warning: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200",
};

export function ToastViewport({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 left-1/2 z-50 flex w-full max-w-md -translate-x-1/2 flex-col gap-2 px-4 print:hidden"
    >
      {toasts.map((t) => {
        const Icon = toneIcon[t.tone];
        return (
          <div
            key={t.id}
            className={cn(
              "pointer-events-auto flex items-start gap-2 rounded-xl border px-3 py-2.5 text-sm shadow-sm",
              toneClasses[t.tone],
            )}
          >
            <Icon className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p className="flex-1">{t.message}</p>
            <button
              type="button"
              onClick={() => onDismiss(t.id)}
              aria-label="Dismiss"
              className="ml-1 rounded p-0.5 opacity-70 transition-opacity hover:opacity-100"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
