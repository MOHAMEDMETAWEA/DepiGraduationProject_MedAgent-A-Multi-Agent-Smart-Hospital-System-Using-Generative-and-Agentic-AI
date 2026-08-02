"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

type MarkdownProps = {
  children: string;
  className?: string;
};

export function Markdown({ children, className }: MarkdownProps) {
  return (
    <div
      className={cn(
        "text-sm leading-relaxed text-foreground",
        "[&_h1]:mt-0 [&_h1]:mb-3 [&_h1]:text-xl [&_h1]:font-bold [&_h1]:text-foreground [&_h1]:border-b [&_h1]:border-line [&_h1]:pb-2",
        "[&_h2]:mt-5 [&_h2]:mb-2 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-foreground",
        "[&_h3]:mt-4 [&_h3]:mb-1.5 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:text-ink-2",
        "[&_h4]:mt-3 [&_h4]:mb-1 [&_h4]:text-sm [&_h4]:font-semibold [&_h4]:text-ink-3",
        "[&_p]:my-2 [&_p]:text-ink-2",
        "[&_strong]:font-semibold [&_strong]:text-foreground",
        "[&_em]:italic",
        "[&_ul]:my-2 [&_ul]:ps-6 [&_ul]:list-disc [&_ul]:marker:text-ink-4",
        "[&_ol]:my-2 [&_ol]:ps-6 [&_ol]:list-decimal [&_ol]:marker:text-ink-4",
        "[&_li]:my-0.5 [&_li]:text-ink-2",
        "[&_code]:rounded [&_code]:bg-base-2 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.85em] [&_code]:text-primary",
        "[&_pre]:my-3 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-base-2 [&_pre]:p-3",
        "[&_pre_code]:bg-transparent [&_pre_code]:p-0",
        "[&_blockquote]:my-3 [&_blockquote]:border-s-4 [&_blockquote]:border-primary [&_blockquote]:bg-primary-tint/40 [&_blockquote]:ps-4 [&_blockquote]:py-2 [&_blockquote]:text-ink-3 [&_blockquote]:italic",
        "[&_hr]:my-4 [&_hr]:border-line",
        "[&_table]:my-3 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs",
        "[&_th]:border [&_th]:border-line [&_th]:bg-base-2 [&_th]:px-2 [&_th]:py-1.5 [&_th]:text-start [&_th]:font-semibold",
        "[&_td]:border [&_td]:border-line [&_td]:px-2 [&_td]:py-1.5",
        "[&_a]:text-primary [&_a]:underline-offset-2 hover:[&_a]:underline",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
