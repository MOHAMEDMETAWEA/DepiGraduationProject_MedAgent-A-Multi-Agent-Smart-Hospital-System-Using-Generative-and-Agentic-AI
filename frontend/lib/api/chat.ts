import { apiRequest } from "./client";

export type Conversation = {
  id: string;
  title: string | null;
  status: string;
  triage_level: string | null;
  triage_score: number | null;
  language: string;
  red_flags_detected: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message: string | null;
};

export type Message = {
  id: string;
  role: string;
  content: string;
  citations: Array<Record<string, unknown>>;
  tool_calls: Array<Record<string, unknown>>;
  tool_name: string | null;
  created_at: string;
};

export type ChatEvent = {
  type: "token" | "tool_start" | "tool_result" | "thinking" | "triage" | "red_flag" | "error" | "done";
  content: string;
  data: Record<string, unknown>;
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const chatApi = {
  createConversation: async (language: string = "ar") =>
    apiRequest<Conversation>("/conversations", {
      method: "POST",
      body: { language },
    }),

  listConversations: async (page = 1, status?: string) =>
    apiRequest<{ items: Conversation[]; total: number }>(
      `/conversations?page=${page}&page_size=20${status ? `&status=${status}` : ""}`
    ),

  getConversation: async (id: string) =>
    apiRequest<Conversation>(`/conversations/${id}`),

  deleteConversation: async (id: string) =>
    apiRequest(`/conversations/${id}`, { method: "DELETE" }),

  getMessages: async (convId: string) =>
    apiRequest<Message[]>(`/conversations/${convId}/messages`),

  streamChat: async function* (
    convId: string,
    message: string,
    token: string,
    model?: string,
    imageData?: string,
    imageKind?: string,
    visionProvider?: string,
    visionModel?: string
  ): AsyncGenerator<ChatEvent> {
    const body: Record<string, string> = { message };
    if (model) body.model = model;
    if (imageData) body.image_data = imageData;
    if (imageKind) body.image_kind = imageKind;
    if (visionProvider) body.vision_provider = visionProvider;
    if (visionModel) body.vision_model = visionModel;

    const makeRequest = (authToken: string) =>
      fetch(`${API}/conversations/${convId}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(body),
      });

    let response = await makeRequest(token);

    // Auto-refresh on 401
    if (response.status === 401) {
      try {
        const refreshRes = await fetch(`${API}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            refresh_token: JSON.parse(
              localStorage.getItem("medagent-auth") || "{}"
            ).state?.refreshToken,
          }),
        });
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          response = await makeRequest(data.access_token);
        }
      } catch {
        // refresh failed, use original response
      }
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err?.detail || "Chat request failed");
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const raw = line.slice(6);
          if (!raw.trim()) continue;
          try {
            const event: ChatEvent = JSON.parse(raw);
            yield event;
          } catch {
            // skip malformed lines
          }
        }
      }
    }
  },
};
