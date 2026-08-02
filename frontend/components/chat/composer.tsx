"use client";

import { ArrowUp, Brain, Check, ChevronDown, Loader2 } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { ImageUpload } from "@/components/chat/ImageUpload";
import { VisionModelSelector, type VisionOption } from "@/components/chat/VisionModelSelector";

const MODEL_GROUPS = [
  {
    label: "OpenRouter",
    models: [
      { value: "qwen/qwen-2.5-72b-instruct", label: "Qwen 2.5 72B" },
      { value: "openai/gpt-4o", label: "GPT-4o" },
      { value: "anthropic/claude-3.5-sonnet", label: "Claude 3.5 Sonnet" },
      { value: "google/gemini-2.5-flash", label: "Gemini 2.5 Flash" },
      { value: "meta-llama/llama-4-maverick", label: "Llama 4 Maverick" },
      { value: "deepseek/deepseek-chat", label: "DeepSeek V3" },
    ],
  },
  {
    label: "Groq",
    models: [
      { value: "groq/qwen/qwen3-32b", label: "Qwen 3 32B" },
      { value: "groq/allam-2-7b", label: "Allam 2 7B (عربي)" },
      { value: "groq/llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
      { value: "groq/meta-llama/llama-4-scout-17b-16e-instruct", label: "Llama 4 Scout 17B" },
      { value: "groq/llama-3.1-8b-instant", label: "Llama 3.1 8B" },
    ],
  },
  {
    label: "OpenAI",
    models: [
      { value: "oa/gpt-4o", label: "GPT-4o" },
      { value: "oa/gpt-4o-mini", label: "GPT-4o Mini" },
      { value: "oa/gpt-4.1", label: "GPT-4.1" },
    ],
  },
  {
    label: "Google Gemini",
    models: [
      { value: "gemini/gemini-2.5-flash", label: "Gemini 2.5 Flash" },
      { value: "gemini/gemini-2.5-pro", label: "Gemini 2.5 Pro" },
    ],
  },
  {
    label: "HuggingFace",
    models: [
      { value: "hf/Qwen/Qwen2.5-72B-Instruct", label: "Qwen 2.5 72B" },
      { value: "hf/meta-llama/Llama-3.1-8B-Instruct", label: "Llama 3.1 8B" },
      { value: "hf/google/gemma-2-9b-it", label: "Gemma 2 9B" },
    ],
  },
];

const ALL_MODELS = MODEL_GROUPS.flatMap((g) => g.models.map((m) => m.value));

export type ComposerAttachment = {
  dataUri: string;
  kind: string;
  mimeType: string;
  fileName: string;
};

type Props = {
  onSend: (message: string, attachment?: ComposerAttachment) => void;
  disabled?: boolean;
  selectedModels: string[];
  onModelsChange: (models: string[]) => void;
  visionOptions: VisionOption[];
  onVisionChange: (options: VisionOption[]) => void;
};

const fileToDataUri = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

const guessImageKind = (fileName: string): string => {
  const lower = fileName.toLowerCase();
  if (lower.includes("xray") || lower.includes("x-ray") || lower.includes("chest")) return "xray";
  if (lower.includes("ct") || lower.includes("scan")) return "ct";
  if (lower.includes("skin") || lower.includes("rash") || lower.includes("derm")) return "skin";
  if (lower.includes("wound") || lower.includes("cut") || lower.includes("burn")) return "wound";
  return "other";
};

export function ChatComposer({
  onSend,
  disabled,
  selectedModels,
  onModelsChange,
  visionOptions,
  onVisionChange,
}: Props) {
  const [value, setValue] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageResetSignal, setImageResetSignal] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [value]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    if (dropdownOpen) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownOpen]);

  const handleSend = async () => {
    const trimmed = value.trim();
    if (disabled || selectedModels.length === 0) return;
    if (!trimmed && !imageFile) return;

    let attachment: ComposerAttachment | undefined;
    if (imageFile) {
      try {
        const dataUri = await fileToDataUri(imageFile);
        attachment = {
          dataUri,
          kind: guessImageKind(imageFile.name),
          mimeType: imageFile.type,
          fileName: imageFile.name,
        };
      } catch {
        // فشل تحويل الصورة لـ base64 — نكمل النص بس
      }
    }

    const messageToSend = trimmed || (attachment ? "راجع هذه الصورة من فضلك" : "");
    onSend(messageToSend, attachment);
    setValue("");
    setImageFile(null);
    setImageResetSignal((s) => s + 1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const toggleModel = (model: string) => {
    const next = selectedModels.includes(model)
      ? selectedModels.filter((m) => m !== model)
      : [...selectedModels, model];
    if (next.length > 0) onModelsChange(next);
  };

  const toggleAll = () => {
    onModelsChange(selectedModels.length === ALL_MODELS.length ? [ALL_MODELS[0]] : [...ALL_MODELS]);
  };

  const isCompareMode = selectedModels.length > 1;

  const label = selectedModels.length === 1
    ? MODEL_GROUPS.flatMap((g) => g.models).find((m) => m.value === selectedModels[0])?.label || selectedModels[0]
    : selectedModels.length === ALL_MODELS.length
      ? `All models (${ALL_MODELS.length})`
      : `${selectedModels.length} models`;

  return (
    <div className="sticky bottom-0 border-t border-border bg-card/85 backdrop-blur-xl p-4">
      <div className="max-w-3xl mx-auto">
        {/* Model selector + image upload row */}
        <div className="flex items-center gap-2 mb-3">
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              disabled={disabled}
              className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer disabled:opacity-50"
            >
              <Brain className="h-3.5 w-3.5 text-muted-foreground/60 flex-shrink-0" />
              <span className="truncate max-w-[140px]">{label}</span>
              <ChevronDown className={`h-3 w-3 transition-transform duration-200 ${dropdownOpen ? "rotate-180" : ""}`} />
            </button>

            {dropdownOpen && (
              <div className="absolute bottom-full left-0 mb-2 z-50 w-60 rounded-xl border border-border bg-popover shadow-lg py-2 max-h-[280px] overflow-y-auto">
                {MODEL_GROUPS.map((group) => (
                  <div key={group.label}>
                    <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                      {group.label}
                    </div>
                    {group.models.map((m) => {
                      const checked = selectedModels.includes(m.value);
                      return (
                        <button
                          key={m.value}
                          onClick={() => toggleModel(m.value)}
                          className="flex items-center gap-2 w-full px-3 py-2 text-xs text-left hover:bg-muted transition-colors"
                        >
                          <span className={`grid place-items-center w-4 h-4 rounded border flex-shrink-0 transition-colors ${
                            checked ? "bg-primary border-primary text-primary-foreground" : "border-border"
                          }`}>
                            {checked && <Check className="h-2.5 w-2.5" />}
                          </span>
                          <span className="text-foreground">{m.label}</span>
                        </button>
                      );
                    })}
                  </div>
                ))}
                <div className="border-t border-border mt-1 pt-1">
                  <button
                    onClick={toggleAll}
                    className="flex items-center gap-2 w-full px-3 py-2 text-[11px] font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                  >
                    {selectedModels.length === ALL_MODELS.length ? "Deselect all" : "Select all"}
                  </button>
                </div>
              </div>
            )}
          </div>

          {isCompareMode && (
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
              Compare
            </span>
          )}

          {/* Vision-model selector — independent of the chat model so the
              patient can pair any chat LLM with any vision LLM. Multi-select
              triggers vision-compare mode: same image, N vision backends,
              N stacked result cards so the user can A/B/C accuracy. */}
          <div className="ml-2">
            <VisionModelSelector
              value={visionOptions}
              onChange={onVisionChange}
              disabled={disabled}
            />
          </div>

          <div className="ml-auto">
            <ImageUpload
              onImageSelect={(file) => setImageFile(file)}
              disabled={disabled}
              resetSignal={imageResetSignal}
            />
          </div>
        </div>

        {/* Input row */}
        <div className="flex gap-3 items-end bg-muted/50 rounded-2xl border border-border/60 px-4 py-2 transition-colors focus-within:border-primary/40 focus-within:bg-muted/80 focus-within:shadow-sm">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isCompareMode ? "Compare models — describe your symptoms..." : "Describe your symptoms in Arabic or English..."}
            rows={1}
            className="flex-1 resize-none border-none bg-transparent outline-none text-sm text-foreground placeholder:text-muted-foreground/50 py-1.5 px-0 font-sans"
            disabled={disabled}
          />
          <button
            onClick={() => void handleSend()}
            disabled={disabled || (!value.trim() && !imageFile) || selectedModels.length === 0}
            className="flex-shrink-0 w-9 h-9 rounded-xl bg-primary text-primary-foreground grid place-items-center border-none cursor-pointer disabled:opacity-30 hover:opacity-90 transition-all duration-200"
          >
            {disabled ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
