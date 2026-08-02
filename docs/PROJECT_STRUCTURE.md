# MedAgent — Project Structure / هيكل المشروع

> **EN:** A file-by-file map of the entire codebase. Every directory has a
> 1-line role description and every file has a one-line purpose, in both
> English and Arabic. Use this as the canonical reference when you want to
> find *where* something lives or *why* it exists.
>
> **AR:** خريطة كاملة للمشروع ملف بملف. كل مجلد فيه سطر يوصّف دوره المعماري،
> وكل ملف فيه سطر بيشرح وظيفته — بالعربي والإنجليزي. استخدم الـ doc ده مرجع
> لو سُئلت "إيه هو الملف ده؟" أو لو بتدور على حاجة معينة في الكود.
>
> **Audience / الجمهور:** DEPI graders · new contributors · clinicians ·
> ops engineers.

---

## How to read this doc / إزاي تقرا الـ doc

كل جدول في الـ doc له ٣ أعمدة:

| Column | Meaning EN | المعنى بالعربي |
| --- | --- | --- |
| **Path / المسار** | Relative path from repo root | المسار من جذر المشروع |
| **English** | One-line purpose in English | شرح بالإنجليزي في سطر |
| **العربية** | One-line purpose in Arabic | شرح بالعربي في سطر |

> ⏩ **Quick-jump:** [Backend](#2-backend--fastapi-service) ·
> [Frontend](#3-frontend--nextjs-16-app-router) ·
> [Scripts](#4-scripts--repo-root-ops-scripts) ·
> [Docs](#5-docs--documentation) ·
> [Cheat-sheet / دليل البحث السريع](#cheat-sheet--دليل-البحث-السريع)

What's intentionally excluded / المُستبعد عمداً:
`node_modules/`, `.next/`, `__pycache__/`, `.venv/`, lock files, build artifacts.

---

## 1. Repository root / جذر المشروع

| Path | English | العربية |
| --- | --- | --- |
| `README.md` | Project pitch + 5-command quick start + tech stack | شرح المشروع + 5 أوامر للبدء + الـ tech stack |
| `ONBOARDING.md` | First-day guide for new contributors | دليل أول يوم لأي عضو جديد |
| `CLAUDE.md` | Working conventions for AI coding agents | تعليمات الـ AI agents اللي بتشتغل على الكود |
| `LICENSE` | Open-source license | رخصة المشروع |
| `Makefile` | `make dev/up/down/reset/seed-all` shortcuts | اختصارات تشغيل الـ docker |
| `docker-compose.yml` | Local stack (Postgres+pgvector, Redis, Mailpit, backend, frontend) | تكوين البيئة المحلية |
| `docker-compose.prod.yml` | Production overrides (no Mailpit, no hot reload) | تكوين الإنتاج (overrides) |
| `pyproject.toml` | Python deps + ruff/mypy/pytest config (managed via uv) | حزم Python + إعدادات الـ tooling |
| `package.json` | pnpm workspace root | الـ workspace root للـ pnpm |
| `pnpm-workspace.yaml` | Declares `frontend/` as the workspace | بيحدد إن `frontend/` هو الـ workspace |
| `.python-version` | Pins Python 3.12 | بيثبت Python 3.12 |
| `.editorconfig` | Cross-IDE indentation defaults | إعدادات تنسيق موحّدة بين الـ IDEs |
| `.dockerignore` | Excludes caches from Docker build context | استثناءات بناء صورة Docker |
| `.coveragerc` | Coverage exclusion patterns | استثناءات قياس الـ coverage |
| `plan.md` | Historical phase-by-phase roadmap | خطة المراحل من البداية لحد دلوقتي |
| `uv.lock` / `pnpm-lock.yaml` | Dependency lockfiles | ملفات قفل الحزم |

---

## 2. `backend/` — FastAPI service / خدمة الـ backend

**Role / الدور:** the entire server tier — FastAPI + SQLAlchemy 2 (async)
+ Alembic + the AI pipeline + pytest suite. / كل طبقة الـ server: API + DB
+ Migrations + Pipeline الـ AI + Tests.

```
backend/
├── app/        production code
├── alembic/    DB migrations
├── tests/      pytest suite
├── scripts/    ops + ML scripts
├── data/       backend-private data
├── Dockerfile
├── alembic.ini
└── .env.example
```

### 2.1 `backend/app/` — Python package

#### Top-level / المستوى الأول

| Path | English | العربية |
| --- | --- | --- |
| `app/main.py` | FastAPI factory: middleware, routers, lifespan, `/health`, `/metrics` | نقطة بداية الـ FastAPI: routers + middleware + lifecycle |

#### 2.1.1 `app/core/` — Infrastructure / البنية التحتية

**Role / الدور:** the primitives every module uses (config, DB, auth,
logging, encryption). No business logic. / الأساسيات اللي بيحتاجها كل module:
config + DB + auth + logging + encryption. مفيش business logic هنا.

| Path | English | العربية |
| --- | --- | --- |
| `core/config.py` | Pydantic `Settings` — reads .env, validates SECRET_KEY | إعدادات المشروع من ملف `.env` |
| `core/database.py` | Async SQLAlchemy engine + `get_session()` | محرك قاعدة البيانات + دالة الـ session |
| `core/deps.py` | FastAPI deps: `get_current_user`, `require_role`, rate-limit | dependencies للـ auth + الصلاحيات + الـ rate limit |
| `core/security.py` | JWT encode/decode + bcrypt hashing | تشفير JWT + هاش كلمات السر |
| `core/encryption.py` | Fernet-based PHI envelope (encrypt/decrypt) | تشفير بيانات المرضى (PHI) |
| `core/email.py` | aiosmtplib mailer — auto STARTTLS/SSL by port | إرسال الإيميلات (Gmail/Mailpit) |
| `core/exceptions.py` | Custom exceptions + global handlers | استثناءات مخصصة + معالجاتها |
| `core/logging.py` | structlog setup; adds request_id + user_id + trace_id | تسجيل لوجز منظّم بـ structlog |
| `core/metrics.py` | Prometheus counters/histograms | مؤشرات Prometheus للـ observability |
| `core/middleware.py` | Request-ID, security headers (HSTS/CSP), audit | حقن request_id + هيدرز الأمان |
| `core/sentry.py` | Prod-only Sentry init + PHI scrubber hook | تكامل Sentry للإنتاج + إخفاء بيانات المرضى |
| `core/tracing.py` | OpenTelemetry instrumentation (OTLP exporter) | تتبّع الـ requests بـ OpenTelemetry |

#### 2.1.2 `app/models/` — SQLAlchemy ORM / نماذج قاعدة البيانات

**Role / الدور:** declarative tables, 1:1 with Postgres schema. Queries live
elsewhere. / جداول قاعدة البيانات بـ SQLAlchemy. الاستعلامات في `service.py`.

| Path | English | العربية |
| --- | --- | --- |
| `models/base.py` | DeclarativeBase + created_at/updated_at mixin | الـ Base المشترك لكل الجداول |
| `models/_types.py` | Custom column types (EncryptedString for PHI) | أنواع أعمدة مخصصة (تشفير PHI) |
| `models/users.py` | User table (email, password_hash, role, lockout) | جدول المستخدمين |
| `models/patient_profile.py` | PatientProfile (DOB, allergies, conditions — encrypted) | بروفايل المريض (مشفّر) |
| `models/doctor_profile.py` | DoctorProfile (license, specialty, approval) | بروفايل الدكتور (الترخيص + التخصص) |
| `models/conversation.py` | Conversation (triage level, language, red flags) | جلسة المحادثة |
| `models/messages.py` | Message (encrypted content, tool calls, citations) | رسائل المحادثة (مشفّرة) |
| `models/auth_token.py` | AuthToken (email-verify + password-reset, hashed) | توكنات تفعيل الإيميل واستعادة الباسوورد |
| `models/refresh_token.py` | RefreshToken (rotatable long-lived JWT) | توكنات تجديد الجلسات |
| `models/handoff_summary.py` | HandoffSummary (SOAP markdown + state machine) | تحويل المريض للدكتور (SOAP) |
| `models/handoff_exports.py` | HandoffExport (FHIR/HL7 export audit) | سجلات تصدير FHIR/HL7 |
| `models/kb_chunk.py` | KbChunk (pgvector embedding + dedup hash) | فِقَر قاعدة المعرفة (RAG) |
| `models/vision_analysis.py` | VisionAnalysis (image analysis findings, encrypted) | نتائج تحليل الصور |
| `models/safety_assessment.py` | SafetyAssessment (hallucination + citation scores) | تقييم الأمان والهلوسات |
| `models/audit_log.py` | AuditLog (immutable, hash-chained for tamper detection) | سجل تدقيق غير قابل للتعديل |
| `models/notification_log.py` | NotificationLog (email/SMS delivery + status) | سجل الإيميلات والـ SMS |
| `models/support_ticket.py` | SupportTicket (user help requests) | تذاكر الدعم الفني |

#### 2.1.3 `app/clinical/` — Clinical KB / المحتوى الطبي

**Role / الدور:** YAML-driven medical knowledge — clinicians edit these
directly without touching Python. / محتوى طبي بـ YAML — الأطباء بيعدلوا
عليه مباشرة من غير ما يلمسوا الكود.

| Path | English | العربية |
| --- | --- | --- |
| `clinical/kb.py` | KB loader; validates YAML at startup, exposes `get_kb()` | محمّل قاعدة المعرفة (validates عند الـ startup) |
| `clinical/schemas.py` | Pydantic models — the YAML contracts | الـ schemas اللي بتـ validate الـ YAMLs |
| `clinical/chief_complaints/abdominal_pain.yaml` | Abdominal pain triage tree | شجرة فرز ألم البطن |
| `clinical/chief_complaints/back_pain.yaml` | Back pain triage tree | شجرة فرز آلام الظهر |
| `clinical/chief_complaints/chest_pain.yaml` | Chest pain (with cardiac red flags) | ألم الصدر (مع الـ red flags القلبية) |
| `clinical/chief_complaints/cough.yaml` | Cough triage tree | شجرة فرز الكحة |
| `clinical/chief_complaints/diarrhea.yaml` | Diarrhea / dehydration triage | فرز الإسهال والجفاف |
| `clinical/chief_complaints/fatigue.yaml` | Fatigue triage tree | فرز الإرهاق |
| `clinical/chief_complaints/fever.yaml` | Fever (child-adult split) | فرز الحمى (أطفال + بالغين) |
| `clinical/chief_complaints/headache.yaml` | Headache — thunderclap red flags | فرز الصداع — مع red flags الصداع المفاجئ |
| `clinical/chief_complaints/skin_rash.yaml` | Skin rash triage | فرز الطفح الجلدي |
| `clinical/chief_complaints/sore_throat.yaml` | Sore throat triage | فرز التهاب الحلق |
| `clinical/formulary/drugs.yaml` | Egyptian drug formulary (names, doses, interactions) | الأدوية المصرية (أسماء + جرعات + تفاعلات) |
| `clinical/specialties/general_practice.yaml` | GP intake template | قالب الاستقبال للممارس العام |
| `clinical/specialties/pediatrics.yaml` | Pediatrics intake template | قالب الاستقبال لطب الأطفال |
| `clinical/specialties/ent.yaml` | ENT intake template | قالب الاستقبال للأنف والأذن والحنجرة |

> See [`CLINICAL_KB.md`](CLINICAL_KB.md) for the editing guide /
> راجع `CLINICAL_KB.md` للتفاصيل الكاملة.

#### 2.1.4 `app/ai/` — AI pipeline / خط أنابيب الـ AI

##### `ai/agent/` — ReAct loop / حلقة ReAct

| Path | English | العربية |
| --- | --- | --- |
| `ai/agent/agent.py` | MedAgent ReAct loop: plan → tool → observe → answer (SSE) | الحلقة الأساسية للـ agent + بثّ SSE |
| `ai/agent/base.py` | Abstract Tool class (name, schema, async run) | الكلاس الأب لكل الـ tools |
| `ai/agent/registry.py` | ToolRegistry — generates OpenAI tool schemas | سجل الأدوات وتوليد schemas للـ LLM |
| `ai/agent/pii.py` | PII scrubber (names, phone, national-ID) | تنظيف بيانات الهوية قبل LLM |
| `ai/agent/tot_mode.py` | Tree-of-Thoughts: branches reasoning, picks best | استراتيجية شجرة الأفكار للتشخيص |
| `ai/agent/branches/pediatric.py` | Pediatric context overlay | سياق طب الأطفال |
| `ai/agent/branches/pregnancy.py` | Pregnancy context overlay | سياق الحمل |
| `ai/agent/prompts/system_ar.txt` | Arabic system prompt (PROMPT-V3a) | الـ system prompt بالعربي |
| `ai/agent/prompts/system_en.txt` | English system prompt (PROMPT-V3a) | الـ system prompt بالإنجليزي |
| `ai/agent/prompts/system_ar_pediatric.txt` | AR pediatric overlay | إضافة الأطفال بالعربي |
| `ai/agent/prompts/system_en_pediatric.txt` | EN pediatric overlay | إضافة الأطفال بالإنجليزي |
| `ai/agent/prompts/system_ar_pregnancy.txt` | AR pregnancy overlay | إضافة الحمل بالعربي |
| `ai/agent/prompts/system_en_pregnancy.txt` | EN pregnancy overlay | إضافة الحمل بالإنجليزي |
| `ai/agent/prompts/system_*.v1.bak.txt` | Backup of prompt v1 | نسخة احتياطية للـ prompt القديم |

##### `ai/llm/` — LLM providers / مزوّدو الـ LLM

| Path | English | العربية |
| --- | --- | --- |
| `ai/llm/base.py` | LLMProvider protocol (chat/stream/tool-calling) | الـ interface الموحّد لأي LLM |
| `ai/llm/openai_compat.py` | OpenAI-compatible provider (Groq/Gemini/OpenAI/OpenRouter) | مزوّد متوافق مع OpenAI API |
| `ai/llm/hf_inference.py` | HuggingFace Inference API provider | مزوّد HuggingFace |
| `ai/llm/vision_provider.py` | Vision-specific provider (image+text) | مزوّد تحليل الصور |

##### `ai/retrieval/` — RAG / استرجاع المعرفة

| Path | English | العربية |
| --- | --- | --- |
| `ai/retrieval/embeddings.py` | multilingual-e5-large embedder (1024-dim) | محوّل النص لمتجهات (AR+EN) |
| `ai/retrieval/vectorstore.py` | pgvector ANN search + upsert + dedup | تخزين/بحث المتجهات في Postgres |
| `ai/retrieval/chunker.py` | Recursive semantic chunker | تقسيم النصوص الطويلة |
| `ai/retrieval/retriever.py` | High-level: query → embed → search → rerank | الواجهة الأمامية للـ RAG |
| `ai/retrieval/reranker.py` | Cross-encoder reranker | تحسين ترتيب نتائج البحث |

##### `ai/safety/` — Safety gate / بوابة الأمان

| Path | English | العربية |
| --- | --- | --- |
| `ai/safety/post_llm_gate.py` | Hallucination detector + forbidden-phrase rewriter | كشف الهلوسات وإعادة صياغة العبارات الممنوعة |

##### `ai/tools/` — 14 agent tools / الـ 14 أداة للـ agent

| Path | English | العربية |
| --- | --- | --- |
| `ai/tools/clinical_lookup.py` | KB-grounded: free text → ChiefComplaint | يحوّل وصف المريض لشكوى رئيسية من KB |
| `ai/tools/triage_scorer.py` | Manchester Triage Scale (emergency/urgent/routine) | حساب درجة الطوارئ (مقياس مانشستر) |
| `ai/tools/red_flag_detector.py` | Strict emergency keyword + pattern detector | كاشف علامات الطوارئ الحقيقية |
| `ai/tools/assess_pediatric_safety.py` | Age-specific safety (doses, weight bands) | فحص أمان الأطفال (جرعات حسب العمر) |
| `ai/tools/assess_pregnancy_safety.py` | Trimester-specific safety (teratogen avoidance) | فحص أمان الحمل (تجنّب المُمَسِّخات) |
| `ai/tools/medication.py` | Drug-interaction + contraindication checker | كشف تفاعلات الأدوية |
| `ai/tools/mental_health.py` | PHQ-9 / GAD-7 screening administrator | فحص الاكتئاب والقلق |
| `ai/tools/retrieve_knowledge.py` | Wraps the RAG retriever for the agent | استدعاء RAG من الـ agent |
| `ai/tools/calibrate_uncertainty.py` | Confidence scoring + qualitative labels | حساب درجة الثقة في التشخيص |
| `ai/tools/format_soap.py` | Conversation → SOAP-note structure | تنسيق المحادثة بصيغة SOAP |
| `ai/tools/doctor_summary.py` | LLM-composed doctor handoff summary | ملخّص للطبيب يتم توليده بالـ LLM |
| `ai/tools/analyze_vision.py` | Image → structured vision findings JSON | تحليل الصور وإرجاع JSON منظّم |
| `ai/tools/tot_differential_diagnosis.py` | Tree-of-Thoughts differential diagnosis | تشخيص تفاضلي بأسلوب شجرة الأفكار |
| `ai/tools/verify_no_hallucination.py` | Verifier pass; flags ungrounded claims | بوابة التحقق من عدم وجود هلوسة |

##### `ai/nlp/` and others / متفرّقات

| Path | English | العربية |
| --- | --- | --- |
| `ai/nlp/language.py` | AR/EN detection + Arabic-diacritics normalization | اكتشاف اللغة وتطبيع التشكيل |
| `ai/mlflow_client.py` | ML experiment tracking client | عميل تتبع تجارب MLflow |

#### 2.1.5 `app/modules/` — Domain routers / الراوترز

**Role / الدور:** one folder per HTTP domain. Pattern per folder:
`router.py` (routes) + `schemas.py` (Pydantic I/O) + `service.py` (logic). /
كل domain له folder، ولكل folder ٣ ملفات: router + schemas + service.

##### `modules/auth/`

| Path | English | العربية |
| --- | --- | --- |
| `auth/router.py` | `/auth/register`, `/login`, `/refresh`, `/verify-email`, `/reset` | endpoints التسجيل والدخول والتفعيل |
| `auth/schemas.py` | Register/login/reset Pydantic models | schemas تسجيل ودخول |
| `auth/service.py` | Registration flow, email verification, password reset | منطق التسجيل والتفعيل |

##### `modules/conversations/`

| Path | English | العربية |
| --- | --- | --- |
| `conversations/router.py` | `/conversations` CRUD + pagination + GET messages | endpoints المحادثات |
| `conversations/chat.py` | SSE-streaming chat endpoint (wires agent + vision + verifier) | endpoint الـ chat بالـ SSE |
| `conversations/schemas.py` | ChatRequest, TriageEvent, MessageOut types | schemas الـ chat |
| `conversations/service.py` | Conversation CRUD + message persistence + triage state | منطق المحادثات وحفظ الرسائل |

##### `modules/handoff/`

| Path | English | العربية |
| --- | --- | --- |
| `handoff/router.py` | `/handoffs` + `/status` + `/review` + `/send` + `/pdf` | endpoints تحويل المريض |
| `handoff/schemas.py` | Handoff create/send/review/status payloads | schemas تحويل المريض |
| `handoff/service.py` | State machine, auto-claim, concurrency check | آلة الحالات + الـ claim التلقائي |
| `handoff/fhir_export.py` | Composes FHIR R4 Bundle | تصدير بصيغة FHIR R4 |
| `handoff/hl7_export.py` | Composes HL7 v2 ADT/MDM messages | تصدير بصيغة HL7 v2 |

##### `modules/doctors/`

| Path | English | العربية |
| --- | --- | --- |
| `doctors/router.py` | Doctor lookup, availability, profile | endpoints الأطباء |
| `doctors/schemas.py` | Doctor profile + availability schemas | schemas بيانات الطبيب |
| `doctors/service.py` | Doctor search, approval, specialty filter | البحث عن طبيب + الموافقة |

##### `modules/users/`

| Path | English | العربية |
| --- | --- | --- |
| `users/router.py` | `/users/me`, profile update, locale | endpoints بيانات المستخدم |
| `users/schemas.py` | User profile schemas | schemas بيانات المستخدم |
| `users/service.py` | User CRUD + avatar upload | تعديل البيانات ورفع الصورة |

##### `modules/notifications/`

| Path | English | العربية |
| --- | --- | --- |
| `notifications/router.py` | Notification preferences + history | endpoints الإشعارات |
| `notifications/schemas.py` | Preference + log schemas | schemas الإشعارات |
| `notifications/service.py` | Email scheduling + follow-up timers | جدولة الإيميلات والمتابعات |

##### `modules/admin/`

| Path | English | العربية |
| --- | --- | --- |
| `admin/router.py` | Admin dashboard, doctor approval, audit viewer | endpoints لوحة الأدمن |

##### `modules/support/`

| Path | English | العربية |
| --- | --- | --- |
| `support/router.py` | Support ticket endpoints | endpoints تذاكر الدعم |
| `support/service.py` | Ticket CRUD + escalation | منطق تذاكر الدعم |

#### 2.1.6 `app/common/` — Cross-cutting helpers / أدوات مساعدة مشتركة

| Path | English | العربية |
| --- | --- | --- |
| `common/audit.py` | `log_action()` — single entry point for audit trail | تسجيل أي عملية في سجل التدقيق |
| `common/audit_chain.py` | SHA-256 chains audit entries for tamper detection | ربط سجلات التدقيق بسلسلة هاش |
| `common/pagination.py` | Generic cursor-based pagination | pagination موحّد |
| `common/pdf.py` | PDF generation (handoff PDFs via ReportLab) | توليد PDF لتحويل المريض |

### 2.2 `backend/alembic/` — Database migrations / هجرات قاعدة البيانات

**Role / الدور:** every schema change is versioned. / كل تعديل على الـ schema له ملف.

| Path | English | العربية |
| --- | --- | --- |
| `alembic.ini` | Alembic config | إعدادات Alembic |
| `alembic/env.py` | Migration env — uses our Base.metadata for autogenerate | بيئة الهجرات وربطها بالـ ORM |
| `alembic/script.py.mako` | Template for new revisions | قالب توليد ملفات الهجرة |
| `alembic/README` | Alembic conventions for this repo | اصطلاحات الـ Alembic في المشروع |
| `alembic/versions/acb828cc2c29_initial.py` | Initial schema (users/conversations/messages/kb) | الجداول الأساسية الأولى |
| `alembic/versions/7774aebfe2b0_add_account_lockout_fields.py` | Account-lockout columns | أعمدة قفل الحسابات |
| `alembic/versions/T2_5_01_add_safety_assessments.py` | safety_assessments table | جدول تقييمات الأمان |
| `alembic/versions/T2_5_07_add_encrypted_columns.py` | Converts PHI columns to EncryptedString | تشفير أعمدة بيانات المرضى |
| `alembic/versions/T2_5_08_add_audit_chain.py` | previous_hash/current_hash on audit_logs | سلسلة الهاش لسجل التدقيق |
| `alembic/versions/T2_13_add_vision_analyses.py` | vision_analyses table | جدول تحليل الصور |
| `alembic/versions/T4_01_add_handoff_exports.py` | handoff_exports audit table | جدول تصديرات الـ handoff |
| `alembic/versions/T5_01_handoff_routing.py` | Doctor-routing columns on handoff_summaries | توجيه التحويلات للطبيب |
| `alembic/versions/0193202de7ca_add_secondary_indexes.py` | Performance indexes on hot queries | فهارس ثانوية للأداء |

### 2.3 `backend/tests/` — pytest suite / مجموعة الاختبارات

| Path | English | العربية |
| --- | --- | --- |
| `tests/conftest.py` | Shared pytest fixtures (test DB, client) | fixtures مشتركة |
| `tests/factories.py` | polyfactory test data builders | مولّدات بيانات للاختبارات |
| `tests/test_core.py` | Config + logging + metrics tests | اختبارات إعدادات النواة |
| `tests/test_models.py` | ORM relationships & constraints | اختبارات نماذج الـ ORM |
| `tests/test_deps.py` | Auth guard + rate limiter | اختبارات الـ dependencies |
| `tests/test_security.py` | Password + JWT round-trip | اختبارات الأمان |
| `tests/test_phi_encryption.py` | EncryptedString round-trip | اختبارات تشفير PHI |
| `tests/test_audit.py` | Audit log writer/reader | اختبارات سجل التدقيق |
| `tests/test_chunker.py` | Chunker boundary cases | اختبارات تقسيم النصوص |
| `tests/test_tools.py` | Tool registry + input validation | اختبارات أدوات الـ agent |
| `tests/test_branches.py` | Pediatric/pregnancy branch | اختبارات سياقات الأطفال والحمل |
| `tests/test_safety_gate.py` | Hallucination gate | اختبارات بوابة الأمان |
| `tests/test_e2e_conversation_to_handoff.py` | Full flow: chat → triage → handoff → export | اختبار شامل من الـ chat للـ handoff |
| `tests/test_fhir_hl7_export.py` | FHIR + HL7 structure | اختبارات تصدير FHIR و HL7 |
| `tests/test_handoff_routes.py` | Handoff state machine (≥25 cases) | اختبارات راوتر التحويلات |
| `tests/test_notifications.py` | Email scheduling (≥15 cases) | اختبارات الإيميلات |
| `tests/test_chat_sse.py` | SSE event order + safety short-circuit | اختبارات بثّ الـ SSE |
| `tests/test_admin.py` | Admin endpoints + audit dashboard | اختبارات الأدمن |
| `tests/test_users.py` | Profile CRUD + avatar | اختبارات بيانات المستخدم |
| `tests/test_rate_limit.py` | Rate-limit enforcement | اختبارات الـ rate limit |
| `tests/test_sentry_scrubber.py` | PHI scrubbing in Sentry events | اختبارات إخفاء PHI من Sentry |
| `tests/test_phase2.py` | Phase-2 milestone tests | اختبارات Phase 2 |
| `tests/test_vision_and_branches.py` | Vision + pediatric/pregnancy integration | اختبارات الرؤية + الفروع |
| `tests/auth/test_register.py` | Registration validation | اختبارات التسجيل |
| `tests/auth/test_login.py` | JWT issuance + invalid creds | اختبارات الدخول |
| `tests/auth/test_token.py` | Refresh + revoke + expiry | اختبارات تجديد التوكنات |
| `tests/auth/test_password.py` | Reset flow + hashing | اختبارات استعادة كلمة السر |
| `tests/eval/run_clinical_eval.py` | Clinical accuracy harness | إطار التقييم السريري |
| `tests/eval/clinical_cases.jsonl` | Labeled clinical cases | حالات سريرية مُصنّفة |
| `tests/eval/hallucination_cases.jsonl` | Hallucination test cases | حالات اختبار الهلوسة |
| `tests/eval/clinical_eval_results.json` | Last benchmark output | آخر نتائج تقييم |
| `tests/eval/specialized_tools/*.jsonl` | Per-tool eval sets | مجموعات تقييم لكل أداة |
| `tests/eval/vision/cases.jsonl` | Vision tool eval set | مجموعة تقييم تحليل الصور |

### 2.4 `backend/scripts/` — Backend scripts / سكريبتات الـ backend

| Path | English | العربية |
| --- | --- | --- |
| `backend/scripts/seed.py` | Seeds demo users + sample conversations | بيانات تجريبية للديمو |
| `backend/scripts/smoke_test.py` | One-minute health check | فحص صحي سريع |
| `backend/scripts/quick_test.py` | Fast regression subset | اختبارات تراجع سريعة |
| `backend/scripts/conversation_test.py` | E2E conversation simulator | محاكي محادثة كامل |
| `backend/scripts/create_gold_set.py` | Builds gold set for evaluation | بناء مجموعة مرجعية للتقييم |
| `backend/scripts/download_datasets.py` | Fetches external datasets | تنزيل مجموعات بيانات خارجية |
| `backend/scripts/eval.py` | Full evaluation harness | تقييم كامل |
| `backend/scripts/eval_specialized.py` | Pediatric/pregnancy evals | تقييم متخصص للأطفال والحمل |
| `backend/scripts/finetune_lora.py` | LoRA fine-tuning entry point | بدء عملية الـ fine-tuning |
| `backend/scripts/label_triage.py` | Manual triage labeling | تصنيف الفرز يدوياً |
| `backend/scripts/benchmark_models.py` | Compare LLM backends | مقارنة موديلات LLM |
| `backend/scripts/audit_verify.py` | Walk audit chain & report breaks | فحص سلسلة هاش التدقيق |

### 2.5 `backend/data/`

| Path | English | العربية |
| --- | --- | --- |
| `backend/data/medications/interactions.json` | Drug-drug interaction matrix | مصفوفة تفاعلات الأدوية |
| `backend/data/knowledge_base/seed/medical_seed.json` | KB seed corpus (~hundreds of chunks) | بذرة قاعدة المعرفة |

---

## 3. `frontend/` — Next.js 16 App Router

**Role / الدور:** the bilingual UI. SSE-streamed chat, role-based dashboards
(patient/doctor/admin), Cairo+Inter typography, Tailwind 4. / واجهة
ثنائية اللغة بـ Next.js 16 — chat بـ SSE + لوحات حسب الدور + تصميم Tailwind.

```
frontend/
├── app/         App Router pages
├── components/  UI primitives + feature components
├── lib/         API client + utils
├── store/       Zustand state
├── messages/    en.json / ar.json
├── src/i18n/    next-intl routing
├── test/        Vitest setup
├── e2e/         Playwright specs
└── (config files)
```

> ⚠️ **EN:** Read `frontend/AGENTS.md` before editing. Next.js 16 has
> breaking changes (`middleware.ts` → `proxy.ts`, async route params).
> **AR:** اقرأ `frontend/AGENTS.md` الأول — Next.js 16 فيه breaking changes.

### 3.1 `frontend/app/` — Pages / الصفحات

| Path | English | العربية |
| --- | --- | --- |
| `app/layout.tsx` | Root layout — fonts (Inter, Cairo, JetBrains Mono) | الـ layout الجذر + الخطوط |
| `app/globals.css` | Tailwind 4 + design tokens + RTL utilities | تنسيق عام + دعم RTL |
| `app/[locale]/layout.tsx` | Locale wrapper — sets lang/dir for RTL Arabic | غلاف اللغة (RTL/LTR) |
| `app/[locale]/page.tsx` | Landing/marketing home | الصفحة الرئيسية |
| `app/[locale]/(auth)/login/page.tsx` | Login form | صفحة تسجيل الدخول |
| `app/[locale]/(auth)/register/page.tsx` | Register form + role selector | صفحة إنشاء حساب |
| `app/[locale]/(auth)/forgot-password/page.tsx` | Password-reset request | طلب استعادة كلمة السر |
| `app/[locale]/(auth)/reset-password/page.tsx` | Token-validated reset form | إعادة تعيين كلمة السر |
| `app/[locale]/(auth)/verify-email/page.tsx` | Email verification landing | تفعيل الإيميل |
| `app/[locale]/(app)/layout.tsx` | App shell (sidebar + header + auth guard) | غلاف التطبيق الداخلي |
| `app/[locale]/(app)/chat/page.tsx` | Conversation list + new chat | قائمة المحادثات |
| `app/[locale]/(app)/chat/[id]/page.tsx` | Single conversation (SSE + triage + vision) | محادثة واحدة بـ SSE |
| `app/[locale]/(app)/history/page.tsx` | Past conversations with filters | سجل المحادثات السابقة |
| `app/[locale]/(app)/profile/page.tsx` | User profile, avatar, preferences | بيانات المستخدم |
| `app/[locale]/(app)/doctor/inbox/page.tsx` | Doctor inbox (triage-sorted) | صندوق الطبيب |
| `app/[locale]/(app)/doctor/handoff/[id]/page.tsx` | Handoff detail (workflow + notes + PDF) | تفاصيل التحويل |
| `app/[locale]/(app)/admin/dashboard/page.tsx` | Admin overview + metrics | لوحة الأدمن |
| `app/[locale]/(app)/admin/users/page.tsx` | User management | إدارة المستخدمين |
| `app/[locale]/(app)/admin/doctors/page.tsx` | Doctor approval queue | الموافقة على الأطباء |
| `app/[locale]/(app)/admin/audit/page.tsx` | Audit log viewer | عارض سجل التدقيق |
| `app/[locale]/(app)/admin/safety/page.tsx` | Safety assessment dashboard | لوحة تقييم الأمان |
| `app/[locale]/(app)/support/contact/page.tsx` | Support ticket form | تذكرة دعم جديدة |
| `app/[locale]/(app)/support/faq/page.tsx` | Frequently asked questions | الأسئلة الشائعة |

### 3.2 `frontend/components/`

#### `components/ui/` — Shadcn-style primitives / مكونات أساسية

| Path | English | العربية |
| --- | --- | --- |
| `ui/button.tsx` | Polymorphic button (variants, sizes, async loading) | زرار متعدد الأشكال |
| `ui/input.tsx` | Form input + label + error slot | حقل إدخال |
| `ui/card.tsx` | Card layout primitive | كرت أساسي |
| `ui/label.tsx` | Form label | تسمية حقل |
| `ui/markdown.tsx` | Safe Markdown renderer (RTL-aware) | عارض ماركداون يدعم RTL |
| `ui/toast.tsx` | Toast notification system | نظام الإشعارات الفورية |
| `ui/{button,input,card}.test.tsx` | Vitest unit tests | اختبارات الـ UI |

#### `components/auth/`

| Path | English | العربية |
| --- | --- | --- |
| `auth/auth-fields.tsx` | Reusable email/password fields + errors | حقول الإيميل والباسوورد |
| `auth/auth-shell.tsx` | Centered form layout | غلاف صفحات الـ auth |

#### `components/chat/`

| Path | English | العربية |
| --- | --- | --- |
| `chat/composer.tsx` | Message input + attachments + send | محرّر إرسال الرسائل |
| `chat/message-bubble.tsx` | One message (avatar, content, events, images) | فقاعة الرسالة |
| `chat/triage-panel.tsx` | Triage display (emergency/urgent/routine) | لوحة الفرز |
| `chat/DifferentialPanel.tsx` | Differential diagnosis + likelihood labels | لوحة التشخيص التفاضلي |
| `chat/ConfidenceBadge.tsx` | Inline confidence indicator | شارة درجة الثقة |
| `chat/WatchSignalsCard.tsx` | "علامات تستدعي طوارئ" card | كرت علامات الطوارئ |
| `chat/ImageUpload.tsx` | Image attachment + preview | رفع الصور |
| `chat/VisionModelSelector.tsx` | Multi-select vision-model picker | اختيار موديل تحليل الصور |
| `chat/VisionResultCard.tsx` | Structured vision findings | عرض نتائج تحليل الصور |
| `chat/VisionDisclaimerModal.tsx` | First-use vision disclaimer | إخلاء مسؤولية تحليل الصور |
| `chat/ComparisonGrid.tsx` | Side-by-side vision-compare layout | مقارنة عدة موديلات رؤية |
| `chat/DoctorSearchDialog.tsx` | Doctor lookup modal for handoff | البحث عن طبيب للتحويل |

#### `components/layout/`

| Path | English | العربية |
| --- | --- | --- |
| `layout/app-shell.tsx` | Authenticated layout wrapper | غلاف التطبيق الداخلي |
| `layout/sidebar.tsx` | Role-aware navigation | شريط جانبي حسب الدور |
| `layout/brand-logo.tsx` | Logo + wordmark | شعار التطبيق |
| `layout/language-switcher.tsx` | AR↔EN toggle | مبدّل اللغة |
| `layout/theme-toggle.tsx` | Dark/light/system theme | مبدّل الـ theme |
| `layout/theme-provider.tsx` | next-themes provider wrapper | غلاف theme provider |
| `layout/auth-hydrator.tsx` | SSR-safe auth state restoration | استرجاع حالة الـ auth في SSR |
| `layout/locale-html-sync.tsx` | Keeps html lang/dir in sync | مزامنة lang/dir |

#### `components/landing/` — Public marketing / صفحات تسويقية

| Path | English | العربية |
| --- | --- | --- |
| `landing/landing-nav.tsx` | Public nav (logo + Login/Register) | الـ nav للصفحة العامة |
| `landing/landing-footer.tsx` | Public footer | تذييل الصفحة العامة |
| `landing/hero.tsx` | Hero headline + CTA | قسم الـ Hero |
| `landing/feature-grid.tsx` | Capability cards | شبكة المميزات |
| `landing/how-it-works.tsx` | 3-step workflow | خطوات الاستخدام |
| `landing/triage-levels.tsx` | Emergency/urgent/routine explanation | شرح مستويات الفرز |
| `landing/safety-section.tsx` | Safety + limitations | قسم الأمان والحدود |
| `landing/social-proof.tsx` | Stats / testimonials | الأرقام والشهادات |
| `landing/final-cta.tsx` | Closing CTA panel | الـ CTA الختامي |

#### `components/emergency/`

| Path | English | العربية |
| --- | --- | --- |
| `emergency/SOSButton.tsx` | Floating emergency button + crisis resources | زرّ الطوارئ |

### 3.3 `frontend/lib/` — Utils & API client / الأدوات والـ API

| Path | English | العربية |
| --- | --- | --- |
| `lib/utils.ts` | `cn()` + general helpers | دوال مساعدة عامة |
| `lib/utils.test.ts` | Tests for utils | اختبارات الـ utils |
| `lib/motion.ts` | Framer Motion animation presets | إعدادات حركات Framer |
| `lib/api/client.ts` | HTTP client — JWT refresh + error handling | الـ HTTP client (JWT + معالجة الأخطاء) |
| `lib/api/auth.ts` | Typed wrappers for `/auth/*` | استدعاءات الـ auth |
| `lib/api/chat.ts` | `/conversations/*` + SSE stream parser | استدعاءات الـ chat + بثّ SSE |
| `lib/api/handoff.ts` | `/handoffs/*` + FHIR/HL7/PDF exports | استدعاءات التحويلات |
| `lib/api/admin.ts` | `/admin/*` endpoints | استدعاءات الأدمن |
| `lib/api/support.ts` | `/support/*` endpoints | استدعاءات الدعم |
| `lib/data/landing.ts` | Landing-page bilingual copy | نصوص الصفحة العامة |
| `lib/handoff/markdown.ts` | Handoff Markdown helpers | تنسيق ماركداون التحويلات |

### 3.4 `frontend/store/` — Zustand state / الحالة

| Path | English | العربية |
| --- | --- | --- |
| `store/auth.ts` | Auth store (user, tokens, actions) | store المصادقة |
| `store/auth.test.ts` | Unit test for auth store | اختبار store المصادقة |
| `store/chat.ts` | Chat state (list, messages, triage) | store المحادثات |

### 3.5 `frontend/e2e/` — Playwright tests / اختبارات End-to-End

| Path | English | العربية |
| --- | --- | --- |
| `e2e/helpers.ts` | Reusable login/setup fixtures | أدوات مشتركة للاختبارات |
| `e2e/auth.spec.ts` | Auth happy path | المسار الناجح للمصادقة |
| `e2e/auth-flow.spec.ts` | Full auth journey | رحلة مصادقة كاملة |
| `e2e/chat.spec.ts` | Chat interaction + SSE + triage | اختبار المحادثة والفرز |
| `e2e/handoff-flow.spec.ts` | Chat → handoff → export | تحويل المريض كاملاً |
| `e2e/admin.spec.ts` | Admin dashboard access | لوحة الأدمن |
| `e2e/multilingual.spec.ts` | AR/EN parity + RTL | تكافؤ اللغتين |

### 3.6 Frontend config files / ملفات الإعدادات

| Path | English | العربية |
| --- | --- | --- |
| `frontend/next.config.ts` | Next.js config (images, i18n, allowedDevOrigins) | إعدادات Next.js |
| `frontend/proxy.ts` | Dev proxy (tunnel-aware Location header fix) | proxy للتطوير + إصلاح الـ tunnel |
| `frontend/tsconfig.json` | TypeScript config | إعدادات TypeScript |
| `frontend/eslint.config.mjs` | ESLint flat config | إعدادات ESLint |
| `frontend/postcss.config.mjs` | PostCSS + Tailwind 4 | إعدادات PostCSS |
| `frontend/playwright.config.ts` | E2E runner config | إعدادات Playwright |
| `frontend/vitest.config.ts` | Unit test runner config | إعدادات Vitest |
| `frontend/components.json` | Shadcn component registry | سجل مكونات Shadcn |
| `frontend/vercel.json` | Vercel deployment hints | إعدادات نشر Vercel |
| `frontend/package.json` | Frontend deps (Next.js 16, React 19, …) | حزم الـ frontend |
| `frontend/Dockerfile` | Frontend image (Node 20 + pnpm) | صورة Docker للـ frontend |
| `frontend/.env.example` | Frontend env template | قالب الـ env |
| `frontend/README.md` | Frontend developer notes | ملاحظات للمطوّرين |
| `frontend/CLAUDE.md` | Re-exports `AGENTS.md` for Claude Code | تعليمات الـ AI agents |
| `frontend/AGENTS.md` | Next.js 16 breaking-changes warning | تحذيرات Next.js 16 |
| `frontend/test/setup.ts` | Vitest global setup | إعداد Vitest العام |
| `frontend/messages/en.json` | English i18n strings | نصوص الإنجليزي |
| `frontend/messages/ar.json` | Arabic i18n strings | نصوص العربي |
| `frontend/src/i18n/routing.ts` | next-intl routing config | إعدادات توجيه next-intl |
| `frontend/src/i18n/request.ts` | Request-time i18n context | سياق i18n وقت الطلب |
| `frontend/src/i18n/navigation.ts` | Typed Link/useRouter wrappers | غلاف Link/useRouter مطبوع |

---

## 4. `scripts/` — Repo-root ops scripts / سكريبتات تشغيلية

| Path | English | العربية |
| --- | --- | --- |
| `scripts/README.md` | When and how to run each script | متى وكيف تشغّل كل سكريبت |
| `scripts/seed_kb.py` | Loads `data/.../medical_seed.json` into pgvector | تحميل بذرة قاعدة المعرفة |
| `scripts/build_kb.py` | Builds full corpus from configured sources | بناء قاعدة المعرفة الكاملة |
| `scripts/build_curated_kb.py` | Curated, citation-checked corpus | بناء قاعدة معرفة منقّحة |
| `scripts/download_kb.py` | Downloads source documents (NICE/WHO/CDC) | تنزيل المصادر الطبية |
| `scripts/test_retrieval.py` | Sanity-checks vector search quality | اختبار جودة البحث المتجهي |
| `scripts/audit_verify.py` | Verifies the audit-log hash chain | فحص سلسلة هاش التدقيق |
| `scripts/verify_user.py` | CLI: flip is_email_verified or mint verify token | تفعيل مستخدم بدون SMTP |

---

## 5. `docs/` — Documentation / التوثيق

| Path | English | العربية |
| --- | --- | --- |
| `docs/INDEX.md` | Documentation navigation hub | مركز توجيه التوثيق |
| `docs/PROJECT_STRUCTURE.md` | **(this file)** bilingual codebase tour | **(الملف ده)** خريطة الكود |
| `docs/architecture.md` | High-level system design | تصميم النظام عالي المستوى |
| `docs/ai-pipeline.md` | Agent loop, tools, safety gates | شرح pipeline الـ AI |
| `docs/api-reference.md` | REST endpoint reference | مرجع الـ REST endpoints |
| `docs/development.md` | Local dev setup + workflows | إعداد بيئة التطوير |
| `docs/deployment.md` | Docker + production checklist | الإنتاج + قائمة المراجعة |
| `docs/safety.md` | Security, encryption, audit, threat model | الأمان والتشفير والتدقيق |
| `docs/CLINICAL_KB.md` | KB schema + editing guide + clinical sources | دليل تحرير المحتوى الطبي |
| `docs/DEPI-final-report.md` | Final DEPI delivery report | تقرير التسليم النهائي لـ DEPI |
| `docs/TEAM_PRESENTATION.md` | Team contribution map + defense notes | خريطة مساهمات التيم وملاحظات المناقشة |
| `docs/MANUAL_VERIFY.md` | Manual UI verification checklist | قائمة فحص يدوي للـ UI |
| `docs/conversation-flow.html` | Interactive conversation visualization | تصور تفاعلي لمسار محادثة |
| `docs/tasks/STATUS.md` | Phase completion status | حالة إنجاز المراحل |
| `docs/runbooks/audit_verification.md` | How to verify audit chain in prod | إجراء فحص سلسلة التدقيق |
| `docs/runbooks/key_rotation.md` | Encryption key rotation procedure | تدوير مفاتيح التشفير |

---

## 6. Other top-level dirs / مجلدات أخرى

| Path | English | العربية |
| --- | --- | --- |
| `data/knowledge_base/seed/medical_seed.json` | KB seed corpus (symptoms, conditions, citations) | بذرة قاعدة المعرفة الطبية |
| `infra/grafana/dashboards/medagent.json` | Grafana dashboard (RPS, latency, handoffs, errors) | لوحة Grafana للمراقبة |
| `pipeline/dags/kb_pipeline.py` | Airflow-style DAG (KB update cycle) | DAG تحديث قاعدة المعرفة |
| `notebooks/medagent_finetune_optimized.ipynb` | LoRA fine-tuning notebook (M1-friendly) | نوت بوك الـ fine-tuning |

---

## Architectural conventions / اصطلاحات معمارية

| Convention EN | اصطلاح بالعربي | Where / المكان |
| --- | --- | --- |
| Per-domain triplet: `router.py` + `schemas.py` + `service.py` | كل domain فيه 3 ملفات: راوتر + سكيمات + خدمة | `backend/app/modules/<domain>/` |
| YAML-driven clinical content | المحتوى الطبي مدفوع بـ YAML | `backend/app/clinical/` |
| Tool = subclass of `Tool` + register | كل أداة subclass من `Tool` + register | `backend/app/ai/tools/` |
| PHI columns use `EncryptedString` | أعمدة PHI مشفّرة بـ `EncryptedString` | `backend/app/models/_types.py` |
| Audit log is hash-chained | سجل التدقيق مربوط بسلسلة هاش | `backend/app/common/audit_chain.py` |
| Frontend components grouped by domain | مكونات الـ frontend مجمّعة حسب الـ domain | `frontend/components/{chat,auth,...}/` |
| i18n keys mirror UI structure | مفاتيح i18n مرآة لهيكل الواجهة | `frontend/messages/{en,ar}.json` |

---

## Cheat-sheet / دليل البحث السريع

| If you want to… / لو عاوز… | Open / افتح |
| --- | --- |
| Add a new chief complaint / تضيف شكوى رئيسية | `backend/app/clinical/chief_complaints/<name>.yaml` |
| Add an agent tool / تضيف أداة جديدة للـ agent | `backend/app/ai/tools/<tool>.py` + register في `chat.py` |
| Change a system prompt / تعدّل الـ system prompt | `backend/app/ai/agent/prompts/system_{ar,en}.txt` |
| Add an API endpoint / تضيف endpoint جديد | `backend/app/modules/<domain>/router.py` + `service.py` |
| Add a frontend page / تضيف صفحة جديدة | `frontend/app/[locale]/(app)/<path>/page.tsx` |
| Add a translation key / تضيف مفتاح ترجمة | `frontend/messages/{en,ar}.json` (الاتنين مع بعض) |
| Add a DB column / تضيف عمود لقاعدة البيانات | New Alembic revision في `backend/alembic/versions/` |
| Add a backend unit test / تضيف اختبار وحدة backend | `backend/tests/test_<area>.py` |
| Add an E2E test / تضيف اختبار E2E | `frontend/e2e/<flow>.spec.ts` |
| Wire a new metric / توصّل مؤشر Prometheus جديد | `backend/app/core/metrics.py` + استدعاء عند الـ call site |
| Verify the audit chain / تتأكد من سلسلة التدقيق | `uv run python backend/scripts/audit_verify.py` |
| Reset the demo environment / تعيد ضبط بيئة الديمو | `make reset && make seed-all` |
| Verify a user without SMTP / تفعّل مستخدم بدون إيميل | `docker compose exec backend /app/.venv/bin/python /app/scripts/verify_user.py <email>` |

---

## Numbers at a glance / الأرقام بشكل سريع

| Metric | Count |
| --- | --- |
| Backend Python modules / ملفات Python في الـ backend | ~115 |
| Backend tests / اختبارات الـ backend | ~305 (coverage ≥75%) |
| Agent tools / أدوات الـ agent | 14 |
| Chief complaints (YAML) / شكاوى رئيسية | 10 |
| Drug formulary entries / مدخلات الأدوية | dozens (Egyptian brand names) |
| Specialty templates / قوالب التخصصات | 3 (GP / Pediatrics / ENT) |
| Frontend pages / صفحات الـ frontend | 19 routes |
| Frontend E2E specs / اختبارات Playwright | 7 spec files |
| Database tables / جداول قاعدة البيانات | 15 (FHIR-aligned) |
| Languages / اللغات | Arabic (MSA + Egyptian) + English |

---

*Last reviewed / آخر مراجعة: 2026-05-24 — kept in sync with the on-disk tree. /
متزامن مع الكود الفعلي.*
