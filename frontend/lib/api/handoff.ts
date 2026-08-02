import { apiRequest } from "./client";

export type DoctorPublic = {
  id: string;
  user_id: string;
  full_name: string;
  specialty: string;
  years_of_experience: number | null;
  languages: string[];
};

export type HandoffResponse = {
  id: string;
  conversation_id: string;
  patient_user_id: string;
  doctor_user_id: string | null;
  status: string;
  priority: number;
  sent_at: string | null;
  reviewed_at: string | null;
  doctor_private_notes: string | null;
  summary_markdown: string;
  pdf_url: string | null;
  created_at: string;
  updated_at: string;
};

export const handoffApi = {
  /** Generate a handoff summary from a conversation */
  generate: (conversationId: string) =>
    apiRequest<HandoffResponse>("/handoffs", {
      method: "POST",
      body: { conversation_id: conversationId },
    }),

  /** Send a generated handoff to a specific doctor */
  send: (handoffId: string, doctorUserId: string, message?: string) =>
    apiRequest<{ sent: boolean }>(`/handoffs/${handoffId}/send`, {
      method: "POST",
      body: { doctor_user_id: doctorUserId, message },
    }),

  /** List patient's own handoffs */
  list: (page = 1) =>
    apiRequest<{ items: HandoffResponse[]; total: number }>(
      `/handoffs?page=${page}&page_size=20`
    ),

  /** Get handoff detail */
  get: (handoffId: string) => apiRequest<HandoffResponse>(`/handoffs/${handoffId}`),
};

export const doctorApi = {
  /** Search approved doctors */
  search: (search?: string, specialty?: string, page = 1) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (specialty) params.set("specialty", specialty);
    params.set("page", String(page));
    params.set("page_size", "20");
    return apiRequest<{ items: DoctorPublic[]; total: number }>(
      `/doctors/available?${params.toString()}`
    );
  },
};
