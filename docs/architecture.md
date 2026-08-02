# MedAgent — Architecture

> **Last updated:** 2026-05-06 | **Document version:** 2.0

## Overview

MedAgent is a bilingual (Arabic + English) medical triage AI assistant built with a microservice-inspired modular monolith architecture. The system separates concerns across four layers: HTTP (REST/SSE), Service (business logic), Agent (AI orchestration), and Data (persistence).

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         User (Browser)                            │
└──────────────────────────────┬───────────────────────────────────┘
                                │ HTTPS
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 16 on Vercel)                                 │
│  - App Router pages (Client Components)                          │
│  - Auth flow, chat UI, history, profile, doctor portal, admin    │
│  - shadcn/ui + Tailwind v4 + next-intl (AR/EN, RTL/LTR)         │
└──────────────────────────────┬───────────────────────────────────┘
                                │ REST / SSE
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  Backend API (FastAPI)                                           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ HTTP layer: routers, middleware (auth, CORS, rate limit,    │  │
│  │              audit log, error handler)                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Service layer: business logic per domain                    │  │
│  │ (auth, users, conversations, handoff, admin, support)       │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Agent layer: ReAct loop, tools, safety, prompts             │  │
│  │ (calls LLM, RAG, returns streaming tokens)                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Data layer: SQLAlchemy 2.0 (async), Alembic migrations      │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────┬───────────────────┬──────────────────┬────────────┬────────┘
      │                   │                  │            │
      ▼                   ▼                  ▼            ▼
┌──────────┐      ┌──────────────┐    ┌────────────┐  ┌────────┐
│PostgreSQL│      │ Vector store │    │ LLM        │  │ Redis  │
│ + pgvec  │      │ (pgvector)   │    │ (OpenRouter)│  │(rate   │
│          │      │              │    │            │  │ limit) │
└──────────┘      └──────────────┘    └────────────┘  └────────┘
```

## Layer Responsibilities

| Layer | Responsibility | Must NOT do |
|---|---|---|
| **HTTP layer (routers)** | Parse request, validate schema, call service, format response | Contain business logic, query DB directly |
| **Service layer** | Business logic, orchestrate repositories + agent | Know about HTTP details (status codes, headers) |
| **Agent layer** | LLM orchestration, tool calling, RAG, safety guards | Know about web framework, talk to DB tables directly |
| **Data layer (repos)** | DB queries, transactions | Contain business logic |
| **Frontend** | UI, optimistic updates, validation, presentation | Contain business logic that should be backend-enforced |

## Backend Module Structure

```
backend/app/
├── core/                     # Cross-cutting infra
│   ├── config.py             # Pydantic Settings
│   ├── database.py           # Async engine, session factory
│   ├── security.py           # JWT, password hash
│   ├── deps.py               # FastAPI dependencies (auth, rate limit)
│   ├── exceptions.py         # Custom exception hierarchy + handlers
│   ├── middleware.py          # CORS, audit, rate limit
│   ├── encryption.py         # PHI encryption (Fernet AES-256)
│   ├── logging.py            # structlog config
│   └── email.py              # Email sender
│
├── modules/                  # Domain modules
│   ├── auth/                 # Auth (register, login, refresh, verify, reset)
│   ├── users/                # Profile CRUD
│   ├── conversations/        # Chat sessions + messages + SSE streaming
│   ├── handoff/              # Doctor handoff summaries + PDF + FHIR/HL7
│   ├── doctors/              # Doctor accounts + inbox
│   ├── admin/                # Dashboard, user mgmt, audit, safety
│   ├── support/              # FAQ + contact form
│   └── notifications/        # Email notifications
│
├── ai/                       # Agent + AI layer
│   ├── llm/                  # LLM provider abstraction (OpenAI-compat, HF)
│   ├── retrieval/            # RAG: embeddings, vector store, reranker
│   ├── agent/                # ReAct loop, tool registry, prompts
│   ├── tools/                # 15 clinical tools
│   ├── safety/               # Multi-stage safety pipeline
│   └── nlp/                  # Language detect, Arabic norm, PII scrub
│
├── models/                   # SQLAlchemy models (15 tables)
├── common/                   # Shared utilities (pagination, PDF, audit)
└── main.py                   # FastAPI app entry, router registration
```

## Communication Patterns

| Pattern | Where | Notes |
|---|---|---|
| Direct function call | Service ↔ Repository | Same process, sync/async function call |
| Direct function call | Service ↔ Agent | Same process; agent is a Python class |
| HTTP REST | Frontend ↔ Backend | Standard requests; auth via Bearer JWT |
| SSE (Server-Sent Events) | Backend → Frontend (chat) | One-way streaming during AI generation |
| Background task | FastAPI BackgroundTasks | Email sending, audit log writes |
| External HTTP | Backend → LLM provider | Via httpx async client |
| External HTTP | Backend → SMTP | Via aiosmtplib |

## Frontend Architecture

### Routing Structure (App Router + next-intl)

```
app/[locale]/
├── (auth)/                   # Public routes (no auth required)
│   ├── login/
│   ├── register/
│   ├── forgot-password/
│   ├── reset-password/
│   └── verify-email/
└── (app)/                    # Protected routes (auth required)
    ├── chat/                 # Chat interface
    │   ├── page.tsx          # New conversation
    │   └── [id]/             # Existing conversation
    ├── history/              # Conversation history
    ├── profile/              # User profile
    ├── admin/                # Admin dashboard
    │   ├── dashboard/
    │   ├── users/
    │   ├── doctors/
    │   ├── audit/
    │   └── safety/
    ├── doctor/               # Doctor portal
    │   ├── inbox/
    │   └── handoff/
    └── support/
        ├── faq/
        └── contact/
```

### State Management Strategy

| State kind | Tool | Example |
|---|---|---|
| Server state | Direct API calls | Conversations list, user profile |
| Auth state | Zustand (persisted) | Access token, current user, role |
| Form state | react-hook-form + Zod | Login, register, profile forms |
| Navigation state | URL params | Filters, pagination |

### Internationalization (i18n)

- **Library:** `next-intl` for translations
- **Locales:** `ar` (default), `en`
- **Locale routing:** `as-needed` prefix (Arabic = no prefix, English = `/en`)
- **RTL/LTR:** Auto-detected via `<html lang>` and `dir` attributes
- **Translation files:** `frontend/messages/ar.json`, `frontend/messages/en.json`

## AI Agent Architecture

### ReAct Loop

The MedAgent follows a ReAct-style agent loop:

1. **Pre-flight:** Language detection, Arabic normalization, PII scrubbing
2. **Red-flag fast path:** Emergency keywords bypass the LLM entirely
3. **Build prompt:** System prompt + conversation history + tool specs
4. **Agent loop** (max 5 iterations):
   - LLM responds with either final answer or tool call
   - If tool call: execute tool, append result to context, continue loop
   - If final: proceed to safety verification
5. **Safety verification:** Post-LLM hallucination detection, uncertainty calibration
6. **Response formatting:** Final response with citations and triage

### Tool System

The agent uses a pluggable tool registry (`ToolRegistry`) with 15 clinical tools:

| Tool | Purpose |
|---|---|
| `retrieve_medical_knowledge` | RAG over curated medical knowledge base |
| `score_triage` | Manchester Triage Scale assessment |
| `detect_red_flags` | Emergency keyword + pattern detection |
| `summarize_for_doctor` | Generate structured handoff summary |
| `format_soap` | SOAP note formatting |
| `tot_differential_diagnosis` | Tree-of-Thought differential diagnosis |
| `analyze_vision` | Preliminary medical image triage |
| `verify_no_hallucination` | Clinical claim verification |
| `calibrate_uncertainty` | Confidence calibration |
| `check_medication_interactions` | Drug-drug + allergy + dose safety |
| `screen_mental_health` | PHQ-9 / GAD-7 screening |
| `assess_pediatric_safety` | Age-aware pediatric safety gate |
| `assess_pregnancy_safety` | OB red flags + pregnancy category warnings |

## Database Design

### Core Tables

- **users** — All user types (patient, doctor, admin)
- **patient_profiles** — Extended patient data (1:1 with users)
- **doctor_profiles** — License, specialty, approval status
- **auth_tokens** — Email verification + password reset tokens
- **refresh_tokens** — Single-use rotated refresh tokens
- **conversations** — Chat sessions with triage state
- **messages** — Individual messages with optional encryption
- **handoff_summaries** — Doctor handoff documents
- **handoff_exports** — FHIR R4 / HL7 v2 / PDF exports
- **safety_assessments** — Post-LLM verification records
- **vision_analyses** — Per-image analysis records
- **medication_records** — Normalized patient medications
- **kb_chunks** — Knowledge base for RAG (with pgvector embeddings)
- **audit_logs** — Hash-chained tamper-evident audit trail
- **support_tickets** — Help and contact form submissions
- **notification_log** — Email notification history

### Conventions

- **Primary keys:** UUID v4
- **Timestamps:** `TIMESTAMPTZ` with defaults
- **Soft delete:** `deleted_at` on user-facing entities
- **Foreign keys:** `ON DELETE CASCADE` for owned data, `ON DELETE SET NULL` for references
- **Indexes:** All FKs, all WHERE-filtered columns
- **Migrations:** Alembic with auto-run on startup in non-prod

## Extensibility Seams

The system is designed for extension at these points:

1. **Tool registry** (`ai/agent/registry.py`) — Register new tools by implementing the `Tool` ABC
2. **LLM provider** (`ai/llm/base.py`) — New providers implement `LLMProvider` protocol
3. **Vector store** (`ai/retrieval/vectorstore.py`) — New stores implement `VectorStore` protocol
4. **Knowledge sources** — Drop ingestion scripts into `scripts/kb/` and register in `kb_registry.yaml`
5. **Notification channels** — New channels implement `NotificationChannel` protocol

## Infrastructure

### Docker Services

| Service | Image | Port |
|---|---|---|
| PostgreSQL 17 + pgvector | `pgvector/pgvector:pg17` | 5432 |
| Redis 7 | `redis:7-alpine` | 6379 |
| Mailpit (dev SMTP) | `axllent/mailpit` | 1025, 8025 |
| Backend (FastAPI) | Custom Dockerfile | 8000 |
| Frontend (Next.js) | Custom Dockerfile | 3000 |

### Deployment Targets

| Component | Target |
|---|---|
| Frontend | Vercel (serverless) |
| Backend | Railway / Render |
| Database | Neon / Supabase (managed Postgres) |
| LLM | OpenRouter / HuggingFace Inference |
