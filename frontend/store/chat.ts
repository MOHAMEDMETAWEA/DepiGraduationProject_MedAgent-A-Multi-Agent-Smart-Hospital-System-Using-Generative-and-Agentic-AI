import { create } from "zustand";

export type TriageLevel = "emergency" | "urgent" | "routine" | null;

export type Triage = {
  level: TriageLevel;
  score: number | null;
  reasoning: string | null;
};

export type ChatStreamState = "idle" | "streaming" | "tool" | "done" | "error";

type ChatState = {
  conversationId: string | null;
  streamState: ChatStreamState;
  triage: Triage;
  redFlags: Array<Record<string, unknown>>;
  activeTool: string | null;
  lastError: string | null;

  setConversation: (id: string | null) => void;
  setStreamState: (s: ChatStreamState) => void;
  setTriage: (t: Partial<Triage>) => void;
  pushRedFlag: (flag: Record<string, unknown>) => void;
  setActiveTool: (name: string | null) => void;
  setError: (msg: string | null) => void;
  reset: () => void;
};

const initialTriage: Triage = { level: null, score: null, reasoning: null };

export const useChatStore = create<ChatState>((set) => ({
  conversationId: null,
  streamState: "idle",
  triage: initialTriage,
  redFlags: [],
  activeTool: null,
  lastError: null,

  setConversation: (id) => set({ conversationId: id }),
  setStreamState: (streamState) => set({ streamState }),
  setTriage: (t) => set((s) => ({ triage: { ...s.triage, ...t } })),
  pushRedFlag: (flag) => set((s) => ({ redFlags: [...s.redFlags, flag] })),
  setActiveTool: (activeTool) => set({ activeTool }),
  setError: (lastError) => set({ lastError, streamState: lastError ? "error" : "idle" }),
  reset: () =>
    set({
      conversationId: null,
      streamState: "idle",
      triage: initialTriage,
      redFlags: [],
      activeTool: null,
      lastError: null,
    }),
}));
