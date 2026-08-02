# MedAgent — API Reference

> **Base URL:** `/api/v1` | **Version:** 0.1.0

## Conventions

- All requests/responses: JSON (except SSE chat: `text/event-stream`)
- Auth: `Authorization: Bearer <jwt>` for protected endpoints
- Errors: `{"error": {"code": "...", "message": "...", "details": {...}}}`
- Pagination: `?page=1&per_page=20` → `{"items": [...], "total": N, "page": 1, "per_page": 20}`

## Auth Endpoints

Rate limit: 5 requests/min/IP.

### POST /auth/register

Register a new user (patient or doctor).

```
Body: {
  email: string,
  password: string,
  full_name: string,
  phone?: string,
  role: "patient" | "doctor" | "admin",
  locale?: "ar" | "en",
  license_number?: string,     // required for doctor
  specialty?: string           // required for doctor
}
201: { user_id, email, role, requires_email_verification: true }
Side effects: sends verification email; doctor goes to pending approval queue
```

### POST /auth/login

Authenticate and receive tokens.

```
Body: { email: string, password: string }
200: { access_token, refresh_token, user: { id, email, full_name, role, locale } }
401: invalid credentials | email_not_verified | doctor_not_approved | account_disabled
```

### POST /auth/refresh

Rotate tokens. Single-use refresh tokens.

```
Body: { refresh_token: string }
200: { access_token, refresh_token }
```

### POST /auth/logout

Invalidate refresh token.

```
Headers: Authorization: Bearer <jwt>
Body: { refresh_token: string }
204: No Content
```

### POST /auth/verify-email

Verify email with token from registration email.

```
Body: { token: string }
200: { verified: true }
```

### POST /auth/resend-verification

Resend verification email. Rate limit: 1/min/IP per email.

```
Body: { email: string }
200: { sent: true }
```

### POST /auth/forgot-password

Request password reset link.

```
Body: { email: string }
200: { sent: true }    // always 200 to prevent enumeration
```

### POST /auth/reset-password

Reset password with token.

```
Body: { token: string, new_password: string }
200: { reset: true }
```

### POST /auth/change-password

Change password while authenticated. Revokes all other refresh tokens.

```
Headers: Authorization: Bearer <jwt>
Body: { current_password: string, new_password: string }
200: { changed: true }
```

## User Endpoints

Rate limit: 60/min/user.

### GET /users/me

Get current user profile.

```
200: { id, email, full_name, role, locale, phone?, avatar_url?, ... }
```

### PUT /users/me

Update basic user info.

```
Body: { full_name?, phone?, locale?, avatar_url? }
200: updated user object
```

### PATCH /users/me/profile

Update role-specific profile (patient or doctor).

```
200: updated profile object
```

### DELETE /users/me

Soft delete account (anonymizes data).

```
200: { deleted: true }
```

## Conversation / Chat Endpoints

Rate limit: 20/min/user.

### POST /conversations

Start a new conversation.

```
Body: { initial_message?: string, language?: "ar" | "en" }
201: { conversation_id, title? }
```

### GET /conversations

List user's conversations (paginated).

```
Query: ?status=active&page=1&per_page=20
200: { items: Conversation[], total, page, per_page }
```

### GET /conversations/{id}

Get conversation with messages.

```
200: { conversation: Conversation, messages: Message[] }
```

### DELETE /conversations/{id}

Soft delete a conversation.

```
200: { deleted: true }
```

### POST /conversations/{id}/chat

Send a message and receive streaming AI response.

```
Headers: Accept: text/event-stream
Body: { message: string, model?: string }
200: SSE stream

SSE Events:
  event: token       data: {"content": "..."}
  event: tool_start  data: {"name": "...", "input": {...}}
  event: tool_result data: {"name": "...", "output": {...}}
  event: citation    data: {"source": "...", "title": "...", "url": "..."}
  event: triage      data: {"level": "emergency|urgent|routine", "score": 85, "reasoning": "..."}
  event: safety      data: {"hallucination_score": 0.05, "uncertainty": "low"}
  event: done        data: {"message_id": "..."}
  event: error       data: {"error": "..."}
```

### POST /conversations/{id}/messages/with-image

Send message with image for vision analysis.

```
Body (multipart): content (text), image (file), kind ("xray" | "ct" | "photo" | "skin")
201: { message_id, vision_analysis_id, triage }
```

### GET /conversations/{id}/triage

Get current triage state for a conversation.

```
200: { level, score, reasoning, recommended_actions }
```

## Handoff Endpoints

### POST /conversations/{id}/handoff

Generate a doctor handoff summary.

```
201: { handoff_id, summary_markdown, pdf_url }
```

### GET /handoffs/{id}/pdf

Download handoff summary as PDF.

```
200: application/pdf (binary)
```

### GET /handoffs/{id}/export

Export handoff in FHIR R4 or HL7 v2 format.

```
Query: ?format=fhir|hl7
200 (fhir): application/fhir+json — FHIR R4 Bundle
200 (hl7):  application/hl7-v2 — HL7 v2.5 message
```

### POST /handoffs/{id}/send

Send handoff to a specific doctor.

```
Body: { doctor_user_id: string }
200: { sent: true }
```

### GET /handoffs/{id}

View a handoff summary (doctor or owner).

```
200: full handoff object with summary_markdown
```

### POST /handoffs/{id}/review

Mark handoff as reviewed by doctor.

```
Body: { notes?: string }
200: { reviewed: true }
```

## Doctor Endpoints

### GET /doctors/me/inbox

List handoffs received by the doctor.

```
Query: ?page=1&per_page=20
200: { items: Handoff[], total, page, per_page }
```

## Admin Endpoints

Admin role required for all endpoints below.

### GET /admin/dashboard

Platform statistics.

```
200: {
  total_users: number,
  active_today: number,
  safety_incidents_this_week: number,
  pending_doctors: number,
  system_health: string
}
```

### GET /admin/users

List all users (paginated, filterable).

```
Query: ?role=patient&search=ahmed&page=1&per_page=20
200: { items: AdminUser[], total, page, per_page }
```

### PATCH /admin/users/{id}

Update user status or role.

```
Body: { is_active?: boolean, role?: string }
200: { updated: true }
```

### GET /admin/doctors/pending

List doctors awaiting approval.

```
200: { items: PendingDoctor[] }
```

### POST /admin/doctors/{id}/approve

Approve a doctor's registration.

```
200: { approved: true }
```

### POST /admin/doctors/{id}/reject

Reject a doctor's registration.

```
Body: { reason: string }
200: { rejected: true }
```

### GET /admin/safety-incidents

List conversations flagged for safety review.

```
Query: ?page=1&per_page=20
200: { items: SafetyIncident[], total, page, per_page }
```

### GET /admin/safety-stats

Aggregated safety statistics.

```
200: {
  total_assessments, hallucination_avg, hallucination_rate,
  citation_avg, citation_rate, uncertainty_distribution,
  triage_inconsistencies, forbidden_phrase_rewrites_total,
  flagged_conversations
}
```

### GET /admin/audit-logs

Browse audit trail (filterable).

```
Query: ?user_id=...&action=...&page=1&per_page=20
200: { items: AuditLogEntry[], total, page, per_page }
```

### GET /admin/audit-verify

Verify hash-chain integrity of audit trail.

```
200: { ok: boolean, last_sequence: number, broken_at?: number }
```

## Support Endpoints

### GET /support/faq

List FAQ items (public, cached).

```
200: FAQ items array
```

### POST /support/contact

Submit contact form.

```
Body: { email: string, subject: string, message: string }
201: { ticket_id: string }
```

## Health / Meta Endpoints

### GET /health

Liveness check.

```
200: { status: "ok" }
```

### GET /health/ready

Readiness check (includes DB connectivity).

```
200: { status: "ready", checks: { db: "ok" } }
```

### GET /version

Build info.

```
200: { version: string, env: string, commit: string }
```

### GET /metrics

Prometheus exposition format (internal use only).
