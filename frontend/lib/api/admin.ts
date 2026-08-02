import { apiRequest } from "./client";

export type DashboardStats = {
  total_users: number;
  active_today: number;
  safety_incidents_this_week: number;
  pending_doctors: number;
  system_health: string;
};

export type AdminUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
};

export type PendingDoctor = {
  id: string;
  user_id: string;
  license_number: string;
  specialty: string;
  created_at: string;
};

export type SafetyIncident = {
  id: string;
  title: string | null;
  triage_level: string | null;
  created_at: string;
};

export type AuditLogEntry = {
  id: string;
  sequence: number;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  created_at: string;
};

export type SafetyStats = {
  total_assessments: number;
  hallucination_avg: number | null;
  hallucination_rate: number | null;
  citation_avg: number | null;
  citation_rate: number | null;
  uncertainty_distribution: Record<string, number>;
  triage_inconsistencies: number;
  forbidden_phrase_rewrites_total: number;
  flagged_conversations: number;
};

export type AuditVerifyResult = {
  ok: boolean;
  last_sequence: number;
  broken_at: number | null;
};

export const adminApi = {
  getDashboard: () =>
    apiRequest<DashboardStats>("/admin/dashboard"),

  listUsers: (params?: { role?: string; search?: string; page?: number }) => {
    const qs = new URLSearchParams();
    if (params?.role) qs.set("role", params.role);
    if (params?.search) qs.set("search", params.search);
    if (params?.page) qs.set("page", String(params.page));
    return apiRequest<{ items: AdminUser[]; total: number; page: number; page_size: number }>(
      `/admin/users?${qs.toString()}`
    );
  },

  updateUser: (userId: string, body: { is_active?: boolean; role?: string }) =>
    apiRequest<{ updated: boolean }>(`/admin/users/${userId}`, {
      method: "PATCH",
      body,
    }),

  getPendingDoctors: () =>
    apiRequest<{ items: PendingDoctor[] }>("/admin/doctors/pending"),

  approveDoctor: (doctorId: string) =>
    apiRequest<{ approved: boolean }>(`/admin/doctors/${doctorId}/approve`, {
      method: "POST",
    }),

  rejectDoctor: (doctorId: string, reason: string) =>
    apiRequest<{ rejected: boolean }>(`/admin/doctors/${doctorId}/reject`, {
      method: "POST",
      body: { reason },
    }),

  getSafetyIncidents: (page?: number) =>
    apiRequest<{ items: SafetyIncident[]; total: number; page: number; page_size: number }>(
      `/admin/safety-incidents?page=${page || 1}&page_size=20`
    ),

  getAuditLogs: (params?: { user_id?: string; action?: string; page?: number }) => {
    const qs = new URLSearchParams();
    if (params?.user_id) qs.set("user_id", params.user_id);
    if (params?.action) qs.set("action", params.action);
    if (params?.page) qs.set("page", String(params.page));
    return apiRequest<{ items: AuditLogEntry[]; total: number; page: number; page_size: number }>(
      `/admin/audit-logs?${qs.toString()}`
    );
  },

  verifyAuditChain: () =>
    apiRequest<AuditVerifyResult>("/admin/audit-verify"),

  getSafetyStats: () =>
    apiRequest<SafetyStats>("/admin/safety-stats"),
};
