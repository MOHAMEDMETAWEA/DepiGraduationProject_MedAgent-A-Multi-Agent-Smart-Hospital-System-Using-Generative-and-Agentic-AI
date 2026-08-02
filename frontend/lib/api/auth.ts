import { apiRequest } from "./client";

export type RegisterInput = {
  email: string;
  password: string;
  full_name: string;
  role?: string;
  locale?: string;
  license_number?: string;
  specialty?: string;
};

export type LoginInput = { email: string; password: string };

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  user: { id: string; email: string; full_name: string; role: string; locale: string };
};

export type RegisterResponse = {
  user_id: string;
  email: string;
  role: string;
  requires_email_verification: boolean;
};

export const authApi = {
  register: (body: RegisterInput) =>
    apiRequest<RegisterResponse>("/auth/register", { method: "POST", body }),
  login: (body: LoginInput) =>
    apiRequest<LoginResponse>("/auth/login", { method: "POST", body }),
  verifyEmail: (token: string) =>
    apiRequest("/auth/verify-email", { method: "POST", body: { token } }),
  forgotPassword: (email: string) =>
    apiRequest("/auth/forgot-password", { method: "POST", body: { email } }),
  resetPassword: (token: string, new_password: string) =>
    apiRequest("/auth/reset-password", {
      method: "POST",
      body: { token, new_password },
    }),
  logout: (refresh_token: string) =>
    apiRequest("/auth/logout", { method: "POST", body: { refresh_token } }),
};
