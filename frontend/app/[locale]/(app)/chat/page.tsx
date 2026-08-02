"use client";

import { chatApi, type ChatEvent } from "@/lib/api/chat";
import { useAuthStore } from "@/store/auth";
import { MessageBubble, TypingIndicator } from "@/components/chat/message-bubble";
import { ChatComposer, type ComposerAttachment } from "@/components/chat/composer";
import { TriagePanel, triageFromEvents } from "@/components/chat/triage-panel";
import { DifferentialPanel } from "@/components/chat/DifferentialPanel";
import { DoctorSearchDialog } from "@/components/chat/DoctorSearchDialog";
import { WatchSignalsCard } from "@/components/chat/WatchSignalsCard";
import { VisionResultCard, type VisionResult } from "@/components/chat/VisionResultCard";
import { VISION_OPTIONS, type VisionOption } from "@/components/chat/VisionModelSelector";
import { Clock, Hash, MessageSquare, Plus, Search, Send, Sparkles, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

// Strip Qwen3 thinking tags from response
function cleanResponse(text: string): string {
  return text
    .replace(/<think>/g, "\n💭 ")
    .replace(/<\/think>/g, "\n")
    .replace(/<\/?response>/g, "")
    .trim();
}

function getProviderName(model: string): string {
  if (model.startsWith("groq/")) return "Groq";
  if (model.startsWith("oa/")) return "OpenAI";
  if (model.startsWith("gemini/")) return "Google";
  if (model.startsWith("hf/")) return "HuggingFace";
  return "OpenRouter";
}

function getModelLabel(model: string): string {
  const base = MODEL_LABELS[model] || model;
  const provider = getProviderName(model);
  return `${base} · ${provider}`;
}

const triageBadge: Record<string, string> = {
  emergency: "badge-emergency",
  urgent: "badge-urgent",
  routine: "badge-routine",
};

const MODEL_LABELS: Record<string, string> = {
  "qwen/qwen-2.5-72b-instruct": "Qwen 2.5 72B",
  "openai/gpt-4o": "GPT-4o",
  "anthropic/claude-3.5-sonnet": "Claude 3.5 Sonnet",
  "google/gemini-2.5-flash": "Gemini 2.5 Flash",
  "meta-llama/llama-4-maverick": "Llama 4 Maverick",
  "deepseek/deepseek-chat": "DeepSeek V3",
  "groq/qwen/qwen3-32b": "Qwen 3 32B",
  "groq/allam-2-7b": "Allam 2 7B",
  "groq/llama-3.3-70b-versatile": "Llama 3.3 70B",
  "groq/meta-llama/llama-4-scout-17b-16e-instruct": "Llama 4 Scout 17B",
  "groq/llama-3.1-8b-instant": "Llama 3.1 8B",
  "oa/gpt-4o": "GPT-4o",
  "oa/gpt-4o-mini": "GPT-4o Mini",
  "oa/gpt-4.1": "GPT-4.1",
  "gemini/gemini-2.5-flash": "Gemini 2.5 Flash",
  "gemini/gemini-2.5-pro": "Gemini 2.5 Pro",
  "hf/Qwen/Qwen2.5-72B-Instruct": "Qwen 2.5 72B",
  "hf/meta-llama/Llama-3.1-8B-Instruct": "Llama 3.1 8B",
  "hf/google/gemma-2-9b-it": "Gemma 2 9B",
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  thinkingText?: string;
  events?: ChatEvent[];
  modelLabel?: string;
  triageLevel?: string | null;
  triageScore?: number | null;
  latencyMs?: number;
  tokenCount?: number;
  imagePreview?: string;
};

export default function ChatPage() {
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);

  const [convId, setConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [currentEvents, setCurrentEvents] = useState<ChatEvent[]>([]);
  const [triageExpanded, setTriageExpanded] = useState(false);
  const [selectedModels, setSelectedModels] = useState<string[]>(["groq/meta-llama/llama-4-scout-17b-16e-instruct"]);
  // Vision backend selection — independent of chat model. Multi-select:
  // when 2+ are picked AND an image is attached, we fan out N parallel
  // requests to compare accuracy across vision LLMs. Defaults to the
  // recommended single option (Gemini 2.0 Flash). Survives a refresh via
  // localStorage so the patient doesn't have to re-pick every reload.
  const [visionOptions, setVisionOptions] = useState<VisionOption[]>([VISION_OPTIONS[0]]);
  const [sendToDoctorOpen, setSendToDoctorOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const [convs, setConvs] = useState<Array<{ id: string; title: string | null; triage_level: string | null; updated_at: string }>>([]);
  const [convLoading, setConvLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [portalReady, setPortalReady] = useState(false);

  const isCompareMode = selectedModels.length > 1;
  const triage = triageFromEvents(currentEvents);

  const loadConvs = useCallback(async () => {
    setConvLoading(true);
    const res = await chatApi.listConversations(1);
    if (res.data) setConvs(res.data.items);
    setConvLoading(false);
  }, []);

  // Initial data fetch — sets conv list + loading state inside loadConvs.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { loadConvs(); }, [loadConvs]);
  // Hydration guard for the portal-based mobile sidebar (next-themes pattern).
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setPortalReady(true); }, []);
  // Restore the saved vision options from a previous session so the user
  // doesn't have to re-pick on every reload. We match each saved entry on
  // (provider, model) against VISION_OPTIONS — silently drop any that no
  // longer exist (e.g. if we remove a backend from the catalogue), and if
  // nothing matches we fall back to the default first option.
   
  useEffect(() => {
    try {
      const raw = localStorage.getItem("medagent-vision-options");
      if (!raw) return;
      const saved = JSON.parse(raw) as Array<{ provider?: string; model?: string }>;
      if (!Array.isArray(saved)) return;
      const matches: VisionOption[] = [];
      for (const s of saved) {
        const m = VISION_OPTIONS.find(
          (o) => o.provider === s.provider && o.model === s.model,
        );
        if (m && !matches.some((x) => x.provider === m.provider && x.model === m.model)) {
          matches.push(m);
        }
      }
      if (matches.length > 0) setVisionOptions(matches);
    } catch {
      /* ignore corrupt storage */
    }
  }, []);
  const handleVisionChange = useCallback((opts: VisionOption[]) => {
    // The selector guarantees opts.length >= 1, but we belt-and-suspender it.
    const next = opts.length > 0 ? opts : [VISION_OPTIONS[0]];
    setVisionOptions(next);
    try {
      localStorage.setItem(
        "medagent-vision-options",
        JSON.stringify(next.map((o) => ({ provider: o.provider, model: o.model }))),
      );
    } catch {
      /* localStorage may be unavailable in private mode */
    }
  }, []);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const loadConversation = async (id: string) => {
    setConvId(id);
    const msgs = await chatApi.getMessages(id);
    if (msgs.data && Array.isArray(msgs.data)) {
      // Hydrate persisted events (triage / watch_signals / tot_branches / …)
      // alongside the text — without this, navigating back into a chat lost
      // every card except the message bubble.
      type ApiMessage = {
        role: string;
        content: string;
        events?: ChatEvent[];
        image_data?: string | null;
        image_kind?: string | null;
      };
      const rebuilt: ChatMessage[] = (msgs.data as ApiMessage[]).map((m) => {
        const events: ChatEvent[] = Array.isArray(m.events) ? m.events : [];
        const triage = events.find((e) => e.type === "triage");
        return {
          role: m.role as ChatMessage["role"],
          content: m.content,
          events,
          triageLevel: (triage?.data?.level as string | null | undefined) ?? null,
          triageScore: (triage?.data?.score as number | null | undefined) ?? null,
          // Restore the attached image (only present on user messages where
          // an image was uploaded) so the picture shows up on reload.
          imagePreview: m.image_data ?? undefined,
        };
      });
      setMessages(rebuilt);
    }
  };

  const deleteConv = async (id: string) => {
    if (!confirm("Delete this conversation?")) return;
    await chatApi.deleteConversation(id);
    if (convId === id) { setConvId(null); setMessages([]); }
    loadConvs();
  };

  const deleteAll = async () => {
    if (!confirm("Delete ALL conversations?")) return;
    setStreaming(true);
    let deleted = 0;
    for (const c of convs) {
      try { const res = await chatApi.deleteConversation(c.id); if (res.status === 204 || res.status === 200) deleted++; } catch { /* */ }
    }
    setConvs([]); setConvId(null); setMessages([]);
    setStreaming(false);
    if (deleted > 0) loadConvs();
  };

  const newChat = () => { setConvId(null); setMessages([]); setCurrentEvents([]); };

  const getToken = () => {
    if (accessToken) return accessToken;
    try { const raw = localStorage.getItem("medagent-auth"); if (raw) return JSON.parse(raw).state?.accessToken || null; } catch { /* */ }
    return null;
  };

  const refreshToken = () => {
    try { const raw = localStorage.getItem("medagent-auth"); if (raw) return JSON.parse(raw).state?.accessToken || null; } catch { /* */ }
    return null;
  };


  const handleSend = async (message: string, attachment?: ComposerAttachment) => {
    let token = getToken();
    if (!token) return;

    setStreaming(true); setCurrentEvents([]);

    let id = convId;
    if (!id) {
      const res = await chatApi.createConversation("ar");
      if (res.error || !res.data) { setStreaming(false); return; }
      id = res.data.id; setConvId(id); loadConvs();
    }
    token = refreshToken() || token;

    const imageData = attachment?.dataUri;
    const imageKind = attachment?.kind;

    // Three execution modes:
    //  1. Vision-compare: 1 chat model + image + 2+ vision options
    //     → N parallel streams, same chat model, different vision per stream.
    //     This is the new mode the user asked for ("لقياس الدقة بين الموديلات").
    //  2. Chat-compare: 2+ chat models (existing). Uses visionOptions[0].
    //  3. Single: 1 chat + 0/1 vision options (existing).
    //
    // Chat-compare wins if both would apply — running an M × N matrix would
    // be too many requests and noisy to read. Users pick one comparison axis
    // at a time. We do not currently surface that to the user explicitly,
    // but the dropdown labels ("Compare") make the active mode obvious.
    const isChatCompare = selectedModels.length > 1;
    const isVisionCompare =
      !!imageData && visionOptions.length > 1 && !isChatCompare;
    const primaryVision = visionOptions[0];

    if (!isChatCompare && !isVisionCompare) {
      // ── Single model (streaming live display) ──
      const [model] = selectedModels;
      const label = getModelLabel(model);

      // Add user message + placeholder assistant message
      const placeholder: ChatMessage = { role: "assistant", content: "", thinkingText: "", events: [], modelLabel: label };
      setMessages((prev) => [...prev, { role: "user", content: message, imagePreview: imageData }, placeholder]);
      const msgIdx = messages.length + 1; // index of placeholder after set

      const start = performance.now();

      const streamText = (fullText: string, msgIdx: number, field: "content" | "thinkingText", events: ChatEvent[]) => {
        let pos = 0;
        const total = fullText.length;
        return new Promise<void>((resolve) => {
          const tick = () => {
            if (pos >= total) { resolve(); return; }
            const chunk = fullText.slice(0, pos + 1);
            pos = chunk.length;
            setMessages((prev) => prev.map((m, i) =>
              i === msgIdx ? { ...m, [field]: chunk, events } : m
            ));
            setTimeout(() => requestAnimationFrame(tick), 12);
          };
          requestAnimationFrame(tick);
        });
      };

      const events: ChatEvent[] = [];
      let fullTxt = "";
      let thinkingTxt = "";

      try {
        for await (const event of chatApi.streamChat(
          id,
          message,
          token,
          model,
          imageData,
          imageKind,
          // Only forward the vision override when an image is attached —
          // text-only messages never call analyze_vision so the field would
          // just be ignored. Saves a few bytes per request.
          imageData ? primaryVision.provider : undefined,
          imageData ? primaryVision.model : undefined,
        )) {
          events.push(event);
          if (event.type === "token") fullTxt += event.content;
          if (event.type === "thinking") thinkingTxt += event.content;
          if (event.type === "red_flag") fullTxt = "🚨 تم اكتشاف علامات طارئة — يرجى التوجه للطوارئ فوراً";
          if (event.type === "error") fullTxt = event.content || "⚠️ خطأ من النموذج";
          if (event.type === "done") break;
        }
      } catch (e) { console.error("Chat error:", e); fullTxt = "عذراً، حدث خطأ."; }

      // Animate thinking text first (if any), then the response
      if (thinkingTxt) {
        await streamText(thinkingTxt, msgIdx, "thinkingText", events);
      }

      const clean = cleanResponse(fullTxt);
      const fallback = events.some(e => e.type === "red_flag")
        ? "🚨 تم اكتشاف علامات طارئة — يرجى التوجه للطوارئ فوراً"
        : events.some(e => e.type === "tool_result")
          ? "⚠️ اكتمل التحليل ولكن لم يتم إنشاء رد. حاول إعادة الصياغة."
          : "⚠️ لم يتم إنشاء رد. حاول مرة أخرى.";
      await streamText(clean || fallback, msgIdx, "content", events);

      const triageEvt = events.find((e) => e.type === "triage");
      setMessages((prev) => prev.map((m, i) =>
        i === msgIdx ? {
          ...m,
          content: clean || "⚠️ No response",
          thinkingText: thinkingTxt || undefined,
          events,
          latencyMs: performance.now() - start,
          tokenCount: events.filter((e) => e.type === "token").length,
          triageLevel: triageEvt?.data?.level as string || null,
          triageScore: triageEvt?.data?.score as number || null,
        } : m
      ));
      if (fullTxt) loadConvs();
    } else if (isVisionCompare) {
      // ── Vision-compare: same chat model, N vision backends ──
      // We fan out N requests to /chat, each pinned to the same chat model
      // but with a different vision provider/model. Each response is rendered
      // as its own assistant message labeled with the vision backend so the
      // user can visually compare the resulting findings + urgency + confidence
      // cards side-by-side. The full agent still runs for each, which means
      // the text portion may vary too — that's intentional, because the
      // downstream reasoning depends on what the vision tool returned.
      const [model] = selectedModels;
      const userMsg: ChatMessage = {
        role: "user",
        content: message,
        imagePreview: imageData,
      };
      const startIdx = messages.length;
      const modelMsgs: ChatMessage[] = visionOptions.map((opt) => ({
        role: "assistant",
        content: "",
        thinkingText: "",
        // In vision-compare the chat model is identical across all rows so
        // we drop it from the label and present a clean medical-product
        // header: "MedAgent · 👁 Gemini 1.5 Flash". This is the "اسم احترافي"
        // the user asked for instead of "Llama 4 Scout 17B · Groq · vision:".
        modelLabel: `MedAgent · 👁 ${opt.label}`,
        events: [],
      }));
      setMessages((prev) => [...prev, userMsg, ...modelMsgs]);

      const streams = visionOptions.map(async (opt, idx) => {
        const msgIdx = startIdx + 1 + idx;
        const start = performance.now();
        const events: ChatEvent[] = [];
        let fullTxt = "";
        let thinkingTxt = "";
        let triageLevel: string | null = null;
        let triageScore: number | null = null;

        try {
          for await (const event of chatApi.streamChat(
            id,
            message,
            token,
            model,
            imageData,
            imageKind,
            opt.provider,
            opt.model,
          )) {
            events.push(event);
            if (event.type === "token") fullTxt += event.content;
            if (event.type === "thinking") thinkingTxt += event.content;
            if (event.type === "red_flag") fullTxt = "🚨 تم اكتشاف علامات طارئة — يرجى التوجه للطوارئ فوراً";
            if (event.type === "error") fullTxt = event.content || "⚠️ خطأ من النموذج";
            if (event.type === "triage") {
              triageLevel = (event.data?.level as string) || null;
              triageScore = (event.data?.score as number) || null;
            }
            if (event.type === "done") break;
          }
        } catch (e: unknown) {
          fullTxt = e instanceof Error ? e.message : "Request failed";
        }

        const clean = cleanResponse(fullTxt);
        setMessages((prev) =>
          prev.map((m, i) =>
            i === msgIdx
              ? {
                  ...m,
                  content:
                    clean ||
                    (events.some((e) => e.type === "red_flag")
                      ? "🚨 تم اكتشاف علامات طارئة"
                      : events.some((e) => e.type === "tool_result")
                        ? "⚠️ اكتمل التحليل بدون رد"
                        : "⚠️ No response"),
                  thinkingText: thinkingTxt || undefined,
                  events,
                  triageLevel,
                  triageScore,
                  latencyMs: performance.now() - start,
                  tokenCount: events.filter((e) => e.type === "token").length,
                }
              : m,
          ),
        );
      });

      await Promise.all(streams);
      loadConvs();
    } else {
      // ── Chat-compare mode: stack model responses vertically ──
      const userMsg: ChatMessage = { role: "user", content: message, imagePreview: imageData };
      const startIdx = messages.length; // user message index after set
      const modelMsgs: ChatMessage[] = selectedModels.map((model) => ({
        role: "assistant",
        content: "",
        thinkingText: "",
        modelLabel: getModelLabel(model),
        events: [],
      }));
      setMessages((prev) => [...prev, userMsg, ...modelMsgs]);

      const streams = selectedModels.map(async (model, idx) => {
        const msgIdx = startIdx + 1 + idx; // position in messages array
        const start = performance.now();
        const events: ChatEvent[] = [];
        let fullTxt = "";
        let thinkingTxt = "";
        let triageLevel: string | null = null;
        let triageScore: number | null = null;

        try {
          for await (const event of chatApi.streamChat(
            id,
            message,
            token,
            model,
            imageData,
            imageKind,
            imageData ? primaryVision.provider : undefined,
            imageData ? primaryVision.model : undefined,
          )) {
            events.push(event);
            if (event.type === "token") fullTxt += event.content;
            if (event.type === "thinking") thinkingTxt += event.content;
            if (event.type === "red_flag") fullTxt = "🚨 تم اكتشاف علامات طارئة — يرجى التوجه للطوارئ فوراً";
            if (event.type === "error") fullTxt = event.content || "⚠️ خطأ من النموذج";
            if (event.type === "triage") {
              triageLevel = (event.data?.level as string) || null;
              triageScore = (event.data?.score as number) || null;
            }
            if (event.type === "done") break;
          }
        } catch (e: unknown) {
          fullTxt = e instanceof Error ? e.message : "Request failed";
        }

        // Animate thinking text first
        if (thinkingTxt) {
          const total = thinkingTxt.length;
          let pos = 0;
          await new Promise<void>((resolve) => {
            const tick = () => {
              if (pos >= total) { resolve(); return; }
              const chunk = thinkingTxt.slice(0, pos + 1);
              pos = chunk.length;
              setMessages((prev) => prev.map((m, i) =>
                i === msgIdx ? { ...m, thinkingText: chunk, events } : m
              ));
              setTimeout(() => requestAnimationFrame(tick), 8);
            };
            requestAnimationFrame(tick);
          });
        }

        // Smooth character-by-character reveal via rAF for the response
        const clean = cleanResponse(fullTxt);
        const total = clean.length;
        let pos = 0;
        await new Promise<void>((resolve) => {
          const tick = () => {
            if (pos >= total) { resolve(); return; }
            const chunk = clean.slice(0, pos + 1);
            pos = chunk.length;
            setMessages((prev) => prev.map((m, i) =>
              i === msgIdx ? { ...m, content: chunk, events, triageLevel, triageScore } : m
            ));
            setTimeout(() => requestAnimationFrame(tick), 8);
          };
          requestAnimationFrame(tick);
        });

        setMessages((prev) => prev.map((m, i) =>
          i === msgIdx ? {
            ...m,
            content: clean || (events.some(e => e.type === "red_flag") ? "🚨 تم اكتشاف علامات طارئة" : events.some(e => e.type === "error") ? (events.find(e => e.type === "error")?.content || "⚠️ خطأ") : events.some(e => e.type === "tool_result") ? "⚠️ اكتمل التحليل بدون رد" : "⚠️ No response"),
            thinkingText: thinkingTxt || undefined,
            events,
            triageLevel,
            triageScore,
            latencyMs: performance.now() - start,
            tokenCount: events.filter((e) => e.type === "token").length,
          } : m
        ));
      });

      await Promise.all(streams);
      loadConvs();
    }

    setStreaming(false); setCurrentEvents([]);
  };

  const filtered = searchTerm ? convs.filter((c) => (c.title || "").toLowerCase().includes(searchTerm.toLowerCase())) : convs;

  const historyList = (
    <div className="flex flex-col h-full">
      <div className="p-2 space-y-2 flex-shrink-0">
        <button onClick={newChat} className="btn-primary flex w-full items-center justify-center gap-1.5 rounded-lg py-1.5 text-[11px] font-semibold">
          <Plus className="h-3 w-3" /> New Chat
        </button>
        <div className="flex items-center gap-1.5 rounded-md bg-muted/50 px-2 py-1.5">
          <Search className="h-3 w-3 text-muted-foreground flex-shrink-0" />
          <input value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} placeholder="Search..." className="w-full bg-transparent text-[11px] text-foreground placeholder:text-muted-foreground outline-none" />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-1.5 pb-2 space-y-0.5 min-h-0">
        {convLoading ? (
          <p className="text-[11px] text-muted-foreground text-center py-4">Loading...</p>
        ) : filtered.length === 0 ? (
          <p className="text-[11px] text-muted-foreground text-center py-4">{searchTerm ? "No results" : "No conversations"}</p>
        ) : (
          filtered.map((c) => (
            <div key={c.id} onClick={() => loadConversation(c.id)}
              className={`group flex items-start gap-1.5 w-full text-left px-2 py-1.5 rounded-md cursor-pointer transition-colors ${c.id === convId ? "bg-sidebar-accent text-sidebar-accent-foreground" : "hover:bg-muted/50 text-sidebar-foreground"}`}>
              <MessageSquare className="h-3 w-3 mt-0.5 flex-shrink-0 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className="text-[11px] leading-tight truncate">{c.title || "New conversation"}</p>
                <div className="flex items-center gap-1 mt-0.5">
                  {c.triage_level && <span className={`text-[8px] font-semibold px-1 py-0 rounded-full ${triageBadge[c.triage_level] || "bg-muted text-ink-4"}`}>{c.triage_level}</span>}
                  <span className="text-[9px] text-muted-foreground">{new Date(c.updated_at).toLocaleDateString()}</span>
                </div>
              </div>
              <button onClick={(e) => { e.stopPropagation(); deleteConv(c.id); }} className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-100 dark:hover:bg-red-950/30 text-muted-foreground hover:text-red-600 flex-shrink-0">
                <Trash2 className="h-2.5 w-2.5" />
              </button>
            </div>
          ))
        )}
      </div>
      {convs.length > 0 && (
        <div className="px-1.5 pb-2 flex-shrink-0">
          <button onClick={deleteAll} className="flex w-full items-center justify-center gap-1 rounded-md py-1.5 text-[10px] text-muted-foreground hover:bg-red-50 dark:hover:bg-red-950/30 hover:text-red-600 transition-colors">
            <Trash2 className="h-2.5 w-2.5" /> Delete all
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {portalReady && createPortal(historyList, document.getElementById("sidebar-history-slot") || document.body)}

      <div className="flex-1 flex flex-col min-w-0">
        {triage.level && <TriagePanel state={triage} collapsed={!triageExpanded} onToggle={() => setTriageExpanded(!triageExpanded)} />}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
          <div className="max-w-5xl mx-auto">
            {messages.length === 0 && !streaming && (
              <div className="flex flex-col items-center justify-center h-full min-h-[40vh] text-center">
                <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary mb-5 shadow-sm">
                  <Sparkles className="h-7 w-7" />
                </div>
                <h3 className="text-xl font-semibold text-foreground">MedAgent Triage</h3>
                <p className="mt-2 text-sm text-muted-foreground max-w-xs">Describe your symptoms in Arabic or English.</p>
              </div>
            )}

            {messages.map((msg, i) => {
              if (msg.role === "user") {
                return <MessageBubble key={i} role="user" content={msg.content} senderName={user?.full_name || undefined} imagePreview={msg.imagePreview} />;
              }
              // CX2: suppress the assistant placeholder while there's no
              // content yet — the TypingIndicator already shows the avatar
              // + spinner, so rendering the empty bubble here was the source
              // of the "two stethoscopes" bug during the thinking phase.
              const hasAnyContent =
                Boolean(msg.content) ||
                (msg.events?.length ?? 0) > 0 ||
                Boolean(msg.thinkingText);
              if (!hasAnyContent) return null;
              return (
                <div key={i}>
                  {/* Model name label */}
                  {msg.modelLabel && (
                    <div className="ml-12 mb-2 text-xs font-semibold text-muted-foreground/70">
                      {msg.modelLabel}
                    </div>
                  )}

                  {/* Response card */}
                  <MessageBubble
                    role="assistant"
                    content={msg.content}
                    events={msg.events}
                    senderName={undefined}
                  />

                  {/* ToT branches — labels follow the user's profile locale,
                       not the URL locale (so a user with locale=ar still sees
                       Arabic labels even when the URL is /en). */}
                  {Boolean(msg.events?.find((e) => e.type === "tot_branches")?.data?.branches) && (
                    <div className="mt-3 ml-11 max-w-[85%]">
                      <DifferentialPanel
                        branches={
                          msg.events!.find((e) => e.type === "tot_branches")!.data
                            .branches as Array<{
                            name: string;
                            confidence: number;
                            evidence: string;
                          }>
                        }
                        language={
                          (user?.locale as "ar" | "en" | undefined) ?? "ar"
                        }
                      />
                    </div>
                  )}

                  {/* Vision analysis card — surfaces analyze_vision tool
                      output as a structured panel (findings + urgency +
                      confidence + disclaimer). Without this card the patient
                      saw only the assistant's prose summary, which felt like
                      "the AI didn't look at my image". We pull the image
                      thumbnail from the *previous* user message (which is the
                      one that carried the attachment). */}
                  {(() => {
                    const visionEvent = msg.events?.find(
                      (e) =>
                        e.type === "tool_result" &&
                        (e.data?.tool as string | undefined) === "analyze_vision",
                    );
                    if (!visionEvent) return null;
                    const result = visionEvent.data?.result as
                      | Partial<VisionResult>
                      | undefined;
                    if (!result) return null;
                    // Find the most recent user message before this one — that
                    // is the one that uploaded the image.
                    const prevUser = [...messages.slice(0, i)]
                      .reverse()
                      .find((m) => m.role === "user");
                    const visionResult: VisionResult = {
                      findings: Array.isArray(result.findings) ? result.findings : [],
                      urgency:
                        (result.urgency as VisionResult["urgency"]) ?? "none",
                      confidence:
                        typeof result.confidence === "number" ? result.confidence : 0,
                      disclaimer: result.disclaimer ?? "",
                      imageUrl: prevUser?.imagePreview,
                      // Pass through the raw upstream error so the card can
                      // tell the user exactly why this provider failed
                      // (quota / billing / auth / network) instead of the
                      // generic "Vision LLM unavailable" line.
                      error:
                        typeof result.error === "string" ? result.error : undefined,
                    };
                    return (
                      <div className="mt-3 ml-11 max-w-[85%]">
                        <VisionResultCard
                          result={visionResult}
                          language={(user?.locale as "ar" | "en" | undefined) ?? "ar"}
                        />
                      </div>
                    );
                  })()}

                  {/* Triage card is rendered by <MessageBubble> above so the
                      label/colour scheme stays consistent. The duplicate chip
                      that used to live here was the "URGENT · Score 65" eyesore. */}

                  {/* Red-flag watch list — only render for emergency cases.
                      Showing dangerous-sign checklists on every urgent reply
                      was felt as noise/CYA by users; clinically the value is
                      highest when the patient is borderline-emergency. */}
                  {(() => {
                    const ws = msg.events?.find((e) => e.type === "watch_signals");
                    const triage = msg.events?.find((e) => e.type === "triage");
                    const level = (triage?.data?.level as string | undefined) ?? "";
                    const signals = (ws?.data?.signals as string[] | undefined) ?? [];
                    if (signals.length === 0 || level !== "emergency") return null;
                    return (
                      <div className="mt-3 ml-11 max-w-[85%]">
                        <WatchSignalsCard
                          signals={signals}
                          language={(user?.locale as "ar" | "en" | undefined) ?? "ar"}
                        />
                      </div>
                    );
                  })()}

                  {/* Metrics row */}
                  {msg.modelLabel && (
                    <div className="ml-12 mb-4 flex items-center gap-4 text-[11px] text-muted-foreground">
                      {msg.latencyMs != null && (
                        <span className="inline-flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {(msg.latencyMs / 1000).toFixed(1)}s
                        </span>
                      )}
                      {msg.tokenCount != null && (
                        <span className="inline-flex items-center gap-1">
                          <Hash className="h-3 w-3" />
                          {msg.tokenCount} tok
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Typing indicator: only show when there is genuinely no
                assistant content yet. The `currentEvents` state never gets
                populated during streaming (it stays empty until /done), so
                checking it would keep the indicator on forever. The honest
                signal is "is the latest assistant message still empty?" */}
            {streaming &&
              !isCompareMode &&
              (() => {
                const lastAssistant = [...messages]
                  .reverse()
                  .find((m) => m.role === "assistant");
                const hasNoContentYet =
                  !lastAssistant ||
                  (!lastAssistant.content && !lastAssistant.thinkingText);
                return hasNoContentYet ? <TypingIndicator /> : null;
              })()}
          </div>
        </div>

        {/* Send to Doctor button */}
        {messages.length > 0 && convId && !streaming && (
          <div className="flex justify-center px-4 -mt-1 pb-1">
            <button
              onClick={() => setSendToDoctorOpen(true)}
              className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-primary transition-colors px-4 py-2 rounded-xl border border-border/60 hover:border-primary/30 hover:bg-primary/5"
            >
              <Send className="h-3.5 w-3.5" />
              Send to Doctor
            </button>
          </div>
        )}

        <ChatComposer
          onSend={handleSend}
          disabled={streaming}
          selectedModels={selectedModels}
          onModelsChange={setSelectedModels}
          visionOptions={visionOptions}
          onVisionChange={handleVisionChange}
        />
      </div>

      {/* Doctor search dialog */}
      {convId && (
        <DoctorSearchDialog
          conversationId={convId}
          open={sendToDoctorOpen}
          onClose={() => setSendToDoctorOpen(false)}
        />
      )}
    </div>
  );
}
