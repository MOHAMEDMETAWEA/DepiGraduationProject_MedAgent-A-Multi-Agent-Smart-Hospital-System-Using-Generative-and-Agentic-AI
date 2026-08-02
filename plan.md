# MedAgent — Master Project Plan & Specification

> **Document purpose.** This is the canonical specification for MedAgent. Anyone (the project owner, a teammate, or another AI assistant) should be able to read this end-to-end and execute the project with no further context. Each section is self-contained; tasks at the end are the execution units. A task is "done" only when **every** acceptance criterion is met.

> **How to use this plan.** Read §1–§3 to understand what we're building. Read §4–§12 to understand the system design. Execute §13 task-by-task in order — each task references the relevant design sections. Use §14 (acceptance criteria) and §15 (verification) to confirm completion.

---

## 0. Status & metadata

| Field | Value |
|---|---|
| Project | MedAgent — Bilingual Medical Triage Agent |
| Owner | Hossam Hassan (DEPI AI & Data Science Track, Round 2) |
| Document version | 2.0 |
| Created | 2026-04-29 |
| Last spec update | 2026-05-01 (added specialized tools, vision, FHIR/HL7, glassmorphic UI, PHI encryption, observability) |
| Quality bar | Production-grade |
| Working dir | `/Users/hossamhassan/Documents/Labs/Projects/FinalProject_MedAgent` |
| Repo target | `github.com/<user>/medagent` |

---

## 1. Vision

**MedAgent** is a bilingual (Arabic + English) medical triage AI assistant. A patient describes symptoms in natural language; MedAgent asks structured follow-up questions, retrieves grounded medical knowledge, and produces:

1. A **triage assessment** (emergency / urgent / routine).
2. A **differential diagnosis** with confidence scores and supporting evidence.
3. A **safe recommended next action** (e.g., "go to ER", "book GP visit", "self-care + monitor").
4. A **doctor handoff summary** — a structured PDF the patient can print or send to a clinician.

The agent is grounded in retrieved medical guidelines, never hallucinates clinical claims, escalates red-flag symptoms immediately, and always defers final clinical judgment to a licensed physician.

### What makes this project distinctive
1. **Arabic medical NLP** — most medical AI serves English speakers; we serve Arabic-speaking patients with the same quality.
2. **True agent architecture** — not a passive chatbot. ReAct-style planning loop with tool calling.
3. **Safety-first, evidence-grounded** — every clinical claim cites a retrieved source; red-flag detector overrides the agent.
4. **Production-grade engineering** — proper auth, RBAC, audit trail, tests, CI/CD, monitoring, deployment.
5. **Bilingual code-switching** — handles patients who mix Arabic and English in the same message (extremely common in Egypt).

---

## 2. Scope

### 2.1 In scope (MedAgent will do all of this)

**Patient experience**
- Sign up / sign in (email + password, email verification, password reset)
- Onboarding: profile (age, gender, allergies, chronic conditions, current medications, language preference)
- Chat with MedAgent (multi-turn, streaming responses, citations)
- Conversation history (list, view, resume, delete)
- Triage assessment view (level + recommended actions + supporting evidence)
- Doctor handoff summary — generate, preview, download as PDF, optionally email to a doctor
- Profile management (update info, change password, delete account)
- Help & Support page (FAQ + contact form)

**Doctor experience**
- Doctor account type (registration with license number verification — manual approval by admin in MVP)
- Inbox: handoff summaries forwarded by patients
- View patient handoff (read-only)
- Mark handoff as reviewed / add private notes
- Profile management

**Admin experience**
- Login (admin role)
- Dashboard: total users, active conversations today, safety incidents this week, system health
- User management (list, search, deactivate, change role)
- Doctor approval queue (review license numbers, approve/reject)
- Safety incidents review (red-flag conversations flagged for review)
- Audit log viewer (filter by user, action, date range)

**AI Agent capabilities**
- Multi-turn medical conversation
- Bilingual (AR/EN) including code-switching
- RAG over a curated medical knowledge base (WHO guidelines, MedlinePlus, peer-reviewed Q&A)
- **Core tools:** retrieve knowledge, score triage, detect red flags, summarize for doctor
- **Specialized clinical tools:**
  - Medication safety check — drug-drug interaction detection + dose verification
  - Mental health screening — PHQ-9 (depression), GAD-7 (anxiety) standardized scales
  - Pediatric safety branch — age-aware dose checks, age-appropriate red flags
  - Pregnancy safety branch — OB red flags, drug pregnancy-category warnings
  - Vision analysis — clinical photo / X-ray / CT preliminary triage (preliminary only, not radiology replacement)
  - SOAP note formatter — clinician-style structured notes from a conversation
- **Reasoning:** ReAct loop by default; **Tree-of-Thought (ToT)** mode for differential diagnosis under uncertainty
- **Safety pipeline (multi-stage):** input scrub + red-flag fast path → in-LLM rules → post-LLM hallucination detector + uncertainty calibrator + forbidden-phrase rewriter
- **Interoperability:** Doctor handoff exportable as **FHIR R4 Bundle JSON** and **HL7 v2** message
- Streaming responses (SSE)

**ML pipeline**
- Data ingestion + preprocessing (medical dialogues, knowledge base PDFs)
- LoRA fine-tuning on a multilingual base model
- Evaluation suite (BLEU, ROUGE, BERTScore, triage accuracy, hallucination rate, safety recall)
- MLflow experiment tracking & model registry
- Knowledge base build pipeline (chunk → embed → upsert to vector store)

**Operations**
- Auth emails (verify, reset)
- Smart medical follow-up emails (red-flag conversations get a follow-up reminder)
- Audit logging (every state-changing operation)
- Rate limiting (per-IP for auth, per-user for AI endpoints)
- Monitoring (errors → Sentry, metrics → simple stats)
- Deployment (frontend → Vercel, backend → Railway/Render, DB → Neon/Supabase)
- CI/CD (GitHub Actions: lint + test + build + deploy)

### 2.2 Out of scope (explicit non-deliverables — protect against scope creep)

- ❌ **Appointment booking system** (slot management, calendar sync) — this is a separate product.
- ❌ **In-system doctor-patient live messaging** — handoff is one-way (patient → doctor inbox).
- ❌ **Insurance / billing / payments**
- ❌ **Lab results entry workflow**
- ❌ **Prescription writing module** (potential post-MVP extension via tool registry)
- ❌ **Full DICOM medical image viewer / radiology workstation** — we do *preliminary* image triage via the `analyze_vision` tool (Phase 2), but never replace a radiologist or render full DICOM
- ❌ **Direct EHR write-back** — we generate FHIR/HL7 bundles for export, but never write into a hospital EHR
- ❌ **Live video consultations / telemedicine streaming**
- ❌ **Multi-tenant / hospital-wide deployment**
- ❌ **HIPAA / regulated healthcare compliance certification** (we follow best practices; we don't claim compliance)
- ❌ **Mobile native apps** (web is responsive and PWA-ready; native is post-MVP)
- ❌ **Live human chat support** (we have a contact form that emails admin)

### 2.3 User personas

**P1 — Patient (Sara, 32)**
Egyptian, primary Arabic speaker, sometimes types in English/franco. Worried about a symptom but not sure if she should see a doctor. Wants a quick, trustworthy assessment in her language.

**P2 — Doctor (Dr. Ahmed, 45)**
General practitioner. Receives MedAgent handoff summaries from patients before consultations. Wants a clean structured summary to save intake time. Will not use the system to diagnose; uses it as a chart prep tool.

**P3 — Admin (Mona, 30)**
Project owner / system operator. Monitors system health, approves doctor accounts, reviews safety incidents.

---

## 3. Tech stack

Every choice has a justification. No "we picked it because it's popular."

### 3.1 Backend

| Tool | Version | Why |
|---|---|---|
| Python | 3.11+ | Stable, fast, broad ML library support. (3.14 is fine but 3.11 is the conservative target for libraries.) |
| FastAPI | 0.110+ | Async-first, OpenAPI auto-gen, Pydantic validation built-in, dependency injection |
| SQLAlchemy | 2.0+ (async) | Type-safe, mature, async support, broad DB compatibility |
| Alembic | 1.13+ | DB migrations, integrates with SQLAlchemy |
| Pydantic | 2.x | Settings, request/response validation, type safety |
| asyncpg | latest | Fast PostgreSQL async driver |
| python-jose[cryptography] | latest | JWT signing (RS256) |
| passlib[bcrypt] | latest | Password hashing |
| python-multipart | latest | Form/file uploads |
| httpx | latest | Async HTTP client (calling LLM APIs, etc.) |
| pytest + pytest-asyncio | latest | Testing |
| pytest-cov | latest | Coverage reporting |
| ruff | latest | Linting + formatting (replaces black + flake8 + isort) |
| mypy | latest | Static type checking |
| sentry-sdk | latest | Error monitoring |
| structlog | latest | Structured JSON logging |
| slowapi | latest | Rate limiting (Redis-backed) |
| aiosmtplib | latest | Async email sending |
| jinja2 | latest | Email templates |
| weasyprint | latest | PDF generation (doctor handoff) |
| cryptography[fernet] | latest | AES-256 envelope encryption for PHI fields |
| prometheus-client | latest | `/metrics` endpoint for Prometheus scraping |
| opentelemetry-api / opentelemetry-sdk | latest | Distributed tracing |
| opentelemetry-instrumentation-fastapi | latest | Auto-instrument FastAPI handlers |
| opentelemetry-exporter-otlp | latest | Export traces to Grafana Tempo / Jaeger |
| fhir.resources | 7.x | FHIR R4 Pydantic models for handoff export |
| hl7 | latest | HL7 v2 message parsing/generation |
| Pillow | latest | Image preprocessing for `analyze_vision` tool |

### 3.2 Frontend

| Tool | Version | Why |
|---|---|---|
| Next.js | 14 (App Router) | React Server Components, file-based routing, edge-ready, Vercel-optimized |
| React | 18 | Standard |
| TypeScript | 5.x (strict mode) | Type safety end-to-end |
| Tailwind CSS | 3.x | Utility-first, consistent design tokens |
| shadcn/ui | latest | Accessible, customizable components built on Radix UI |
| Radix UI | (via shadcn) | Accessible primitives |
| Lucide React | latest | Icons |
| @radix-ui/react-progress | latest | Triage / safety meter visualizations |
| @radix-ui/react-tooltip | latest | Citation / confidence-band hover details |
| TanStack Query | v5 | Server state, caching, optimistic updates |
| Zustand | latest | Client state (auth, UI preferences) |
| react-hook-form | latest | Forms |
| Zod | latest | Schema validation (shared backend ↔ frontend) |
| next-intl | latest | i18n (Arabic + English) |
| framer-motion | latest | Subtle animations (used sparingly) |
| pnpm | latest | Faster installs, monorepo-friendly |
| Vitest | latest | Unit testing |
| Playwright | latest | E2E testing |
| ESLint | latest | Linting |

### 3.3 AI / ML

| Tool | Version | Why |
|---|---|---|
| HuggingFace Transformers | 4.40+ | Standard for transformer models |
| HuggingFace `peft` | latest | LoRA / QLoRA |
| HuggingFace `trl` (SFTTrainer) | latest | Supervised fine-tuning |
| HuggingFace `datasets` | latest | Dataset loading |
| HuggingFace `accelerate` | latest | Multi-GPU / mixed precision |
| HuggingFace `evaluate` | latest | BLEU/ROUGE/BERTScore |
| sentence-transformers | latest | Embeddings |
| FAISS | latest | Vector store (CPU OK for our scale; <1M vectors) |
| `pgvector` (alt) | latest | Postgres-native vector store, used in production |
| LangChain (selectively) | latest | We use specific utilities (text splitters), NOT the full agent framework |
| MLflow | 2.x | Experiment tracking, model registry |
| PyTorch | 2.x | DL framework |
| bitsandbytes | latest | 4-bit quantization |
| Apache Airflow OR Prefect | latest | Pipeline orchestration |
| Jupyter | latest | Notebooks for exploration |

**Base LLM choice**
- **Primary candidate:** `Qwen/Qwen2.5-7B-Instruct` (multilingual including strong Arabic, fits in Colab T4 with 4-bit)
- **Backup A:** `meta-llama/Llama-3.1-8B-Instruct` with translation pre-pass for AR
- **Backup B:** `inceptionai/jais-13b-chat` (Arabic-first; needs more compute)
- Decision is finalized in Task T3.03 after a small benchmark on triage prompts.

**Embedding model**
- `intfloat/multilingual-e5-large` — strong multilingual, public, runs on CPU.

**Reranker**
- `BAAI/bge-reranker-v2-m3` — multilingual cross-encoder.

### 3.4 Data

| Tool | Why |
|---|---|
| PostgreSQL 16 | Primary DB; JSONB for flexible fields; pgvector for production embeddings |
| Redis | Cache, rate-limit counters, session blacklist |
| MinIO (S3-compatible, optional) | Future image storage; not in MVP |

### 3.5 DevOps & infra

| Tool | Why |
|---|---|
| Docker + docker-compose | Local dev parity |
| GitHub Actions | CI/CD |
| Vercel | Frontend hosting (free tier) |
| Railway OR Render | Backend + Postgres hosting (free tier) |
| Neon OR Supabase | Managed Postgres alternative (free tier) |
| HuggingFace Hub | Model hosting (LoRA adapters) |
| Sentry | Error monitoring (free tier) |

---

## 4. System architecture

### 4.1 High-level diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         User (Browser)                           │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTPS
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14 on Vercel)                                 │
│  - App Router pages (RSC where possible)                         │
│  - Auth flow, chat UI, history, profile, doctor portal, admin    │
│  - shadcn/ui + Tailwind + i18n (AR/EN, RTL/LTR)                  │
└──────────────────────────────┬───────────────────────────────────┘
                               │ REST / SSE
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  Backend API (FastAPI on Railway/Render)                         │
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
│  │ Data layer: SQLAlchemy models, repositories                 │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────┬───────────────────┬──────────────────┬────────────┬────────┘
      │                   │                  │            │
      ▼                   ▼                  ▼            ▼
┌──────────┐      ┌──────────────┐    ┌────────────┐  ┌────────┐
│PostgreSQL│      │ Vector store │    │ LLM        │  │ Redis  │
│ + pgvec  │      │ (pgvector or │    │ (HF / API) │  │(rate   │
│          │      │  FAISS)      │    │            │  │ limit) │
└──────────┘      └──────────────┘    └────────────┘  └────────┘
```

### 4.2 Layer responsibilities

| Layer | Responsibility | Must NOT do |
|---|---|---|
| **HTTP layer (routers)** | Parse request, validate schema, call service, format response | Contain business logic, query DB directly |
| **Service layer** | Business logic, orchestrate repositories + agent | Know about HTTP details (status codes, headers) |
| **Agent layer** | LLM orchestration, tool calling, RAG, safety guards | Know about web framework, talk to DB tables directly |
| **Data layer (repos)** | DB queries, transactions | Contain business logic |
| **Frontend** | UI, optimistic updates, validation, presentation | Contain business logic that should be backend-enforced |

### 4.3 Module boundaries (backend)

```
backend/app/
├── core/                     # Cross-cutting infra
│   ├── config.py             # Pydantic Settings
│   ├── database.py           # Async engine, session factory
│   ├── security.py           # JWT, password hash
│   ├── deps.py               # FastAPI dependencies
│   ├── exceptions.py         # Custom exception hierarchy + handlers
│   ├── middleware.py         # CORS, audit, rate limit
│   ├── logging.py            # structlog config
│   └── email.py              # Email sender
│
├── modules/                  # Domain modules (each owns models+schemas+service+router)
│   ├── auth/                 # Sign up, sign in, refresh, verify, reset
│   ├── users/                # Profile CRUD
│   ├── conversations/        # Chat sessions + messages
│   ├── handoff/              # Doctor handoff summaries
│   ├── doctors/              # Doctor accounts + inbox
│   ├── admin/                # User management, dashboard, audit
│   ├── support/              # FAQ + contact form
│   └── notifications/        # Email notifications
│
├── ai/                       # Agent + AI layer
│   ├── llm/                  # LLM provider abstraction
│   ├── retrieval/            # RAG: embeddings, vector store, reranker
│   ├── agent/                # ReAct loop, tool registry, prompts
│   ├── tools/                # Pluggable tools
│   ├── safety/               # Red-flag detector, disclaimers
│   └── nlp/                  # Language detect, Arabic norm, PII scrub
│
├── common/                   # Shared utilities
│   ├── pagination.py
│   ├── pdf.py                # PDF generation (handoff summaries)
│   └── audit.py              # Audit log helper
│
└── main.py                   # FastAPI app entry, router registration
```

### 4.4 Communication patterns

| Pattern | Where | Notes |
|---|---|---|
| Direct function call | Service ↔ Repository | Same process, sync or async function call |
| Direct function call | Service ↔ Agent | Same process; agent is just a Python class |
| HTTP REST | Frontend ↔ Backend | Standard requests; auth via Bearer JWT |
| SSE (Server-Sent Events) | Backend → Frontend (chat) | One-way streaming tokens during AI generation |
| Background task | FastAPI BackgroundTasks | Email sending, audit log writes (fire-and-forget) |
| External HTTP | Backend → LLM provider | Via httpx async client |
| External HTTP | Backend → SMTP | Via aiosmtplib |

### 4.5 Extensibility seams

These are the explicit places where extension is clean:

1. **Tool registry (`ai/agent/registry.py`)** — register a new agent tool by implementing the `Tool` ABC and calling `registry.register(tool)`. The agent loop never changes.
2. **LLM provider (`ai/llm/base.py`)** — new providers implement `LLMProvider` protocol. Selected via `LLM_PROVIDER` env var.
3. **Vector store (`ai/retrieval/vectorstore.py`)** — new stores implement `VectorStore` protocol. Selected via `VECTOR_STORE` env var.
4. **Knowledge sources** — drop a new ingestion script into `scripts/kb/` and register it in `kb_registry.yaml`.
5. **Notification channels** — new channels implement `NotificationChannel` protocol (e.g., add SMS later).

---

## 5. Database schema

### 5.1 Conventions

- Primary keys: UUID v4 (`gen_random_uuid()`)
- All timestamps: `TIMESTAMPTZ` with `DEFAULT NOW()`
- Soft delete: `deleted_at TIMESTAMPTZ NULL` on user-facing entities
- Audit columns: `created_at`, `updated_at` on all tables
- Foreign keys: ON DELETE CASCADE for owned data; ON DELETE SET NULL for references
- Indexes: any FK gets an index; any column used in WHERE gets an index
- JSONB used only for genuinely schemaless data (allergies, message metadata)

### 5.2 Core tables

```sql
-- Users (all roles)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL CHECK (role IN ('patient', 'doctor', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    locale VARCHAR(5) NOT NULL DEFAULT 'ar' CHECK (locale IN ('ar', 'en')),
    avatar_url VARCHAR(500),
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_role ON users(role);

-- Patient profiles (1:1 with users WHERE role='patient')
CREATE TABLE patient_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date_of_birth DATE,
    gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
    blood_type VARCHAR(5),
    allergies JSONB NOT NULL DEFAULT '[]',          -- ["penicillin", ...]
    chronic_conditions JSONB NOT NULL DEFAULT '[]', -- ["diabetes_type_2", ...]
    current_medications JSONB NOT NULL DEFAULT '[]',-- [{"name":"...","dose":"..."}]
    emergency_contact_name VARCHAR(255),
    emergency_contact_phone VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Doctor profiles (1:1 with users WHERE role='doctor')
CREATE TABLE doctor_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    license_number VARCHAR(100) UNIQUE NOT NULL,
    specialty VARCHAR(100) NOT NULL,
    bio TEXT,
    years_of_experience INTEGER,
    languages JSONB NOT NULL DEFAULT '["ar"]',
    approval_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_doctor_status ON doctor_profiles(approval_status);

-- Email verification + password reset tokens
CREATE TABLE auth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    purpose VARCHAR(20) NOT NULL CHECK (purpose IN ('email_verify', 'password_reset')),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_auth_tokens_user ON auth_tokens(user_id, purpose);

-- Refresh tokens (single-use, rotated)
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_refresh_user ON refresh_tokens(user_id);

-- Conversations (a chat session)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),                     -- auto-generated from first message
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'completed', 'abandoned', 'flagged_for_review')),
    triage_level VARCHAR(20) CHECK (triage_level IN ('emergency', 'urgent', 'routine')),
    triage_score INTEGER CHECK (triage_score BETWEEN 0 AND 100),
    primary_diagnosis VARCHAR(255),
    differential_diagnoses JSONB,           -- [{"name":"...","confidence":0.8}]
    red_flags_detected JSONB DEFAULT '[]',  -- ["chest_pain_radiating", ...]
    language VARCHAR(5) NOT NULL DEFAULT 'ar',
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_conv_patient ON conversations(patient_user_id);
CREATE INDEX idx_conv_status ON conversations(status);
CREATE INDEX idx_conv_created ON conversations(created_at DESC);

-- Messages within a conversation
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    content TEXT,                           -- plaintext when PHI_ENCRYPTION_ENABLED=false
    encrypted_content BYTEA,                -- Fernet ciphertext when PHI_ENCRYPTION_ENABLED=true
    citations JSONB DEFAULT '[]',           -- [{"source":"WHO","title":"...","url":"..."}]
    tool_calls JSONB DEFAULT '[]',          -- when role='assistant' uses tools
    tool_name VARCHAR(100),                 -- when role='tool'
    metadata JSONB,                         -- {"tokens_in": 42, "tokens_out": 100, "model":"..."}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (content IS NOT NULL OR encrypted_content IS NOT NULL)
);
CREATE INDEX idx_msg_conv ON messages(conversation_id, created_at);

-- Per-message safety assessment (post-LLM verification)
CREATE TABLE safety_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID UNIQUE NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    hallucination_score NUMERIC(4,3),       -- 0.000-1.000 from verification model
    citation_completeness NUMERIC(4,3),     -- ratio of clinical claims with citations
    uncertainty_band VARCHAR(20),           -- 'high'|'medium'|'low'
    calibration_metadata JSONB,             -- per-claim confidence breakdown
    forbidden_phrases_rewritten INT DEFAULT 0,
    triage_consistent BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_safety_msg ON safety_assessments(message_id);

-- Vision analysis records (one per uploaded image)
CREATE TABLE vision_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    image_url VARCHAR(500) NOT NULL,         -- signed URL or S3/MinIO path
    image_kind VARCHAR(20) NOT NULL CHECK (image_kind IN ('xray', 'ct', 'photo', 'skin', 'other')),
    analysis_markdown TEXT,                  -- plaintext OR encrypted via separate column below
    encrypted_analysis BYTEA,                -- when PHI_ENCRYPTION_ENABLED=true
    findings JSONB,                          -- structured findings list
    urgency VARCHAR(20),                     -- emergency|urgent|routine|none
    confidence NUMERIC(4,3),
    model_used VARCHAR(100),
    disclaimer_shown BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_vision_conv ON vision_analyses(conversation_id);

-- Patient medication records (normalized — supersedes JSON list in patient_profiles for lookups)
CREATE TABLE medication_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,              -- generic/RxNorm-preferred when known
    rxnorm_code VARCHAR(50),
    dose VARCHAR(100),
    frequency VARCHAR(100),
    route VARCHAR(50),                       -- oral|IV|topical|...
    started_at DATE,
    stopped_at DATE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_meds_patient ON medication_records(patient_user_id) WHERE stopped_at IS NULL;

-- Handoff exports (FHIR / HL7 / PDF artifacts per handoff)
CREATE TABLE handoff_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handoff_id UUID NOT NULL REFERENCES handoff_summaries(id) ON DELETE CASCADE,
    format VARCHAR(10) NOT NULL CHECK (format IN ('fhir', 'hl7', 'pdf')),
    content_url VARCHAR(500),                -- where the file lives (S3/MinIO/local)
    content_inline TEXT,                     -- small payloads can live in DB
    bytes INT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (handoff_id, format)
);
CREATE INDEX idx_handoff_exports_handoff ON handoff_exports(handoff_id);

-- Doctor handoff summaries
CREATE TABLE handoff_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID UNIQUE NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    patient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    doctor_user_id UUID REFERENCES users(id),  -- NULL = not yet sent to a doctor
    sent_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    doctor_private_notes TEXT,
    summary_markdown TEXT NOT NULL,
    pdf_url VARCHAR(500),                   -- where to fetch the PDF (signed URL or path)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_handoff_doctor ON handoff_summaries(doctor_user_id) WHERE doctor_user_id IS NOT NULL;

-- Knowledge base chunks (RAG)
CREATE TABLE kb_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(255) NOT NULL,           -- "WHO Guidelines 2024"
    source_url VARCHAR(500),
    section_title VARCHAR(500),
    content TEXT NOT NULL,
    language VARCHAR(5) NOT NULL,
    embedding vector(1024),                 -- multilingual-e5-large is 1024-dim
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_kb_embedding ON kb_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_kb_lang ON kb_chunks(language);

-- Audit log (every state-changing operation, hash-chained for tamper detection)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence BIGSERIAL UNIQUE NOT NULL,      -- strictly increasing chain order
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,            -- 'login', 'create_conversation', 'update_profile', etc.
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    previous_hash VARCHAR(64) NOT NULL,     -- hex SHA-256 of the prior chain link
    current_hash VARCHAR(64) NOT NULL,       -- hex SHA-256(previous_hash || canonical(row))
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_sequence ON audit_logs(sequence);

-- Support tickets (help & contact form)
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),       -- NULL allowed for non-logged-in
    email VARCHAR(255),
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    admin_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_support_status ON support_tickets(status);

-- Notification log (for emails sent)
CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('email')),
    template VARCHAR(50) NOT NULL,           -- 'verify_email', 'safety_followup', etc.
    recipient VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('queued', 'sent', 'failed', 'bounced')),
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notif_user ON notification_log(user_id);
```

### 5.3 Migration strategy

- Initial migration creates all of §5.2.
- Every schema change in subsequent phases is an Alembic revision, named with the task ID (e.g., `T2_05_add_streaming_metadata.py`).
- Migrations run automatically on backend startup in non-prod; manually triggered in prod.

---

## 6. API specification

### 6.1 Conventions

- Base path: `/api/v1`
- All requests/responses: JSON (except SSE chat, which is `text/event-stream`)
- Auth: `Authorization: Bearer <jwt>` header for protected endpoints
- Errors: standardized envelope `{"error": {"code": "...", "message": "...", "details": {...}}}` with appropriate HTTP status
- Pagination: `?page=1&per_page=20` → `{"items": [...], "total": N, "page": 1, "per_page": 20}`
- Validation errors: 422 with field-level details
- Rate limits: documented per endpoint group below

### 6.2 Auth endpoints (rate limit: 5/min/IP)

```
POST /api/v1/auth/register
  Body: { email, password, full_name, phone?, role: 'patient'|'doctor', locale }
  Doctor extras: { license_number, specialty }
  201: { user_id, email, role, requires_email_verification: true }
  Side effects: sends verification email; doctor goes to pending approval queue

POST /api/v1/auth/verify-email
  Body: { token }
  200: { verified: true }

POST /api/v1/auth/resend-verification
  Body: { email }
  200: { sent: true }
  (rate limit: 1/min/IP per email)

POST /api/v1/auth/login
  Body: { email, password }
  200: { access_token, refresh_token, user: {...} }
  401: invalid credentials | email_not_verified | doctor_not_approved | account_disabled

POST /api/v1/auth/refresh
  Body: { refresh_token }
  200: { access_token, refresh_token }  # both rotated

POST /api/v1/auth/logout
  Header: Bearer
  Body: { refresh_token }
  204

POST /api/v1/auth/forgot-password
  Body: { email }
  200: { sent: true }     # always 200 to avoid user enumeration

POST /api/v1/auth/reset-password
  Body: { token, new_password }
  200: { reset: true }

POST /api/v1/auth/change-password
  Header: Bearer
  Body: { current_password, new_password }
  200: { changed: true }  # also revokes all other refresh tokens
```

### 6.3 User endpoints (rate limit: 60/min/user)

```
GET  /api/v1/users/me                         # current user info
PUT  /api/v1/users/me                         # update full_name, phone, locale, avatar
PATCH /api/v1/users/me/profile                # patient or doctor profile update (role-aware)
DELETE /api/v1/users/me                       # soft delete + anonymization
```

### 6.4 Conversation / Chat endpoints (rate limit: 20/min/user)

```
POST /api/v1/conversations                    # start new conversation
  Body: { initial_message?, language? }
  201: { conversation_id, title? }

GET  /api/v1/conversations                    # list patient's conversations (paginated)
  Query: ?status=active&page=1&per_page=20
  200: { items: [...], total, page, per_page }

GET  /api/v1/conversations/{id}               # get conversation with messages
  200: { conversation: {...}, messages: [...] }

DELETE /api/v1/conversations/{id}             # soft delete

POST /api/v1/conversations/{id}/messages      # send message — STREAMING
  Header: Accept: text/event-stream
  Body: { content }
  200: SSE stream
    event: token       data: {"content": "..."}
    event: tool_call   data: {"name":"...","input":{...}}
    event: tool_result data: {"name":"...","output":{...}}
    event: citation    data: {"source":"...","title":"...","url":"..."}
    event: safety      data: {"hallucination_score":0.05,"uncertainty":"low"}
    event: complete    data: {"message_id":"...","triage":{...}}
    event: error       data: {"error":"..."}

POST /api/v1/conversations/{id}/messages/with-image    # multipart, triggers vision tool
  Body (multipart): content (text), image (file), kind (xray|ct|photo|skin)
  201: { message_id, vision_analysis_id, triage }

GET  /api/v1/conversations/{id}/triage         # current triage state
  200: { level, score, reasoning, recommended_actions }
```

### 6.5 Handoff endpoints

```
POST /api/v1/conversations/{id}/handoff       # generate handoff summary
  201: { handoff_id, summary_markdown, pdf_url }

GET  /api/v1/handoffs/{id}/pdf                # download PDF
  200: application/pdf

GET  /api/v1/handoffs/{id}/export?format=fhir|hl7   # interop export
  200 (fhir): application/fhir+json    — FHIR R4 Bundle
  200 (hl7):  application/hl7-v2       — HL7 v2.5 ADT^A04 + OBX segments
  Side effect: row inserted into handoff_exports

POST /api/v1/handoffs/{id}/send               # send to a doctor
  Body: { doctor_user_id }
  200: { sent: true }

# Doctor-side
GET  /api/v1/doctors/me/inbox                 # list received handoffs (paginated)
GET  /api/v1/handoffs/{id}                    # view handoff (doctor must be recipient)
POST /api/v1/handoffs/{id}/review             # mark reviewed + private notes
  Body: { notes? }
```

### 6.6 Admin endpoints (admin role only)

```
GET  /api/v1/admin/dashboard
  200: { total_users, active_today, safety_incidents_week, system_health }

GET  /api/v1/admin/users
  Query: ?role=patient&search=...&page=1
  200: paginated users

PATCH /api/v1/admin/users/{id}
  Body: { is_active?, role? }

GET  /api/v1/admin/doctors/pending
  200: list of doctors awaiting approval

POST /api/v1/admin/doctors/{id}/approve
POST /api/v1/admin/doctors/{id}/reject
  Body: { reason }

GET  /api/v1/admin/safety-incidents
  Query: ?from=...&to=...&page=1
  200: conversations flagged_for_review

GET  /api/v1/admin/audit-logs
  Query: ?user_id=...&action=...&from=...&to=...&page=1

GET  /api/v1/admin/audit-verify
  200: { ok: true, last_sequence: N, broken_at?: sequence }
  # Walks the audit hash chain to detect tampering

GET  /api/v1/admin/safety-stats
  Query: ?from=...&to=...
  200: {
    hallucination_rate, citation_rate, uncertainty_distribution,
    triage_inconsistencies, forbidden_phrase_rewrites
  }
```

### 6.7 Support endpoints

```
GET  /api/v1/support/faq                       # list of FAQ items (cached, public)
POST /api/v1/support/contact                   # submit contact form
  Body: { email, subject, message }            # email required; user_id auto-attached if logged in
  201: { ticket_id }
```

### 6.8 Health / meta / observability

```
GET /api/v1/health                             # liveness
GET /api/v1/health/ready                       # readiness (checks DB, vector store)
GET /api/v1/version                            # build SHA, version
GET /metrics                                   # Prometheus exposition format
                                                # (no auth, internal scrape only;
                                                #  bind to 0.0.0.0 only inside private network)
```

### 6.9 OpenAPI

FastAPI auto-generates OpenAPI 3 docs at `/api/v1/openapi.json` and Swagger UI at `/docs` (disabled in production).

---

## 7. Frontend design

### 7.1 Page tree (App Router)

```
app/
├── layout.tsx                  # Root: html lang, dir, theme provider, query client
├── page.tsx                    # Landing page (marketing-light, language-aware)
├── (auth)/
│   ├── login/page.tsx
│   ├── register/page.tsx
│   ├── verify-email/page.tsx
│   ├── forgot-password/page.tsx
│   └── reset-password/page.tsx
├── (app)/
│   ├── layout.tsx              # Authenticated shell: sidebar, header, toaster
│   ├── chat/
│   │   ├── page.tsx            # New chat
│   │   └── [id]/page.tsx       # Existing chat
│   ├── history/page.tsx        # Conversation list
│   ├── handoff/[id]/page.tsx   # View handoff summary
│   ├── profile/page.tsx
│   └── settings/page.tsx
├── doctor/
│   ├── inbox/page.tsx
│   └── handoff/[id]/page.tsx
├── admin/
│   ├── dashboard/page.tsx
│   ├── users/page.tsx
│   ├── doctors-pending/page.tsx
│   ├── safety/page.tsx
│   └── audit/page.tsx
├── support/
│   ├── faq/page.tsx
│   └── contact/page.tsx
└── api/auth/[...]/route.ts     # Next.js route handlers (proxy to backend if needed)
```

### 7.2 Component organization

```
components/
├── ui/                         # shadcn-generated primitives (button, card, input, ...)
├── layout/
│   ├── AppShell.tsx
│   ├── Sidebar.tsx
│   ├── Header.tsx
│   └── LanguageSwitcher.tsx
├── auth/
│   ├── LoginForm.tsx
│   ├── RegisterForm.tsx
│   └── PasswordStrengthMeter.tsx
├── chat/
│   ├── ChatInterface.tsx       # Main chat container
│   ├── MessageList.tsx
│   ├── MessageBubble.tsx
│   ├── ChatComposer.tsx
│   ├── TypingIndicator.tsx
│   ├── CitationCard.tsx
│   ├── TriagePanel.tsx
│   └── ToolCallBadge.tsx
├── handoff/
│   ├── HandoffSummary.tsx
│   ├── HandoffPDFPreview.tsx
│   └── SendToDoctorDialog.tsx
├── doctor/
│   └── HandoffInboxItem.tsx
├── admin/
│   ├── StatsCard.tsx
│   ├── UserTable.tsx
│   └── AuditLogTable.tsx
└── common/
    ├── DataTable.tsx
    ├── Pagination.tsx
    ├── EmptyState.tsx
    ├── ErrorBoundary.tsx
    ├── LoadingSpinner.tsx
    └── ConfirmDialog.tsx
```

### 7.3 State management strategy

| State kind | Tool | Example |
|---|---|---|
| Server state | TanStack Query | `useQuery(['conversations'], ...)`, conversations list, user profile |
| Auth state | Zustand store | Access token, current user, role |
| UI state | Zustand store | Sidebar collapsed, theme, language |
| Form state | react-hook-form | All forms |
| URL state | searchParams | Filters, pagination |

### 7.4 i18n & RTL

- `next-intl` for translations.
- Locale files: `locales/ar.json`, `locales/en.json`.
- `<html lang>` and `dir` set in root layout based on locale.
- Tailwind `rtl:` and `ltr:` variants for direction-specific styles.
- All shadcn components are RTL-safe by default.

### 7.5 Design system — Glassmorphic + Liquid Glass

**Inspiration:** modern medical UI conventions — calm, trust-evoking, low-cognitive-load. Glassmorphism with subtle motion communicates "AI-assisted" without being distracting.

**Color tokens (light mode default; dark mode mirror):**

```css
@theme {
  --color-base:                    #f6faff;  /* page background */
  --color-surface:                 #ffffff;  /* solid card */
  --color-surface-container-lowest: rgba(255, 255, 255, 0.8);
  --color-surface-container-low:   #ebf5ff;
  --color-surface-container:       #e1f0fe;

  --color-primary:                 #005bc0;  /* trust blue */
  --color-primary-dim:             #004fa9;
  --color-primary-container:       #d8e2ff;
  --color-on-primary:              #f7f7ff;

  --color-on-surface:              #1e3544;
  --color-on-surface-variant:      #4b6273;
  --color-outline-variant:         #9eb5c8;

  /* Semantic (triage + safety) */
  --color-emergency:               #d92d20;  /* red */
  --color-urgent:                  #f79009;  /* amber */
  --color-routine:                 #12b76a;  /* green */
  --color-info:                    #2e90fa;

  /* Liquid glass shadows */
  --shadow-liquid-glass:           0 40px 80px rgba(0, 91, 192, 0.15);
  --shadow-liquid-hover:           0 50px 100px rgba(0, 91, 192, 0.25);
  --shadow-liquid-glow:            0 0 20px rgba(0, 91, 192, 0.20);
}
```

**Glass utilities** (Tailwind plugin or custom CSS layer):

```ts
// frontend/lib/theme.ts
export const glass = {
  light: 'bg-white/40 backdrop-blur-3xl border border-white/60 shadow-[var(--shadow-liquid-glass)]',
  heavy: 'bg-white/80 backdrop-blur-3xl border border-white/60',
  dark:  'bg-slate-900/40 backdrop-blur-3xl border border-white/10 shadow-2xl',
};
```

**Typography:**
- Display / headings: **Manrope** (rounded, modern)
- Body: **Inter** (English), **Cairo** (Arabic) — selected via locale at root layout
- Numeric (vitals, scores): tabular-nums

**Motion library** at `frontend/lib/motion.ts` (Framer Motion variants):
- `springSmooth` — `{ type: 'spring', damping: 25, stiffness: 400 }` for default UI transitions
- `bounce` — `{ type: 'spring', damping: 15, stiffness: 300 }` for badges and chips
- `fadeUp` — entrance animation for cards (opacity 0→1, y 12→0, duration 0.3s)
- `pulseUrgent` — subtle red pulse on emergency triage (max 3 cycles, then static, never seizure-inducing)

**Border radii:**
- Cards: `rounded-[2.5rem]` (40px)
- Inputs: `rounded-[1.5rem]` (24px)
- Buttons: `rounded-2xl` (16px)
- Badges: `rounded-full`

**Dark mode** via `next-themes`: every glass utility has a dark counterpart; semantic colors keep WCAG AA contrast in both modes.

**Reduced motion:** respect `prefers-reduced-motion`; fall back to opacity transitions only.

### 7.6 Accessibility checklist (every component must pass)

- [ ] Keyboard navigable
- [ ] Focus indicators visible
- [ ] Color contrast ≥ WCAG AA
- [ ] Screen-reader labels (`aria-label`, `aria-describedby`)
- [ ] No keyboard traps
- [ ] Forms have associated labels
- [ ] Error messages programmatically linked
- [ ] Live regions for dynamic content (chat streaming)

---

## 8. AI / ML design

### 8.1 Agent loop (ReAct-style)

```
function answer(user_message, conversation_history):
    # 1. Pre-flight checks
    language = detect_language(user_message)
    user_message = arabic_normalize(user_message) if language == 'ar' else user_message
    user_message = pii_scrub(user_message)
    
    # 2. Red-flag fast path (overrides agent)
    red_flags = detect_red_flags(user_message)
    if red_flags.is_emergency:
        return emergency_response(red_flags, language)
    
    # 3. Build prompt
    system_prompt = load_prompt('system', language)
    tool_specs = registry.list_tools()
    messages = build_messages(system_prompt, conversation_history, user_message, tool_specs)
    
    # 4. Agent loop (max N=5 iterations)
    for iteration in range(MAX_ITERATIONS):
        response = llm.generate(messages, tools=tool_specs, stream=True)
        if response.is_final:
            return finalize(response, language)
        # response is a tool call
        tool_result = registry.run(response.tool_name, response.tool_input)
        messages.append(assistant_message_with_tool_call(response))
        messages.append(tool_message(tool_result))
    
    # 5. Force-finish if max iterations reached
    return ask_for_clarification(language)
```

### 8.2 Tools — all implement the `Tool` ABC

The agent has two tiers of tools. Core tools (Phase 2) ship with the MVP; specialized tools (Phase 2.5) extend clinical reach.

#### 8.2.1 Core MVP tools (Phase 2)

| Tool | Input | Output | Purpose |
|---|---|---|---|
| `retrieve_medical_knowledge` | `query: str, language: str, top_k: int=5` | `list[KBChunk]` | RAG over knowledge base |
| `score_triage` | `symptoms: list[str], age: int?, comorbidities: list[str]?` | `{level: emergency\|urgent\|routine, score: int, reasoning: str}` | Manchester Triage Scale |
| `detect_red_flags` | `text: str, language: str` | `{has_red_flag: bool, flags: list[str], severity: str}` | Emergency keyword + pattern detection |
| `summarize_for_doctor` | `conversation_id: UUID` | `{summary_markdown: str}` | Generate handoff summary |
| `analyze_vision` | `image_b64: str, kind: 'xray'\|'ct'\|'photo'\|'skin', context: str` | `{findings: list[str], urgency: str, confidence: float, disclaimer: str}` | Preliminary image triage (NOT radiology) |

#### 8.2.2 Specialized clinical tools (Phase 2.5)

| Tool | Input | Output | Purpose |
|---|---|---|---|
| `check_medication_interactions` | `meds: list[{name, dose}], allergies: list[str], conditions: list[str]` | `{interactions: [...], allergy_conflicts: [...], dose_warnings: [...]}` | Drug-drug + allergy + dose safety |
| `screen_mental_health` | `responses: dict, scale: 'phq9'\|'gad7'` | `{score: int, severity: str, recommendation: str}` | PHQ-9 / GAD-7 standardized screening |
| `assess_pediatric_safety` | `age_months: int, weight_kg: float?, symptoms: list, meds: list` | `{age_appropriate: bool, dose_warnings: [...], red_flags: [...]}` | Age-aware safety gate (used when patient is < 18) |
| `assess_pregnancy_safety` | `gestational_week: int?, symptoms: list, meds: list` | `{ob_red_flags: [...], category_warnings: [...]}` | OB-aware safety (used when pregnancy declared) |
| `format_soap_note` | `conversation_id: UUID` | `{markdown: str}` | Clinician-style S/O/A/P note from conversation |
| `tot_differential_diagnosis` | `symptoms: list, history: dict` | `{branches: [{hypothesis, probability, reasoning_steps, supporting_citations}]}` | Multi-branch reasoning (Tree-of-Thought) |
| `verify_no_hallucination` | `assistant_message: str, retrieved_sources: list` | `{hallucination_score: float, unsupported_claims: list, suggested_rewrites: list}` | Post-LLM fact-check |
| `calibrate_uncertainty` | `assistant_message: str, retrieved_sources: list` | `{claims: [{text, confidence, band: 'high'\|'medium'\|'low'}]}` | Confidence band per clinical claim |

Each specialized tool has its own §13 task (T2.13–T2.16, T2.5.01–T2.5.04).

### 8.3 Safety pipeline (multi-stage)

Safety is a **layered pipeline**, not a single check. Each stage has clear responsibilities, can be unit-tested in isolation, and writes structured records to `safety_assessments` so we can audit any decision later.

#### Stage 1 — Pre-LLM (input)
- **Language detection** (auto AR/EN; preserves code-switched text).
- **Arabic normalization** (alef forms, taa marbuta, diacritics).
- **PII scrub** (best-effort: names, phone numbers, national IDs, emails).
- **Red-flag fast path** (`detect_red_flags`): if emergency keyword/pattern matches in AR or EN, **bypass the LLM** entirely and return a hardcoded, localized emergency response with the local emergency number (Egypt: 123).

#### Stage 2 — In-LLM (generation)
System prompt enforces:
- Never give a definitive diagnosis (use "this is consistent with..." / "could indicate...").
- Never prescribe medications or specific doses.
- Always cite retrieved sources for clinical claims (inline `[source:N]` tags).
- Always include a "consult a licensed physician" disclaimer.
- If uncertain, say so explicitly and recommend professional evaluation.
- Switch to **pediatric safety branch** when patient profile indicates age < 18.
- Switch to **pregnancy safety branch** when patient profile indicates pregnancy.

#### Stage 3 — Post-LLM (verification, before response is sent)
Runs in parallel where possible; results stored in `safety_assessments`:
- **Hallucination detector** (`verify_no_hallucination`) — a smaller verification LLM compares each clinical claim against retrieved sources. If `hallucination_score > threshold`, the assistant message is rewritten with explicit uncertainty markers OR the unsupported claim is removed.
- **Uncertainty calibrator** (`calibrate_uncertainty`) — assigns each claim a confidence band (high/medium/low). Low-confidence claims get a UI badge ("⚠ low confidence").
- **Citation completeness check** — every clinical assertion must have a citation or be rewritten as uncertainty.
- **Forbidden-phrase rewriter** — prescriptive language ("you should take 500 mg...") triggers a rewrite to advisory language.
- **Triage consistency** — final recommended action must match the `score_triage` tool output (or be more conservative).

#### Stage 4 — Audit chain
- Every state-changing operation writes a hash-chained row to `audit_logs` (see §9.7).
- Safety overrides (red-flag fast path, hallucination rewrites) include their own audit entries with `details.safety_event_kind`.

#### Failure modes & fallbacks
- If verification LLM is unavailable: **fail closed** — surface the message with a "verification unavailable" badge and conservative triage.
- If retrieval returns 0 chunks for a clinical claim: **decline to assert** — rephrase as "I cannot verify this against my sources; please consult a clinician."

### 8.4 RAG pipeline

```
Query → embed (multilingual-e5-large) → FAISS/pgvector top-k=20
      → cross-encoder rerank (bge-reranker-v2-m3) → top-k=5
      → format as context → into LLM prompt
```

Chunking: 256-token chunks with 64-token overlap, semantic boundaries (sentence splitter via spaCy/syntok).

### 8.5 Knowledge base sources (initial)

| Source | License | Size estimate | Languages |
|---|---|---|---|
| WHO clinical guidelines (public) | CC BY-NC-SA | ~500 docs | EN (we translate select Arabic versions) |
| MedlinePlus consumer health | Public domain | ~1000 articles | EN, ES (we translate to AR) |
| Egyptian Ministry of Health public health pages | Government public | ~50 pages | AR |
| PubMed abstracts (curated subset for triage-relevant conditions) | Public | ~5000 abstracts | EN |

### 8.6 Fine-tuning plan (Phase 3)

**Objective:** Improve triage accuracy and bilingual fluency over the base model.

**Method:** QLoRA on Qwen2.5-7B-Instruct.

**Datasets:**
- MedDialog (English split): ~50K conversation turns
- HealthCareMagic-100k: sample 30K
- Translated MedDialog (NLLB-200) → Arabic: 10K turns
- Manually curated Arabic medical Q&A: 2K turns
- Synthetic data generated by the base model on triage scenarios, filtered manually: 5K examples

**Hyperparameters (starting point):**
- LoRA rank: 16, alpha: 32, dropout: 0.05
- Target modules: q_proj, k_proj, v_proj, o_proj
- Batch size: 4 (gradient accumulation 8 = effective 32)
- Learning rate: 2e-4 with cosine schedule, 3% warmup
- Epochs: 3
- Quantization: 4-bit NF4

**Expected training time:** ~10-14h on Colab T4.

### 8.7 Evaluation suite

| Metric | What it measures | Target |
|---|---|---|
| BLEU-4 | Surface n-gram overlap with reference responses | > base model |
| ROUGE-L | Longest common subsequence | > base model |
| BERTScore (F1) | Semantic similarity | > base model |
| Triage accuracy | % correct triage level on 200-case gold set | ≥ 80% |
| Triage macro-F1 | Class-balanced triage performance | ≥ 0.75 |
| Hallucination rate | % responses with unsupported clinical claims (manual review of 100) | ≤ 5% |
| Red-flag recall | % emergency cases correctly escalated | ≥ 95% |
| Citation rate | % responses with at least one cited source | ≥ 90% |
| Refusal appropriateness | % refusals on out-of-scope queries (manual review of 50) | ≥ 90% |

### 8.8 Reasoning modes

Two reasoning modes coexist in the agent. The supervisor decides which to run based on the conversation state.

#### 8.8.1 Default mode — ReAct loop (§8.1)
- One linear chain of thought.
- Used for routine triage, follow-up questions, simple clarifications.
- Bounded by `MAX_ITERATIONS=5`.
- Lower latency, lower cost.

#### 8.8.2 Tree-of-Thought (ToT) mode — for differential diagnosis
Triggered when **ALL** of these are true:
1. Triage level is `urgent` (not emergency — emergency uses fast path).
2. The agent's confidence in its top differential is < 0.7.
3. There is at least one symptom cluster supporting ≥ 2 distinct hypotheses.

Mechanism (`tot_differential_diagnosis` tool):
1. **Branch generation** — generate 3 candidate hypotheses with brief reasoning.
2. **Branch scoring** — for each branch, retrieve top-3 supporting chunks and score (LLM-as-judge) on coherence + evidence support.
3. **Pruning** — keep top 2 branches.
4. **Surfacing** — present both branches in the UI as a "differential" panel with confidence bars; recommend the one with the safer next-action.

Bounded by `MAX_TOT_BRANCHES=3` and `MAX_TOT_DEPTH=2`. Falls back to ReAct mode if any branch fails to retrieve supporting evidence.

#### 8.8.3 Mode selection rule
```
if red_flags.is_emergency:        return EMERGENCY_FAST_PATH
elif triage == 'urgent' and confidence < 0.7:  return TOT_MODE
else:                              return REACT_MODE
```

---

## 9. Security model

### 9.1 Authentication

- **Access token:** JWT, RS256-signed, 15-min expiry, contains `sub` (user_id), `role`, `iat`, `exp`.
- **Refresh token:** opaque random string (256 bits), hashed (SHA-256) before DB storage, 7-day expiry, single-use (rotated on every refresh).
- **Storage on client:** access token in memory (Zustand), refresh token in HTTP-only secure same-site cookie.
- **Password hashing:** bcrypt cost factor 12.
- **Token revocation:** `refresh_tokens.revoked_at` set on logout / password change / role change. Access tokens are short-lived; no blacklist needed.

### 9.2 Authorization (RBAC)

- Three roles: `patient`, `doctor`, `admin`.
- Permission matrix encoded in `core/deps.py` via `require_role(*roles)` dependency.
- Resource-level checks in service layer (e.g., a patient can only fetch their own conversations).

### 9.3 Threat model & mitigations

| Threat | Mitigation |
|---|---|
| SQL injection | SQLAlchemy parameterized queries everywhere; no raw SQL with user input |
| XSS | React auto-escapes; we sanitize Markdown rendering with DOMPurify |
| CSRF | We use Bearer tokens, not session cookies, for the API; the only cookie is HTTP-only refresh token; same-site=strict |
| Brute force login | Rate limit 5/min/IP; account lockout after 10 failed attempts (15-min lockout) |
| User enumeration | `/auth/forgot-password` always returns 200; login error is generic |
| Session hijack | HTTPS only; HSTS; HTTP-only cookies; refresh rotation |
| Privilege escalation | Role checked in middleware AND service layer (defense in depth) |
| PII leakage | PII scrubbed from training data; conversations not used in training without consent; logs scrubbed |
| Prompt injection | Tool inputs validated; system prompt isolated; no raw user input in tool args |
| LLM hallucinations on medical advice | Citation enforcement, red-flag override, mandatory disclaimers, evaluation suite |
| Dependency vulnerabilities | `pip-audit` + `npm audit` in CI; Dependabot |

### 9.4 Data protection

- **In transit:** HTTPS/TLS 1.3 enforced via HSTS. No plaintext HTTP.
- **At rest:** Postgres encryption at rest (provider-managed). Sensitive columns (e.g., refresh token hashes) are SHA-256 hashed.
- **Backups:** Provider-managed daily backups; manual tested restore quarterly.
- **Retention:** Soft-deleted users hard-deleted after 90 days; conversations retained while account active.
- **PII export/delete:** GDPR-style: `/users/me` DELETE soft-deletes + queues anonymization.

### 9.5 Security headers (set by middleware)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: default-src 'self'; img-src 'self' data:; ...
```

### 9.6 PHI field encryption (application-level)

In addition to provider-managed encryption-at-rest (Postgres), we encrypt **sensitive PHI columns** at the application layer using **Fernet (AES-128-CBC + HMAC-SHA256)** before they ever hit the DB. This means a DB-only breach (e.g., stolen backup) does NOT expose PHI plaintext.

**Encrypted fields:**

| Table | Column | Reason |
|---|---|---|
| `messages` | `encrypted_content` (BYTEA) | Patient narrative — high sensitivity |
| `patient_profiles` | `allergies`, `chronic_conditions`, `current_medications` (JSONB → encrypted blob) | Health history |
| `vision_analyses` | `encrypted_analysis` (BYTEA) | Image findings |
| `handoff_summaries` | `summary_markdown` (TEXT → encrypted) | Aggregated PHI |

**Key management:**
- Single key sourced from `DATA_ENCRYPTION_KEY` env (44-byte URL-safe base64; `cryptography.fernet.Fernet.generate_key()` to bootstrap).
- **Startup check:** if `ENV=production` and `DATA_ENCRYPTION_KEY` is missing → fail-fast with non-zero exit.
- **Rotation playbook** at `docs/runbooks/key_rotation.md`: dual-key window (old + new), batch re-encrypt, retire old.

**Toggle:** `PHI_ENCRYPTION_ENABLED` env (default `true` in prod, `false` in `local` for debugging).
- When `false`, the `content` column (TEXT) is used directly.
- When `true`, `encrypted_content` (BYTEA) is the source of truth and `content` is `NULL`.
- The `(content IS NOT NULL OR encrypted_content IS NOT NULL)` CHECK constraint enforces consistency.

**Implementation:**
- `backend/app/core/encryption.py` — `encrypt_phi(plaintext) -> bytes` and `decrypt_phi(ciphertext) -> str`.
- SQLAlchemy `TypeDecorator` to transparently encrypt/decrypt at the ORM layer for `EncryptedString` and `EncryptedJSON` types.
- Repository layer reads the right column based on `PHI_ENCRYPTION_ENABLED`.
- All key-rotation operations are audit-logged.

### 9.7 Audit hash chaining (tamper-evident)

Every row in `audit_logs` is cryptographically chained to the previous row, making after-the-fact tampering detectable.

**Chain construction:**
```python
genesis_hash = sha256("MEDAGENT_AUDIT_GENESIS_V1").hexdigest()

# For each new audit row N:
canonical = canonical_json({
    "sequence": N.sequence,
    "user_id": N.user_id,
    "action": N.action,
    "resource_type": N.resource_type,
    "resource_id": N.resource_id,
    "details": N.details,
    "ip_address": N.ip_address,
    "user_agent": N.user_agent,
    "created_at": N.created_at.isoformat(),
})
N.previous_hash = (sequence-1).current_hash  # or genesis if N is first
N.current_hash = sha256(N.previous_hash + canonical).hexdigest()
```

**Properties:**
- Inserts only use a SERIALIZABLE-isolation transaction to prevent race conditions on `previous_hash` lookup.
- `audit_logs` is **append-only** at the application layer (no UPDATE/DELETE issued). DB-level enforcement: separate role with INSERT-only grant.
- A scheduled job (`scripts/audit_verify.py`, runs nightly + on-demand via `/admin/audit-verify`) walks the chain and reports the first sequence at which the chain breaks.
- WORM-compatible: backups can be exported to immutable storage (S3 Object Lock / similar) for long-term tamper-evidence.

**Limits:**
- This is **detection, not prevention** — a privileged attacker with DB write access could rewrite the entire chain. Detection still works because the chain hash on a replicated audit store (e.g., a write-only S3 bucket) won't match.
- For genuine tamper-resistance, ship hashes off-box on a schedule.

---

## 10. Testing strategy

### 10.1 Levels

| Level | Tool | Scope | Coverage target |
|---|---|---|---|
| Unit | pytest | Pure functions, services with mocked deps | ≥ 80% |
| Integration | pytest + httpx async client | API endpoints with real test DB | All endpoints, golden paths + key error paths |
| Component | Vitest + React Testing Library | UI components in isolation | All complex components |
| E2E | Playwright | Critical user flows in browser | Auth flow, chat flow, handoff flow, admin flow |
| AI eval | Custom harness | Triage accuracy, hallucination, safety | Run on every model release |
| Smoke | Custom | 20-case sanity set in CI | Run on every PR |
| Load | k6 (optional, late) | API under load | Chat endpoint at 50 RPS |

### 10.2 Test data strategy

- Backend: pytest fixtures spin up a PostgreSQL test DB (via testcontainers or a local Docker), run migrations, seed minimal data, roll back per-test transactions.
- Frontend: MSW (Mock Service Worker) for API mocking in component tests.
- AI: a fixed `tests/eval/golden_cases.jsonl` file with manually verified expected behaviors.

### 10.3 CI integration

`.github/workflows/ci.yml` runs on every PR:
1. Backend: ruff, mypy, pytest with coverage, smoke eval
2. Frontend: eslint, type-check, vitest, playwright (smoke set)
3. Combined: docker build, docker-compose up + healthcheck

`.github/workflows/deploy.yml` runs on merge to main:
1. Build and push Docker images
2. Deploy backend to Railway/Render
3. Deploy frontend to Vercel
4. Run post-deploy smoke against staging
5. If staging green, promote to prod

---

## 11. Deployment & operations

### 11.1 Environments

| Env | Purpose | Hosting |
|---|---|---|
| `local` | Developer machine | docker-compose |
| `staging` | Pre-prod testing | Same infra as prod, separate DB |
| `prod` | Live | Vercel + Railway/Render + Neon |

### 11.2 Configuration

All config via env vars. `.env.example` lists every required variable with a brief description and example. `config.py` (Pydantic Settings) validates and types them.

### 11.3 Docker

Multi-stage Dockerfile per app:
1. `deps` stage installs deps with cache
2. `build` stage builds (frontend) or compiles (backend)
3. `runtime` stage is minimal (distroless or python-slim), non-root user, only runtime artifacts

### 11.4 Monitoring & observability (overview)

The full observability stack is documented in §11.6. Summary:

| Concern | Tool |
|---|---|
| Errors | Sentry (free tier) — both frontend and backend |
| Logs | structlog → stdout → provider log aggregator |
| Metrics | Prometheus client → `/metrics` → Grafana Cloud |
| Traces | OpenTelemetry SDK → OTLP exporter → Grafana Tempo |
| Uptime | UptimeRobot (free) hitting `/health/ready` |
| ML metrics | MLflow (Phase 3) — training + inference logging |
| Alerts | Sentry alerts on error rate spike; UptimeRobot on downtime; Grafana alerts on p95 latency or hallucination rate spikes |

### 11.5 Release & rollback

- Every prod deploy is tied to a git SHA (visible in `/api/v1/version`).
- DB migrations: forward-only; never auto-rollback. Keep migrations small and additive when possible.
- Rollback: redeploy previous image; if migration was destructive, restore from backup (rare).

### 11.6 Observability stack (detail)

#### Metrics — Prometheus
- `prometheus-client` exposes `/metrics` on the backend.
- Default Python metrics + custom medical metrics:
  - `medagent_request_duration_seconds{endpoint, method, status}` (histogram)
  - `medagent_agent_iteration_count{mode}` (counter)
  - `medagent_tool_calls_total{tool, success}` (counter)
  - `medagent_red_flags_detected_total{language, flag}` (counter)
  - `medagent_hallucination_score` (histogram, label: `model_version`)
  - `medagent_uncertainty_band_total{band}` (counter)
  - `medagent_emergency_escalations_total{language}` (counter)
- Scraped by **Grafana Cloud free tier** (Prometheus remote-write).

#### Traces — OpenTelemetry
- `opentelemetry-instrumentation-fastapi` auto-instruments routes.
- Manual spans inside the agent loop: `agent.iteration`, `tool.run.{tool_name}`, `llm.generate`, `safety.verify`.
- Span attributes carry `conversation_id`, `language`, `triage_level`, but **NEVER PHI content** (only IDs).
- OTLP exporter → **Grafana Tempo** (free tier).
- Dev mode: console exporter.

#### Logs — structlog
- JSON to stdout; correlation ID = OTel trace ID.
- Log levels by env:
  - `local`: DEBUG
  - `staging`: INFO
  - `prod`: WARNING (errors → Sentry; INFO sampled to log aggregator)

#### ML metrics — MLflow
- Training runs logged in Phase 3 (T3.04, T3.05).
- **Inference logging** (T3.07 + T4.13 extension): every assistant message logs `{model_version, latency, tokens_in, tokens_out, hallucination_score}` as MLflow metrics.

#### Dashboards & alerts
- Grafana dashboards: API latency, agent iteration distribution, tool success rates, hallucination trend, emergency escalations.
- Alerts:
  - p95 latency > 3s for 5 min → Slack webhook
  - Hallucination score p95 > 0.3 for 30 min → Slack + Sentry issue
  - Red-flag escalations spike > 3× baseline → admin email

### 11.7 Interoperability — FHIR + HL7

A doctor handoff can be exported in **two interop formats** beyond the human-readable PDF, so a clinician can ingest it into an EHR or share it across systems.

#### FHIR R4 Bundle (preferred)
- Built using `fhir.resources` Pydantic models.
- Bundle type: `document`.
- Contains:
  - `Patient` (from patient profile, age + gender; no name/phone unless explicitly opted in)
  - `Condition` resources for each differential diagnosis
  - `Observation` for symptoms, vital signs (when collected)
  - `MedicationStatement` for current meds
  - `AllergyIntolerance` for known allergies
  - `ClinicalImpression` for the AI-generated summary, with citations as `evidence.detail` references
  - `Composition` as the bundle's first entry, linking everything
- Validates against the **HAPI FHIR public validator** (test in CI).

#### HL7 v2.5 message
- ADT^A04 (register a patient) + OBX segments for findings.
- Used for legacy systems that haven't adopted FHIR.
- Built with the `hl7` library.

#### Endpoint
- `GET /api/v1/handoffs/{id}/export?format=fhir|hl7` returns the appropriate content-type and inserts a row into `handoff_exports`.
- The frontend handoff page exposes "Download as FHIR" / "Download as HL7" buttons next to "Download PDF".

---

## 12. Data strategy

### 12.1 Datasets (training & evaluation)

See §8.6.

### 12.2 Knowledge base curation

- All sources tracked in `docs/data_card.md` with: name, license, URL, retrieval method, last refresh date.
- Re-embedding pipeline (Phase 3 task) re-builds the vector store from source files.
- Sources are stored under `data/knowledge_base/raw/` (gitignored, downloaded by `scripts/download_kb.py`).

### 12.3 Privacy

- Patient conversations are private to the patient by default.
- Conversations are NEVER used for training without explicit, separate consent (a future opt-in checkbox; not in MVP).
- PII scrub runs on all stored messages (best-effort: names, phone numbers, emails) — but messages are only readable by the conversation owner regardless.

### 12.4 Ethics

- Bias review: evaluate model performance across demographics (age groups, genders) on the eval set; document gaps in the final report.
- Fairness: do not differentiate triage recommendations by gender for symptom-only cases (heart attack symptoms differ; we document this nuance).
- Transparency: every clinical claim cites a source; we publish the eval results, including failure cases.

---

## 13. Phases & tasks

Tasks have IDs `T<phase>.<seq>` (e.g., `T1.04`). Each task lists:
- **Goal:** the outcome
- **Depends on:** prior task IDs
- **Files:** files created/modified
- **References:** which design sections to read
- **Acceptance criteria:** the exact bar for "done"
- **Verification:** how to confirm

A task is **not complete** until all acceptance criteria are demonstrably met. Mark complete in `docs/tasks/STATUS.md` only after verification.

### Phase 1 — Foundation (production-grade infra & auth)

**Goal:** A deployable shell — auth, DB, basic API, basic frontend, CI, all production-grade. No AI yet. By the end of Phase 1, a user can sign up, verify email, log in, view their (empty) profile, and sign out — and the entire system is tested, dockerized, and deployable.

#### T1.01 — Repo scaffolding & monorepo layout
- **Goal:** Clean monorepo structure with `backend/`, `frontend/`, `docs/`, `notebooks/`, `scripts/`, `data/`, `.github/`, root tooling configs.
- **Depends on:** none
- **Files:** `README.md`, `.gitignore`, `.editorconfig`, `LICENSE`, `pnpm-workspace.yaml`, root `pyproject.toml` (for tooling like ruff), root scripts in `package.json` (lint-all, test-all).
- **References:** §4.3, §4.4
- **Acceptance criteria:**
  - [ ] Directory structure matches §4.3
  - [ ] README has: project description, status, prerequisites, quick start, links to docs
  - [ ] `.gitignore` covers Python, Node, IDE, OS, `.env`, `data/`, `__pycache__`, `node_modules`, `.next`, `dist`, `*.log`
  - [ ] EditorConfig set (utf-8, lf, 4-space Python, 2-space JS/TS, trim trailing whitespace)
  - [ ] License file (MIT or chosen)
  - [ ] `git init` done, first commit pushed to GitHub
- **Verification:** `tree -L 2` matches; `git log` shows initial commit; repo URL accessible.

#### T1.02 — Backend project skeleton (FastAPI)
- **Goal:** Runnable FastAPI app with health endpoints, config, logging, exception handlers.
- **Depends on:** T1.01
- **Files:** `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/core/{config,database,security,deps,exceptions,middleware,logging}.py`, `backend/app/common/`, `backend/.env.example`, `backend/Dockerfile`, `backend/tests/conftest.py`
- **References:** §3.1, §4.3, §9.5
- **Acceptance criteria:**
  - [ ] `uv sync` (or `pip install -e .`) installs all deps with locked versions
  - [ ] `uvicorn app.main:app --reload` starts without error
  - [ ] `GET /api/v1/health` returns 200 `{"status":"ok"}`
  - [ ] `GET /api/v1/health/ready` returns 200 `{"status":"ready","checks":{"db":"ok"}}`
  - [ ] `GET /api/v1/version` returns build info
  - [ ] `GET /docs` shows Swagger UI in non-prod env
  - [ ] `/docs` is disabled when `ENV=production`
  - [ ] Custom exception handler returns standardized error envelope (§6.1)
  - [ ] Security headers from §9.5 are set on all responses
  - [ ] Logs are JSON-structured (structlog)
  - [ ] CORS configured to allow frontend origin from env
- **Verification:** All endpoints curl-able; coverage ≥ 80% on `core/`.

#### T1.03 — Database setup & initial migration
- **Goal:** PostgreSQL connected via async SQLAlchemy with Alembic migrations and the schema from §5.2.
- **Depends on:** T1.02
- **Files:** `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial.py`, `backend/app/models/*.py` (one file per table), `backend/scripts/seed.py`
- **References:** §5
- **Acceptance criteria:**
  - [ ] All §5.2 tables exist with correct columns, constraints, indexes
  - [ ] `alembic upgrade head` runs idempotently
  - [ ] `alembic downgrade base` removes all tables cleanly
  - [ ] SQLAlchemy models match the SQL exactly (column names, types, FKs)
  - [ ] pgvector extension enabled in migration
  - [ ] Seed script creates: 1 admin, 1 sample patient, 1 sample doctor (approved)
  - [ ] DB unit tests pass (one per model: create/read/update/soft-delete)
- **Verification:** `psql` shows all tables; `alembic upgrade/downgrade` round-trips clean; tests green.

#### T1.04 — Auth: registration & email verification
- **Goal:** Users can register and verify email; doctor accounts go to pending queue.
- **Depends on:** T1.03
- **Files:** `backend/app/modules/auth/{router,service,schemas}.py`, `backend/app/core/email.py`, `backend/templates/email/verify.{html,txt}`, tests in `tests/auth/`
- **References:** §6.2, §9.1
- **Acceptance criteria:**
  - [ ] `POST /auth/register` validates input, creates user, sends verification email, returns 201
  - [ ] Doctor registration also creates `doctor_profiles` with status='pending'
  - [ ] Password is bcrypt-hashed (cost 12); raw password never logged
  - [ ] `auth_tokens` row created with hashed token; expires in 24h
  - [ ] Email contains verification link with token
  - [ ] `POST /auth/verify-email` validates token, marks user verified, marks token used
  - [ ] `POST /auth/resend-verification` rate-limited 1/min/email
  - [ ] Email enumeration prevented on resend (always 200)
  - [ ] Audit log row written for each register/verify
  - [ ] Unit + integration tests for golden path + 5 error cases (duplicate email, weak password, expired token, used token, non-existent token)
- **Verification:** End-to-end register → receive email (SMTP server in dev: `mailpit`) → click link → user verified.

#### T1.05 — Auth: login, refresh, logout, password change
- **Goal:** Complete login lifecycle with JWT + refresh tokens.
- **Depends on:** T1.04
- **Files:** `backend/app/modules/auth/`, `backend/app/core/security.py`, tests
- **References:** §6.2, §9.1, §9.2
- **Acceptance criteria:**
  - [ ] `POST /auth/login` issues access (15m) + refresh (7d) tokens
  - [ ] Login fails with 401 on: wrong password, unverified email, disabled account, doctor pending
  - [ ] Login enforces rate limit 5/min/IP and account lockout after 10 failed attempts
  - [ ] `POST /auth/refresh` validates refresh token, rotates (issues new + revokes old), returns new pair
  - [ ] Replay of old refresh token returns 401 and revokes ALL user's refresh tokens (token theft signal)
  - [ ] `POST /auth/logout` revokes the provided refresh token
  - [ ] `POST /auth/change-password` requires current password; revokes all other refresh tokens on success
  - [ ] All auth events audit-logged with IP + user agent
  - [ ] Tests: golden + 6 error paths
- **Verification:** Full login → access protected endpoint → refresh → access → logout → access fails.

#### T1.06 — Auth: forgot/reset password
- **Goal:** Self-service password reset via email.
- **Depends on:** T1.05
- **Files:** `backend/app/modules/auth/`, email templates, tests
- **References:** §6.2, §9.3 (user enumeration)
- **Acceptance criteria:**
  - [ ] `POST /auth/forgot-password` always returns 200 (no enumeration)
  - [ ] If email exists, sends reset email with token; token valid 1h
  - [ ] `POST /auth/reset-password` validates token, sets new password, marks token used, revokes all refresh tokens
  - [ ] Tests including: valid reset, expired token, used token, weak new password
- **Verification:** Forgot → email received → reset → login with new password.

#### T1.07 — User profile endpoints
- **Goal:** Authenticated users can view and update their profile.
- **Depends on:** T1.05
- **Files:** `backend/app/modules/users/`, tests
- **References:** §6.3
- **Acceptance criteria:**
  - [ ] `GET /users/me` returns user + role-specific profile (patient or doctor)
  - [ ] `PUT /users/me` updates name, phone, locale, avatar; validates input
  - [ ] `PATCH /users/me/profile` updates patient or doctor profile (role-aware)
  - [ ] `DELETE /users/me` soft-deletes + queues anonymization job
  - [ ] All operations audit-logged
- **Verification:** Sign in → fetch profile → update → fetch shows updates.

#### T1.08 — Frontend project skeleton (Next.js 14)
- **Goal:** Next.js app initialized with App Router, TypeScript strict, Tailwind, shadcn/ui base, i18n, theme provider.
- **Depends on:** T1.01
- **Files:** `frontend/package.json`, `frontend/tsconfig.json`, `frontend/next.config.js`, `frontend/tailwind.config.ts`, `frontend/app/layout.tsx`, `frontend/app/page.tsx`, `frontend/components/ui/*` (initial shadcn components), `frontend/lib/utils.ts`, `frontend/.env.local.example`
- **References:** §3.2, §7
- **Acceptance criteria:**
  - [ ] `pnpm dev` runs Next.js on port 3000
  - [ ] TypeScript strict mode on
  - [ ] Tailwind configured with custom theme tokens (§7.5)
  - [ ] shadcn/ui initialized; at least Button, Input, Card components generated
  - [ ] next-intl set up with `ar` and `en` locales; `<html lang>` and `dir` set dynamically
  - [ ] Dark mode toggle works
  - [ ] Cairo font loaded for Arabic, Inter for English
  - [ ] Landing page renders cleanly in both languages with RTL/LTR correct
  - [ ] eslint + prettier configured; `pnpm lint` and `pnpm format` work
- **Verification:** Visit `/`, switch language to AR → page flips to RTL with Arabic text and Cairo font.

#### T1.09 — Frontend auth pages
- **Goal:** Login, register, verify-email, forgot/reset password pages, all integrated with backend.
- **Depends on:** T1.08, T1.05, T1.06
- **Files:** `frontend/app/(auth)/**`, `frontend/components/auth/**`, `frontend/lib/api/auth.ts`, `frontend/store/auth.ts`, `frontend/hooks/useAuth.ts`
- **References:** §6.2, §7
- **Acceptance criteria:**
  - [ ] Login form (email + password) with react-hook-form + zod validation
  - [ ] Register form (with role selector; doctor extras shown conditionally)
  - [ ] Password strength meter on register
  - [ ] Verify email page handles `?token=...` and calls API
  - [ ] Forgot password & reset password pages
  - [ ] Auth store (Zustand) holds access token in memory; refresh token in HTTP-only cookie via Next.js route handler
  - [ ] On 401 from API, axios/fetch interceptor attempts refresh once, retries; on second 401, signs user out
  - [ ] Loading, error, success states for every form
  - [ ] All forms keyboard-accessible
  - [ ] All forms localized (AR/EN)
- **Verification:** Full flow: register → email link → verify → login → see dashboard placeholder → logout.

#### T1.10 — Frontend authenticated shell + protected routes
- **Goal:** App layout (sidebar, header, language switcher, theme toggle), role-aware navigation, route guards.
- **Depends on:** T1.09
- **Files:** `frontend/app/(app)/layout.tsx`, `frontend/components/layout/**`, `frontend/lib/auth/protect.ts`, `frontend/middleware.ts`
- **References:** §7
- **Acceptance criteria:**
  - [ ] `(app)` route group is protected — unauthenticated users redirect to `/login?redirect=...`
  - [ ] Sidebar nav items differ by role (patient/doctor/admin)
  - [ ] Header shows user avatar + dropdown (profile, settings, logout)
  - [ ] Language switcher persists across navigation
  - [ ] Theme toggle persists in localStorage
  - [ ] Mobile-responsive (sidebar collapses to drawer < 768px)
- **Verification:** Logged-out user visiting `/chat` → redirected to login. After login → redirected back. Switch role accounts → see different sidebar items.

#### T1.11 — Audit log infrastructure
- **Goal:** Every state-changing endpoint writes an audit log row.
- **Depends on:** T1.07
- **Files:** `backend/app/common/audit.py`, integration into existing endpoints
- **References:** §5.2 (`audit_logs`), §9
- **Acceptance criteria:**
  - [ ] `audit_log(action, resource_type, resource_id, details)` helper used in every state-changing service
  - [ ] All auth events (register, verify, login, logout, password change/reset) logged
  - [ ] All profile updates logged
  - [ ] Audit writes are non-blocking (BackgroundTasks) — never fail the main request
  - [ ] Unit tests for audit helper
- **Verification:** Run a flow → query `audit_logs` table → see expected rows.

#### T1.12 — Rate limiting
- **Goal:** Per-IP and per-user rate limits enforced on relevant endpoints.
- **Depends on:** T1.05
- **Files:** `backend/app/core/middleware.py`, `backend/app/core/deps.py`, Redis client setup
- **References:** §6 (limits per group), §9.3
- **Acceptance criteria:**
  - [ ] Redis client connects (env-driven)
  - [ ] Auth endpoints rate-limited 5/min/IP
  - [ ] Resend-verification rate-limited 1/min/email
  - [ ] User endpoints 60/min/user
  - [ ] Hitting limit returns 429 with `Retry-After` header and standardized error envelope
  - [ ] Tests verify limit enforcement
- **Verification:** Hit `/auth/login` 6 times in a minute → 6th returns 429.

#### T1.13 — docker-compose for local dev
- **Goal:** `docker-compose up` brings up the full stack locally.
- **Depends on:** T1.02, T1.03, T1.08
- **Files:** `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore`
- **References:** §11.3
- **Acceptance criteria:**
  - [ ] Services: `postgres`, `redis`, `mailpit` (dev SMTP), `backend`, `frontend`
  - [ ] All services health-check; `backend` waits for `postgres` ready
  - [ ] Volumes for postgres data persistence
  - [ ] `.env` injected
  - [ ] Frontend hot-reloads; backend hot-reloads
  - [ ] Single `make dev` target to start everything
- **Verification:** Fresh clone → `cp .env.example .env` → `docker-compose up` → frontend at 3000, backend at 8000, mailpit at 8025 — all green.

#### T1.14 — CI pipeline (lint + test + build)
- **Goal:** Every PR runs full checks.
- **Depends on:** T1.13
- **Files:** `.github/workflows/ci.yml`, `.github/dependabot.yml`
- **References:** §10.3
- **Acceptance criteria:**
  - [ ] CI matrix: backend (ruff, mypy, pytest, coverage), frontend (eslint, type-check, vitest)
  - [ ] Coverage report uploaded as artifact
  - [ ] CI runs on PR and on push to `main`
  - [ ] CI is mandatory for merge (branch protection rule documented in README)
  - [ ] `pip-audit` and `npm audit --audit-level=high` run; fail on high+ vulns
  - [ ] Dependabot configured for Python (pip), npm (pnpm), GitHub Actions
- **Verification:** Open a PR → see CI green; intentionally break a test → CI red.

#### T1.15 — Initial deployment to staging
- **Goal:** Live URL for the (auth-only) app on staging infra.
- **Depends on:** T1.14
- **Files:** `.github/workflows/deploy-staging.yml`, infra config files (e.g., `railway.json` or `render.yaml`), `frontend/vercel.json`
- **References:** §11
- **Acceptance criteria:**
  - [ ] Frontend deployed to Vercel (staging project) with env vars set
  - [ ] Backend deployed to Railway/Render (staging) with env vars set
  - [ ] Postgres on Neon/Supabase (staging DB)
  - [ ] Migrations run on deploy
  - [ ] Sentry connected (frontend + backend)
  - [ ] UptimeRobot pings `/health/ready` every 5 min
  - [ ] HTTPS enforced; security headers verified via securityheaders.com (A grade)
- **Verification:** Live URL works end-to-end (register → verify → login). securityheaders.com scan ≥ A.

---

### Phase 2 — AI Core (the agent + chat experience)

**Goal:** Working bilingual medical agent with RAG, tools, safety guards, streaming chat. By the end of Phase 2, a verified user can have a multi-turn medical triage conversation in Arabic or English, see citations, see a triage assessment, and the agent reliably escalates red flags.

#### T2.01 — Knowledge base build pipeline
- **Goal:** Script that downloads sources, chunks, embeds, and inserts into `kb_chunks`.
- **Depends on:** T1.03
- **Files:** `scripts/download_kb.py`, `scripts/build_kb.py`, `backend/app/ai/retrieval/{embeddings,vectorstore,chunker}.py`, tests
- **References:** §8.4, §8.5, §12.2
- **Acceptance criteria:**
  - [ ] Downloader fetches WHO, MedlinePlus, Egyptian MoH sources (configurable list)
  - [ ] Chunker splits to 256-token chunks, 64-token overlap, sentence-aware
  - [ ] Embedder uses `intfloat/multilingual-e5-large`
  - [ ] Inserts batches into `kb_chunks` with pgvector embedding
  - [ ] Idempotent: re-running doesn't duplicate
  - [ ] Source license recorded per chunk in `metadata`
  - [ ] At least 5K chunks indexed across AR + EN
- **Verification:** `SELECT count(*), language FROM kb_chunks GROUP BY language;` shows expected counts.

#### T2.02 — Retrieval API (search + rerank)
- **Goal:** A `Retriever` that returns top-k reranked chunks for a query.
- **Depends on:** T2.01
- **Files:** `backend/app/ai/retrieval/{retriever,reranker}.py`, tests
- **References:** §8.4
- **Acceptance criteria:**
  - [ ] `Retriever.search(query, language, top_k=5)` returns reranked `KBChunk` list
  - [ ] Underlying ANN: pgvector cosine; over-fetch (e.g., 20) then rerank to 5
  - [ ] Reranker: bge-reranker-v2-m3
  - [ ] Latency p95 < 500ms on dev DB with 5K chunks (CPU)
  - [ ] Unit tests against fixed corpus + golden queries
- **Verification:** Sample queries return relevant chunks (verified manually on 10 cases).

#### T2.03 — LLM provider abstraction
- **Goal:** Pluggable LLM provider with at least 2 implementations.
- **Depends on:** T1.02
- **Files:** `backend/app/ai/llm/{base,hf_inference,openai_compat}.py`, tests with mocks
- **References:** §3.3, §4.5
- **Acceptance criteria:**
  - [ ] `LLMProvider` protocol with `generate_stream(messages, tools, max_tokens, temperature)` async generator
  - [ ] Implementation 1: HuggingFace Inference API
  - [ ] Implementation 2: OpenAI-compatible (works with vLLM/Ollama for local)
  - [ ] Selected via `LLM_PROVIDER` env var
  - [ ] Retry with exponential backoff on transient errors
  - [ ] Token usage logged per call
- **Verification:** Switch env var, get same agent behavior with different backends.

#### T2.04 — Tool ABC + registry
- **Goal:** Pluggable tool system.
- **Depends on:** T1.02
- **Files:** `backend/app/ai/agent/{base,registry}.py`, tests
- **References:** §4.5, §8.2
- **Acceptance criteria:**
  - [ ] `Tool` ABC with: `name`, `description`, `input_schema` (pydantic), `output_schema`, `async run(input)`
  - [ ] `ToolRegistry` registers tools and exposes JSON-schema list for LLM tool-use
  - [ ] Tools auto-register via decorator
  - [ ] Tests with a dummy tool
- **Verification:** Define a fake tool → it appears in `registry.list()` and runs.

#### T2.05 — Tool: retrieve_medical_knowledge
- **Goal:** Wrap the retriever as an agent tool.
- **Depends on:** T2.02, T2.04
- **Files:** `backend/app/ai/tools/retrieve_knowledge.py`, tests
- **References:** §8.2
- **Acceptance criteria:**
  - [ ] Tool input: `{query: str, language: str, top_k: int=5}`
  - [ ] Tool output: list of chunks with `{source, title, url, content_excerpt}`
  - [ ] Validates input via pydantic
- **Verification:** Run tool with sample query → matches retriever behavior.

#### T2.06 — Tool: detect_red_flags
- **Goal:** Rule-based + LLM-fallback red-flag detector.
- **Depends on:** T2.04
- **Files:** `backend/app/ai/tools/red_flag_detector.py`, `backend/app/ai/safety/red_flags_keywords.yaml`, tests
- **References:** §8.3
- **Acceptance criteria:**
  - [ ] Keyword lists for AR + EN covering: chest pain radiating, stroke FAST signs, severe bleeding, anaphylaxis, suicidal ideation, severe respiratory distress, sepsis red flags
  - [ ] Tool returns `{has_red_flag, flags, severity}`
  - [ ] Tests: 50 emergency cases (recall ≥ 95%) + 20 non-emergency (false-positive rate ≤ 10%)
- **Verification:** Run safety eval suite — meets thresholds.

#### T2.07 — Tool: score_triage (Manchester Triage Scale)
- **Goal:** Compute triage level + score from symptoms.
- **Depends on:** T2.04, T2.06
- **Files:** `backend/app/ai/tools/triage_scorer.py`, `backend/app/ai/safety/triage_rules.yaml`, tests
- **References:** §8.2
- **Acceptance criteria:**
  - [ ] Implements simplified Manchester Triage decision rules
  - [ ] Inputs: symptoms list, optional age + comorbidities
  - [ ] Outputs: level (`emergency`/`urgent`/`routine`), score 0-100, reasoning string
  - [ ] Red flags from T2.06 force `emergency`
  - [ ] Tests on 200-case gold set: accuracy ≥ 80%, macro-F1 ≥ 0.75
- **Verification:** Eval suite green.

#### T2.08 — Tool: summarize_for_doctor
- **Goal:** LLM-driven structured summary of a conversation for a doctor.
- **Depends on:** T2.03, T2.04
- **Files:** `backend/app/ai/tools/doctor_summary.py`, `backend/app/ai/prompts/doctor_summary_{ar,en}.txt`, tests
- **References:** §8.2
- **Acceptance criteria:**
  - [ ] Input: conversation_id; loads messages
  - [ ] Output: markdown with sections: Chief complaint, History, Symptoms, Risk factors, Red flags, AI triage, Recommended next steps
  - [ ] Uses fixed prompt template; no clinical claims without conversation backing
  - [ ] Tests on 10 sample conversations (manual review of output quality)
- **Verification:** Generated summary is correct on sample cases (manual sign-off).

#### T2.09 — Agent core (ReAct loop)
- **Goal:** The full agent loop wiring LLM, tools, safety, streaming.
- **Depends on:** T2.03, T2.05–T2.08
- **Files:** `backend/app/ai/agent/agent.py`, `backend/app/ai/agent/prompts/system_{ar,en}.txt`, tests
- **References:** §8.1, §8.3
- **Acceptance criteria:**
  - [ ] Implements pseudocode in §8.1
  - [ ] Streams tokens, tool calls, tool results, citations as separate events
  - [ ] Hard-stops at MAX_ITERATIONS (default 5)
  - [ ] Red-flag fast path bypasses LLM
  - [ ] Citation enforcement: no clinical assertion without a retrieved source ID
  - [ ] PII scrub on input
  - [ ] Tests with mocked LLM cover: golden path, tool-call, multi-turn, red-flag fast path, max-iteration cutoff
- **Verification:** Run agent end-to-end on 10 sample conversations — outputs look right.

#### T2.10 — Conversation API (CRUD + streaming chat)
- **Goal:** REST + SSE endpoints from §6.4.
- **Depends on:** T2.09
- **Files:** `backend/app/modules/conversations/{router,service,schemas}.py`, tests
- **References:** §6.4
- **Acceptance criteria:**
  - [ ] All endpoints in §6.4 implemented
  - [ ] SSE streaming works with proper event types
  - [ ] On red flag detected mid-conversation, conversation `status=flagged_for_review` and red flags stored
  - [ ] Triage state computed and persisted on each agent turn
  - [ ] Owner-only access enforced
  - [ ] Rate limit 20/min/user
  - [ ] Tests: integration tests for golden + 5 error paths
- **Verification:** End-to-end chat via curl streaming — works.

#### T2.11 — Frontend chat UI
- **Goal:** Real-time streaming chat with citations, triage indicator, tool-call display.
- **Depends on:** T2.10, T1.10
- **Files:** `frontend/app/(app)/chat/**`, `frontend/components/chat/**`, `frontend/lib/api/chat.ts`, `frontend/hooks/useChatStream.ts`
- **References:** §7
- **Acceptance criteria:**
  - [ ] New chat page (`/chat`) creates a conversation on first message
  - [ ] Existing chat (`/chat/[id]`) loads messages and resumes
  - [ ] Message bubbles distinguish user / assistant / tool / system
  - [ ] Streaming: tokens appear progressively, with skeleton until first token
  - [ ] Tool-call badges show "🔍 retrieving knowledge..." while running
  - [ ] Citations appear as inline chips; click opens source modal
  - [ ] Triage panel (sidebar) updates live (color-coded green/yellow/red)
  - [ ] Composer: textarea, send button, Enter-to-send, Shift+Enter newline, character counter, language auto-detect indicator
  - [ ] Mobile-responsive: composer sticky bottom, panel collapsible
  - [ ] All UI strings localized (AR/EN)
  - [ ] Component tests for MessageList, MessageBubble, ChatComposer, TriagePanel
- **Verification:** Live chat in browser — Arabic + English flows work, citations render, triage updates.

#### T2.12 — Conversation history page
- **Goal:** List all of user's conversations with search, filter, delete.
- **Depends on:** T2.10
- **Files:** `frontend/app/(app)/history/page.tsx`, related components
- **References:** §6.4, §7
- **Acceptance criteria:**
  - [ ] Paginated list with: title (auto-generated), date, triage level chip, status
  - [ ] Search by title/content
  - [ ] Filter by status, triage level, date range
  - [ ] Delete (soft) with confirmation
  - [ ] Click → opens conversation in chat page
  - [ ] Empty state when no conversations
- **Verification:** Create 30 conversations → list shows pagination → search/filter works.

#### T2.13 — Tool: `analyze_vision` (preliminary image triage)
- **Goal:** Image upload → vision-LLM analysis → urgency + findings + disclaimer.
- **Depends on:** T2.03 (LLM provider), T2.04 (tool registry)
- **Files:** `backend/app/ai/tools/analyze_vision.py`, `backend/app/ai/llm/vision_provider.py`, `backend/app/modules/conversations/router.py` (multipart upload), tests
- **References:** §8.2.1, §6.4
- **Acceptance criteria:**
  - [ ] Accepts JPEG/PNG/WebP/HEIC up to 10 MB
  - [ ] Image stored to S3/MinIO; URL signed (24h)
  - [ ] Calls vision LLM (GPT-4o Vision in MVP; pluggable to local LLaVA/Qwen-VL)
  - [ ] Output: `{findings, urgency, confidence, disclaimer}` — disclaimer ALWAYS present, ALWAYS in user's language
  - [ ] Records in `vision_analyses` table
  - [ ] Refuses non-clinical images (cats, screenshots) and returns a polite error
  - [ ] PII / faces blurred before storage when `kind='photo'` (Pillow + face detection)
  - [ ] Tests: 5 sample medical images (synthetic) + 3 non-medical (refusal)
- **Verification:** Upload chest X-ray → urgency + findings returned; upload meme → polite refusal.

#### T2.14 — Tool: `check_medication_interactions`
- **Goal:** Drug-drug + drug-allergy + dose-range safety check.
- **Depends on:** T2.04
- **Files:** `backend/app/ai/tools/medication.py`, `backend/data/medications/{interactions,doses}.json` (curated subset), tests
- **References:** §8.2.2
- **Acceptance criteria:**
  - [ ] Bundled interaction dataset for top 200 commonly prescribed drugs in Egypt
  - [ ] Checks RxNorm-mapped names + brand-name aliases (AR + EN)
  - [ ] Returns `{interactions: [{drug_a, drug_b, severity, source}], allergy_conflicts, dose_warnings}`
  - [ ] Severity levels: contraindicated / major / moderate / minor
  - [ ] Tests: 30 known interaction pairs (precision ≥ 0.9, recall ≥ 0.8)
- **Verification:** Run with warfarin + aspirin → bleeding-risk warning returned.

#### T2.15 — Tool: `screen_mental_health` (PHQ-9 / GAD-7)
- **Goal:** Standardized depression and anxiety screening flow.
- **Depends on:** T2.04
- **Files:** `backend/app/ai/tools/mental_health.py`, `backend/app/ai/prompts/phq9_{ar,en}.json`, `backend/app/ai/prompts/gad7_{ar,en}.json`, tests
- **References:** §8.2.2
- **Acceptance criteria:**
  - [ ] Tool emits questions one at a time as a sub-conversation; collects responses
  - [ ] Validated AR translation of PHQ-9 and GAD-7 questions (cite source)
  - [ ] Scoring per official cutoffs (e.g., PHQ-9 ≥ 20 = severe)
  - [ ] **Suicidality item** in PHQ-9 (Q9) > 0 → triggers red-flag fast path with crisis hotline (Egypt: 0800 8888 800)
  - [ ] Output: `{score, severity, recommendation, crisis_resources?}`
  - [ ] Tests: synthetic responses produce expected severity bands; suicidality test verifies escalation
- **Verification:** Run PHQ-9 with maxed responses → severe + crisis resources surfaced.

#### T2.16 — Pediatric & pregnancy safety branches
- **Goal:** Branch the agent's reasoning when patient is a child or pregnant.
- **Depends on:** T2.09 (agent core), T2.07 (triage scorer)
- **Files:** `backend/app/ai/agent/branches/{pediatric,pregnancy}.py`, `backend/app/ai/prompts/system_pediatric_{ar,en}.txt`, `backend/app/ai/prompts/system_pregnancy_{ar,en}.txt`, `backend/app/ai/tools/{assess_pediatric_safety,assess_pregnancy_safety}.py`, tests
- **References:** §8.2.2, §8.3 (Stage 2 branch switching)
- **Acceptance criteria:**
  - [ ] When patient profile DOB indicates age < 18, system prompt switches to pediatric branch automatically
  - [ ] When patient explicitly indicates pregnancy in conversation OR profile, switches to pregnancy branch
  - [ ] `assess_pediatric_safety`: dose-by-weight check, age-appropriate red flags (e.g., infants < 3 mo with fever → emergency)
  - [ ] `assess_pregnancy_safety`: pregnancy-category warnings on meds (FDA A/B/C/D/X), OB red flags (severe headache, vision changes, heavy bleeding)
  - [ ] Both branches override default safety with stricter rules
  - [ ] Tests: 20 pediatric cases + 15 pregnancy cases on gold set
- **Verification:** Run a fever case for a 2-month-old → emergency triage; run NSAID question for a pregnant patient → category-D warning.

---

### Phase 2.5 — Advanced safety, UI polish, and PHI hardening (3–4 weeks)

**Goal:** Take the working MVP from Phase 2 and make it production-grade clinically and visually. By the end of Phase 2.5: the agent has hallucination/uncertainty checking, a glassmorphic UI with Framer Motion, encrypted PHI, hash-chained audit logs, and a Tree-of-Thought reasoning mode for hard cases.

#### T2.5.01 — Hallucination detector tool + post-LLM gate
- **Goal:** Verify every clinical claim against retrieved sources before delivering the response.
- **Depends on:** T2.03, T2.05, T2.09
- **Files:** `backend/app/ai/tools/verify_no_hallucination.py`, `backend/app/ai/safety/post_llm_gate.py`, `backend/app/ai/prompts/verifier_{ar,en}.txt`, tests
- **References:** §8.2.2, §8.3 Stage 3
- **Acceptance criteria:**
  - [ ] Verifier LLM (smaller, faster — e.g., 3B model) compares each claim sentence against retrieved chunks
  - [ ] Returns `{hallucination_score: 0..1, unsupported_claims: [...], suggested_rewrites: [...]}`
  - [ ] If score > 0.3, the gate rewrites unsupported sentences with explicit uncertainty markers
  - [ ] Result persisted to `safety_assessments`
  - [ ] Tests: 50 synthetic claims (25 grounded, 25 fabricated) — recall on fabricated ≥ 0.8
- **Verification:** Inject a fabricated drug interaction in agent output → gate flags + rewrites.

#### T2.5.02 — Uncertainty calibrator + UI confidence badges
- **Goal:** Surface per-claim confidence to the user.
- **Depends on:** T2.5.01, T2.11
- **Files:** `backend/app/ai/tools/calibrate_uncertainty.py`, `frontend/components/chat/ConfidenceBadge.tsx`, tests
- **References:** §8.2.2, §8.3 Stage 3, §7.5
- **Acceptance criteria:**
  - [ ] Tool returns `{claims: [{text, confidence, band}]}` with `band ∈ {high, medium, low}`
  - [ ] `MessageBubble` renders a `<ConfidenceBadge>` next to each sentence with `band != 'high'`
  - [ ] Hover shows the supporting/missing evidence
  - [ ] Bands are accessible (text + icon, not color alone)
  - [ ] Localized AR/EN
- **Verification:** Inject a low-confidence claim → low badge shows in UI with tooltip.

#### T2.5.03 — Tree-of-Thought reasoning mode
- **Goal:** Multi-branch differential diagnosis under uncertainty.
- **Depends on:** T2.5.01, T2.05, T2.09
- **Files:** `backend/app/ai/agent/tot_mode.py`, `backend/app/ai/tools/tot_differential_diagnosis.py`, `frontend/components/chat/DifferentialPanel.tsx`, tests
- **References:** §8.8
- **Acceptance criteria:**
  - [ ] Mode selection rule from §8.8.3 implemented in agent supervisor
  - [ ] Generates 3 branches, scores via verifier, prunes to top 2
  - [ ] UI panel shows both differentials with confidence bars + supporting evidence
  - [ ] Falls back to ReAct mode on retrieval failure
  - [ ] Tests: 10 ambiguous cases — both branches surfaced with reasonable hypotheses
- **Verification:** Send ambiguous symptom set (e.g., chest pain + cough) → DifferentialPanel renders 2 hypotheses.

#### T2.5.04 — SOAP note formatter tool
- **Goal:** Generate a clinician-format S/O/A/P note from any conversation.
- **Depends on:** T2.04, T2.10
- **Files:** `backend/app/ai/tools/format_soap.py`, `backend/app/ai/prompts/soap_{ar,en}.txt`, tests
- **References:** §8.2.2
- **Acceptance criteria:**
  - [ ] Output: structured markdown with `## Subjective`, `## Objective`, `## Assessment`, `## Plan` sections (AR or EN per locale)
  - [ ] Cites supporting messages by ID
  - [ ] Available as alternate handoff format alongside the existing summary
  - [ ] Tests: 5 sample conversations — manual sign-off
- **Verification:** Generate SOAP for a test conversation → all 4 sections populated correctly.

#### T2.5.05 — Glassmorphic design system implementation
- **Goal:** Apply §7.5 design tokens across the app.
- **Depends on:** T1.08, T2.11
- **Files:** `frontend/app/globals.css`, `frontend/lib/theme.ts`, `frontend/tailwind.config.ts`, all component files refactored
- **References:** §7.5
- **Acceptance criteria:**
  - [ ] All design tokens from §7.5 in `globals.css` `@theme` block
  - [ ] Glass utilities applied to: AppShell sidebar, Chat composer, Triage panel, Cards, Modals
  - [ ] Manrope (display) + Inter (body) + Cairo (Arabic) loaded with `next/font`
  - [ ] Dark mode parity verified (every glass element has a dark variant)
  - [ ] Lighthouse accessibility score ≥ 95 on chat page after change
  - [ ] No hardcoded colors anywhere in `frontend/components/**/*.tsx` (CI grep check)
- **Verification:** Visual diff vs Phase 2 — chat page is now glassmorphic; AR + EN both look polished.

#### T2.5.06 — Framer Motion variants + animated chat / SOS button
- **Goal:** Smooth micro-interactions across the app.
- **Depends on:** T2.5.05
- **Files:** `frontend/lib/motion.ts`, components updated to use variants, `frontend/components/emergency/SOSButton.tsx`
- **References:** §7.5
- **Acceptance criteria:**
  - [ ] `lib/motion.ts` exports `springSmooth`, `bounce`, `fadeUp`, `pulseUrgent`
  - [ ] Chat messages enter with `fadeUp`
  - [ ] Triage panel transitions on level change with `springSmooth`
  - [ ] Emergency level uses `pulseUrgent` (max 3 cycles, then static)
  - [ ] `prefers-reduced-motion` is honored — falls back to instant transitions or short opacity-only fades
  - [ ] SOS button (visible on every authenticated page) — one-tap reveals Egypt emergency contacts (123, 0800 8888 800 for crisis)
- **Verification:** Browser test with reduced-motion off and on; emergency conversation triggers pulse correctly.

#### T2.5.07 — PHI field encryption (Fernet wrapper + ORM)
- **Goal:** Encrypt sensitive PHI columns at the application layer.
- **Depends on:** T1.03, T2.10
- **Files:** `backend/app/core/encryption.py`, `backend/app/models/_types.py` (EncryptedString, EncryptedJSON), `backend/alembic/versions/00XX_phi_encryption.py`, `docs/runbooks/key_rotation.md`, tests
- **References:** §9.6
- **Acceptance criteria:**
  - [ ] `encrypt_phi` / `decrypt_phi` helpers using Fernet
  - [ ] SQLAlchemy `TypeDecorator` types: `EncryptedString` and `EncryptedJSON`
  - [ ] Migration adds `encrypted_content`, `encrypted_analysis` columns (nullable)
  - [ ] `messages`, `vision_analyses`, `patient_profiles`, `handoff_summaries` use the new types via `PHI_ENCRYPTION_ENABLED` toggle
  - [ ] Startup check fails fast if `ENV=production` and `DATA_ENCRYPTION_KEY` missing
  - [ ] Key rotation runbook with dual-key window
  - [ ] Tests: round-trip encryption, toggle on/off, missing-key startup failure
- **Verification:** Toggle on → DB rows store ciphertext; toggle off → plaintext; rotation playbook walked end-to-end.

#### T2.5.08 — Audit hash chaining
- **Goal:** Make audit log tamper-evident.
- **Depends on:** T1.11
- **Files:** `backend/app/common/audit.py` (extend), `backend/app/common/audit_chain.py`, `backend/alembic/versions/00XX_audit_chain.py`, `scripts/audit_verify.py`, tests
- **References:** §9.7
- **Acceptance criteria:**
  - [ ] Migration adds `sequence`, `previous_hash`, `current_hash` columns
  - [ ] Insert helper computes hash inside a SERIALIZABLE transaction
  - [ ] Verification script walks the chain → reports first break sequence (or `OK`)
  - [ ] Admin endpoint `GET /admin/audit-verify` exposes the result
  - [ ] CI runs verification on test DB after the test suite
  - [ ] Negative test: manual UPDATE on an audit row → verifier detects it
- **Verification:** Run a flow → verify chain → tamper one row → re-verify → broken_at reported.

#### T2.5.09 — Vision UI: image upload widget + analysis result card
- **Goal:** Frontend surface for the `analyze_vision` tool.
- **Depends on:** T2.13, T2.5.05
- **Files:** `frontend/components/chat/ImageUpload.tsx`, `frontend/components/chat/VisionResultCard.tsx`, `frontend/components/chat/VisionDisclaimerModal.tsx`
- **References:** §8.2.1, §7.5
- **Acceptance criteria:**
  - [ ] Drag-and-drop or tap-to-pick image upload (mobile camera capture supported)
  - [ ] Client-side file size + type validation
  - [ ] Disclaimer modal shown on first use (consent recorded in `audit_logs`)
  - [ ] Result card with findings, urgency badge, confidence bar, AND a prominent "preliminary, not radiology" disclaimer in user's language
  - [ ] Image thumbnail in chat with "view full" modal
  - [ ] Component tests for upload + result card
- **Verification:** Upload chest X-ray on mobile → result card renders correctly with disclaimer.

---

### Phase 3 — ML Pipeline (data, fine-tuning, evaluation, MLOps)

**Goal:** A reproducible, tracked, evaluated ML pipeline. By end of Phase 3, the system has a fine-tuned model with measured performance, a knowledge-base build pipeline orchestrated, and MLflow tracking every experiment.

#### T3.01 — Data collection & preprocessing notebooks
- **Files:** `notebooks/01_data_exploration.ipynb`, `notebooks/02_preprocessing.ipynb`, `data/processed/*.parquet`, `docs/data_card.md`
- **Acceptance:**
  - [ ] Downloads MedDialog (EN), HealthCareMagic, MedQA
  - [ ] Translates 10K MedDialog turns to AR via NLLB-200
  - [ ] Manually curates 2K AR Q&A pairs
  - [ ] PII scrub, normalization (Arabic), train/val/test split (80/10/10)
  - [ ] Data card with sources, licenses, sizes, biases

#### T3.02 — Triage label assignment + gold eval set
- **Files:** `scripts/label_triage.py`, `data/gold/triage_eval.jsonl`
- **Acceptance:**
  - [ ] Rule-based labeler over chief-complaint keywords
  - [ ] 200-case manually verified gold eval set covering all triage levels and AR/EN

#### T3.03 — Base model benchmark
- **Files:** `notebooks/03_base_benchmark.ipynb`
- **Acceptance:**
  - [ ] Compares Qwen2.5-7B, Llama-3.1-8B, Jais-13B on 50 triage prompts
  - [ ] Picks winner with rationale
  - [ ] Writes choice into `docs/03_tech_stack.md` (or equivalent)

#### T3.04 — LoRA fine-tuning
- **Files:** `notebooks/04_finetune.ipynb`, `mlops/configs/lora_v1.yaml`
- **Acceptance:**
  - [ ] Colab-runnable; fits in T4 with 4-bit
  - [ ] Logs every step + hyperparam to MLflow
  - [ ] Saves LoRA adapter + tokenizer to HF Hub (private)
  - [ ] Reports final loss curves

#### T3.05 — Evaluation suite
- **Files:** `scripts/eval.py`, `notebooks/05_evaluation.ipynb`, `tests/eval/*.jsonl`
- **Acceptance:**
  - [ ] All metrics from §8.7 computed
  - [ ] Comparison table: base / fine-tuned / fine-tuned+RAG
  - [ ] Bias slice analysis (gender, age groups)
  - [ ] Failure case writeup

#### T3.06 — Hallucination & safety eval
- **Files:** `tests/eval/hallucination_cases.jsonl`, `tests/eval/safety_cases.jsonl`
- **Acceptance:**
  - [ ] 100 cases reviewed manually for hallucination rate
  - [ ] 50 emergency cases for red-flag recall
  - [ ] 50 out-of-scope queries for refusal appropriateness
  - [ ] Targets in §8.7 met or documented gap

#### T3.07 — MLflow integration in backend
- **Files:** `backend/app/ai/mlflow_client.py`
- **Acceptance:**
  - [ ] Backend can fetch latest "production"-tagged adapter from MLflow registry
  - [ ] Inference logs metadata (model_version, latency) to MLflow

#### T3.08 — KB pipeline (Airflow or Prefect)
- **Files:** `pipeline/dags/kb_pipeline.py`, `pipeline/dags/eval_pipeline.py`
- **Acceptance:**
  - [ ] DAG: download → chunk → embed → upsert → evaluate retrieval quality
  - [ ] Scheduled weekly
  - [ ] Failure alerts to Sentry/email

#### T3.09 — Attention analysis writeup
- **Files:** `notebooks/06_attention_analysis.ipynb`
- **Acceptance:**
  - [ ] Visualizes attention heatmaps over symptom keywords on 10 sample inputs
  - [ ] Discusses how cross-attention re-ranking improves RAG

#### T3.10 — Replace base agent with fine-tuned model in backend
- **Files:** `backend/app/ai/llm/finetuned.py`
- **Acceptance:**
  - [ ] Backend uses fine-tuned adapter via vLLM or HF Inference Endpoint
  - [ ] A/B switch: env var to toggle base vs fine-tuned
  - [ ] Re-runs Phase 2 integration tests; all green

#### T3.11 — Specialized tool evaluation
- **Files:** `tests/eval/specialized_tools/{medication,mental_health,pediatric,pregnancy}.jsonl`, `scripts/eval_specialized.py`
- **Acceptance:**
  - [ ] Medication interactions: 50 known pairs (precision ≥ 0.9, recall ≥ 0.8)
  - [ ] PHQ-9 / GAD-7: validity check on synthetic responses (scoring matches official cutoffs)
  - [ ] Pediatric: 40 cases (20 emergency, 20 routine; recall on emergency ≥ 0.95)
  - [ ] Pregnancy: 30 cases including Category-D drug warnings (recall ≥ 0.9)
  - [ ] Report committed at `docs/eval/specialized_tools_report.md`

#### T3.12 — Vision tool evaluation
- **Files:** `tests/eval/vision/cases.jsonl`, `tests/eval/vision/images/`, `scripts/eval_vision.py`
- **Acceptance:**
  - [ ] 100-case gold set: 50 X-rays (mix of normal, pneumonia, fracture indicators), 30 skin lesions, 20 non-clinical
  - [ ] Sensitivity ≥ 0.85 on "needs urgent imaging review"
  - [ ] Specificity ≥ 0.85 on non-clinical images (proper refusal)
  - [ ] Confusion matrix + false-positive analysis in `docs/eval/vision_report.md`

---

### Phase 4 — Polish & Deploy (admin, doctor, support, prod release)

**Goal:** All non-AI features polished, comprehensive tests, prod deployment, full documentation. By end of Phase 4, the project is submission-ready and live.

#### T4.01 — Doctor handoff: generate + PDF
- **Files:** `backend/app/modules/handoff/`, `backend/app/common/pdf.py`, frontend handoff page
- **Acceptance:**
  - [ ] `POST /conversations/{id}/handoff` produces summary + PDF
  - [ ] PDF includes: patient profile, AI triage, conversation transcript, citations, disclaimer
  - [ ] Frontend preview + download

#### T4.02 — Send handoff to doctor + doctor inbox
- **Files:** `backend/app/modules/handoff/`, `frontend/app/doctor/inbox/`
- **Acceptance:**
  - [ ] Patient can send handoff to a doctor (search/select)
  - [ ] Doctor sees in inbox; mark reviewed; add private notes

#### T4.03 — Admin dashboard
- **Files:** `backend/app/modules/admin/`, `frontend/app/admin/dashboard/`
- **Acceptance:**
  - [ ] Stats cards: total users, active today, safety incidents this week, system health
  - [ ] Recent registrations
  - [ ] Conversation volume chart (last 30 days)

#### T4.04 — Admin: user + doctor management
- **Files:** `frontend/app/admin/users/`, `frontend/app/admin/doctors-pending/`
- **Acceptance:**
  - [ ] Searchable user table with filters; deactivate; change role (with confirm)
  - [ ] Pending doctor queue with approve/reject (with reason)

#### T4.05 — Admin: safety incidents + audit log viewer
- **Files:** `frontend/app/admin/safety/`, `frontend/app/admin/audit/`
- **Acceptance:**
  - [ ] Flagged conversations list with filters
  - [ ] Conversation deep-link
  - [ ] Audit log table with filters by user/action/date

#### T4.06 — Help & Support: FAQ + contact form
- **Files:** `frontend/app/support/`, `backend/app/modules/support/`
- **Acceptance:**
  - [ ] FAQ page with markdown content (i18n)
  - [ ] Contact form posts to backend; sends email + saves ticket
  - [ ] Auto-reply email to user

#### T4.07 — Smart medical follow-up emails (Innovation)
- **Files:** `backend/app/modules/notifications/`, `pipeline/dags/safety_followup.py`
- **Acceptance:**
  - [ ] Conversations with red flags trigger a 24h follow-up email: "We recommended you see a doctor — please confirm you have"
  - [ ] One-click "I saw a doctor" / "I haven't yet" links update conversation
  - [ ] Tested end-to-end with mailpit

#### T4.08 — E2E tests (Playwright)
- **Files:** `frontend/e2e/**`
- **Acceptance:**
  - [ ] Auth flow: register → verify → login → logout
  - [ ] Chat flow: new chat → multi-turn → triage shown
  - [ ] Handoff flow: generate → preview → download → send to doctor
  - [ ] Admin flow: approve doctor → deactivate user
  - [ ] All run in CI

#### T4.09 — Performance pass
- **Files:** lighthouse reports, k6 scripts
- **Acceptance:**
  - [ ] Lighthouse score ≥ 90 on landing + chat pages
  - [ ] Bundle analyzed; route-level code splitting verified
  - [ ] API p95 latency under load (50 RPS chat) documented

#### T4.10 — Production deployment
- **Files:** `.github/workflows/deploy-prod.yml`, prod env configs
- **Acceptance:**
  - [ ] Prod env on Vercel + Railway + Neon
  - [ ] DNS configured (custom domain optional)
  - [ ] HTTPS, HSTS, security headers all green (securityheaders.com A+)
  - [ ] Sentry releases tracked per deploy

#### T4.11 — Final documentation
- **Files:** `docs/**`, `README.md`
- **Acceptance:**
  - [ ] Architecture doc with diagrams
  - [ ] Setup guide
  - [ ] User guide
  - [ ] API docs (OpenAPI export)
  - [ ] Contributing guide
  - [ ] Final report for DEPI (problem, methods, results, business impact, team contributions)
  - [ ] Demo video (5-10 min)

#### T4.12 — Prometheus metrics + Grafana Cloud dashboard
- **Goal:** Production-grade metrics emission and visualization.
- **Depends on:** T1.15
- **Files:** `backend/app/core/metrics.py`, `backend/app/main.py` (mount `/metrics`), `infra/grafana/dashboards/medagent.json`
- **References:** §11.6
- **Acceptance criteria:**
  - [ ] All metrics from §11.6 emitted via `prometheus-client`
  - [ ] `/metrics` endpoint reachable internally (firewalled in prod)
  - [ ] Grafana Cloud free-tier project configured with remote-write
  - [ ] Dashboard with: latency p50/p95/p99, agent iteration distribution, tool success rates, hallucination trend, emergency escalations
  - [ ] Alert rules: p95 latency > 3s for 5 min → Slack; hallucination p95 > 0.3 for 30 min → Slack
- **Verification:** Trigger 100 chat requests → metrics visible in Grafana; manually break the LLM provider → alert fires.

#### T4.13 — OpenTelemetry tracing across backend
- **Goal:** Distributed tracing for end-to-end request visibility.
- **Depends on:** T2.10
- **Files:** `backend/app/core/tracing.py`, manual spans in agent loop, `infra/grafana/tempo_config.yaml`
- **References:** §11.6
- **Acceptance criteria:**
  - [ ] `opentelemetry-instrumentation-fastapi` auto-instruments routes
  - [ ] Manual spans inside agent loop: `agent.iteration`, `tool.run.{tool_name}`, `llm.generate`, `safety.verify`
  - [ ] Span attributes carry IDs only — NEVER PHI text
  - [ ] OTLP exporter to Grafana Tempo
  - [ ] Trace IDs included in structlog output (correlation)
  - [ ] Smoke test: a chat request appears as a single trace with all expected child spans
- **Verification:** In Grafana Tempo, find a recent trace and confirm spans + correlated logs.

#### T4.14 — FHIR Bundle export from handoff
- **Goal:** Export a doctor handoff as a FHIR R4 Bundle JSON.
- **Depends on:** T4.01
- **Files:** `backend/app/modules/handoff/fhir_export.py`, `backend/app/common/fhir_models.py`, tests
- **References:** §11.7, §6.5
- **Acceptance criteria:**
  - [ ] Endpoint `GET /handoffs/{id}/export?format=fhir` returns `application/fhir+json`
  - [ ] Bundle type: `document`; first entry: `Composition`
  - [ ] Resources: Patient, Condition, Observation, MedicationStatement, AllergyIntolerance, ClinicalImpression
  - [ ] Validates against the public HAPI FHIR validator (CI step calls the API)
  - [ ] Inserts a row into `handoff_exports`
  - [ ] Frontend handoff page shows "Download as FHIR" button
- **Verification:** Generate handoff → export FHIR → upload to HAPI validator → green.

#### T4.15 — HL7 v2 export from handoff
- **Goal:** Export a doctor handoff as an HL7 v2.5 message for legacy EHRs.
- **Depends on:** T4.01
- **Files:** `backend/app/modules/handoff/hl7_export.py`, tests
- **References:** §11.7, §6.5
- **Acceptance criteria:**
  - [ ] Endpoint `GET /handoffs/{id}/export?format=hl7` returns `application/hl7-v2`
  - [ ] Message structure: ADT^A04 with OBX segments for findings
  - [ ] Test parses message back via `hl7` library and asserts segment integrity
  - [ ] Inserts a row into `handoff_exports`
- **Verification:** Generate handoff → export HL7 → re-parse → all segments present.

#### T4.16 — Emergency / SOS UI
- **Goal:** One-tap emergency assistance always reachable from anywhere in the app.
- **Depends on:** T2.5.06
- **Files:** `frontend/components/emergency/SOSButton.tsx`, `frontend/components/emergency/EmergencyModal.tsx`, `frontend/app/(app)/layout.tsx`
- **References:** §7.5, §8.3 Stage 1
- **Acceptance criteria:**
  - [ ] Floating SOS button on every authenticated page (bottom-right, glass + pulseUrgent variant)
  - [ ] One tap → modal with: Egypt emergency number (123), poison control, mental-health crisis hotline, ambulance, plus a "share location" button (asks permission, never auto-shares)
  - [ ] When the agent itself escalates an emergency, the SOS modal auto-opens
  - [ ] `prefers-reduced-motion` respected (no pulse, just static highlight)
  - [ ] Localized AR/EN; Arabic numerals option in settings
  - [ ] Hidden on auth pages (login/register) — only available after authentication
- **Verification:** Tap SOS button → modal opens with all numbers and "share location" works; trigger emergency in chat → modal auto-opens.

#### T4.17 — DEPI final submission
- **Files:** `docs/depi/**`
- **Acceptance:**
  - [ ] Final report PDF
  - [ ] Presentation slides PDF
  - [ ] Live demo URL
  - [ ] GitHub repo public
  - [ ] All 5 DEPI milestone deliverables present in `docs/depi/milestone_{1..5}.md`

---

## 14. Cross-cutting acceptance criteria (apply to ALL tasks)

A task is not "done" unless ALL of these are also true:

1. **Tests added or updated** — every new function/endpoint has at least one test
2. **Type-safe** — `mypy` (backend) / `tsc --noEmit` (frontend) pass
3. **Linted** — `ruff` / `eslint` pass; no warnings ignored without justification
4. **Documented** — public functions/endpoints have docstrings; new endpoints in OpenAPI; user-visible features in user docs
5. **Logged** — significant events use `structlog` with appropriate levels
6. **Audited** — state-changing operations write to `audit_logs`
7. **Localized** — every user-facing string has AR + EN translations
8. **Accessible** — components meet checklist in §7.6
9. **Secure** — no secrets in code, no SQL string concatenation, input validated
10. **Reviewable** — task PR includes screenshots/recordings for UI changes; description references task ID
11. **Verified** — verification steps from the task ran and produced expected output
12. **PHI encryption enforced** — when `PHI_ENCRYPTION_ENABLED=true`, sensitive fields go through `EncryptedString`/`EncryptedJSON` types; tests assert ciphertext is stored
13. **Audit chain integrity** — `scripts/audit_verify.py` returns `OK` after every test run

---

## 15. Verification ledger (project-level)

Final acceptance for the project (not per-task):

1. **Fresh-clone install:** `git clone && docker-compose up` brings up the full stack with no manual steps beyond `cp .env.example .env`.
2. **Health green:** All `/health` and `/health/ready` endpoints return 200.
3. **Migrations:** `alembic upgrade head` from empty DB results in §5.2 schema.
4. **Test suite:** `pytest backend/tests` and `pnpm test --filter frontend` both green; coverage ≥ 80% on critical modules.
5. **E2E:** all Playwright suites pass.
6. **AI eval:** `python scripts/eval.py` produces report meeting §8.7 thresholds.
7. **Safety eval:** red-flag recall ≥ 95% on 50-case set.
8. **Lighthouse:** ≥ 90 on landing and chat pages.
9. **Security headers:** securityheaders.com A or A+ on the deployed domain.
10. **Live URLs:** prod URLs respond within 2s p95 from Egypt.
11. **Documentation:** every doc in §13 references list exists and is current.
12. **DEPI deliverables:** all 5 milestone deliverables present with required artifacts.
13. **Specialized tools eval (T3.11):** medication / mental-health / pediatric / pregnancy thresholds all met.
14. **Vision tool eval (T3.12):** sensitivity ≥ 0.85, specificity ≥ 0.85 on the 100-image gold set.
15. **FHIR export validation:** generated bundle passes the public HAPI FHIR validator.
16. **Observability stack:** Prometheus metrics scraped by Grafana Cloud; OTel traces visible in Tempo; one synthetic chat request appears as a single trace with expected child spans.
17. **PHI encryption end-to-end:** with `PHI_ENCRYPTION_ENABLED=true`, manual `psql` SELECT on `messages.encrypted_content` returns BYTEA blobs (not plaintext).
18. **Audit chain end-to-end:** `GET /admin/audit-verify` returns `{ ok: true }`; manual tampering of one row makes it return `broken_at: <sequence>`.

---

## 16. Glossary

- **Agent** — the AI component that orchestrates LLM + tools + safety to answer.
- **Handoff** — a generated summary a patient sends to a doctor.
- **KB / Knowledge base** — the indexed medical content used for RAG.
- **RAG** — Retrieval-Augmented Generation (retrieve relevant context, then generate).
- **Red flag** — a symptom indicating possible emergency (chest pain radiating, FAST signs, etc.).
- **Triage** — assigning urgency level (emergency/urgent/routine).
- **ReAct** — Reason + Act prompt pattern for tool-using agents.
- **LoRA** — Low-Rank Adaptation, a parameter-efficient fine-tuning method.

---

## 17. References (other documents created from this plan)

After this master plan is approved, replicated copies / sub-documents will be created at:

- `README.md` — project intro
- `CLAUDE.md` / `AGENTS.md` — context for AI assistants
- `docs/00_PROJECT_PLAN.md` — replica of this file
- `docs/01_vision_and_scope.md` (extracted from §1, §2)
- `docs/02_architecture.md` (§4 expanded with Mermaid diagrams)
- `docs/03_tech_stack.md` (§3)
- `docs/04_database_schema.md` (§5 with ERD diagram)
- `docs/05_api_specification.md` (§6 with detailed schemas)
- `docs/06_frontend_design.md` (§7 with wireframes)
- `docs/07_ai_ml_design.md` (§8 with diagrams)
- `docs/08_security_model.md` (§9)
- `docs/09_testing_strategy.md` (§10)
- `docs/10_deployment_and_ops.md` (§11)
- `docs/11_data_strategy.md` (§12)
- `docs/12_advanced_tools.md` (§8.2.2 expanded — specialized clinical tools spec)
- `docs/13_safety_pipeline.md` (§8.3 + §8.8 expanded — staged safety + reasoning modes)
- `docs/14_phi_encryption.md` (§9.6 expanded — encryption details + key rotation playbook)
- `docs/15_observability.md` (§11.6 expanded — Prometheus/OTel/MLflow operational guide)
- `docs/16_interoperability.md` (§11.7 expanded — FHIR/HL7 mapping reference)
- `docs/17_design_system.md` (§7.5 expanded — full design tokens + motion library)
- `docs/runbooks/key_rotation.md` (operational runbook for `DATA_ENCRYPTION_KEY` rotation)
- `docs/runbooks/audit_verification.md` (how to run + interpret `audit_verify.py`)
- `docs/eval/specialized_tools_report.md` (T3.11 deliverable)
- `docs/eval/vision_report.md` (T3.12 deliverable)
- `docs/tasks/STATUS.md` — task tracker
- `docs/tasks/phase1/T1.NN_*.md` — one file per task (extracted from §13)
- `docs/tasks/phase2/T2.NN_*.md`
- `docs/tasks/phase2.5/T2.5.NN_*.md`
- `docs/tasks/phase3/T3.NN_*.md`
- `docs/tasks/phase4/T4.NN_*.md`

These will be created as the first execution step after this plan is approved.