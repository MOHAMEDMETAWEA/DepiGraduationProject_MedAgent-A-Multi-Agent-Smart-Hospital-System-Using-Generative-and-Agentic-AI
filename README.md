# MedAgent 🩺

> Bilingual (Arabic + English) clinical triage assistant — **KB-grounded**, **safety-gated**, and **production-ready**.

[![Status](https://img.shields.io/badge/status-MVP%20ready-success)]()
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue)]()
[![Next.js](https://img.shields.io/badge/Next.js-16-black)]()
[![Tests](https://img.shields.io/badge/backend%20tests-305%20passing-success)]()
[![Coverage](https://img.shields.io/badge/coverage-%3E75%25-success)]()

> 📚 **For DEPI reviewers:** start with [docs/INDEX.md](docs/INDEX.md) for a guided tour.

---

## What MedAgent does

MedAgent helps Arabic-speaking patients triage symptoms in plain language, then hands off a structured clinical summary to a doctor.

It is **not** a "see a doctor" chatbot. The patient walks away from every conversation knowing:

1. **How serious** the situation is (Emergency / Urgent / Routine + numerical score).
2. **The 2–3 most likely possibilities** for what they have, with hedged language.
3. **What to do right now** — specific OTC drug name + Egyptian brand + dose, or specific first-aid action.
4. **When to escalate** — concrete watch signals tied to their complaint.

When the patient asks to forward to a doctor, the system generates a structured H&P + SOAP summary the clinician reads in 30 seconds.

⚠️ **Medical Disclaimer:** MedAgent is a triage and information assistant, not a diagnostic tool. Always consult a licensed physician for medical decisions.

---

## What's in the box

| Capability | Detail |
|---|---|
| 🗣 **Bilingual** | Arabic (MSA + Egyptian dialect) and English. Auto-detect, RTL UI. |
| 🧠 **KB-grounded agent** | 14 clinical tools + 10 chief-complaint protocols (NICE CKS / WHO IMCI sourced) + Egyptian drug formulary with brand names. |
| 🔁 **3-phase workflow** | Provisional differential → safety intake → grounded plan. No drugs in turn 1. |
| 🚨 **Emergency playbook** | 5-element response with hotline (123 EG ambulance, 16328 mental-health, 159 poison), first-aid step, what to tell the dispatcher. |
| 📷 **Multi-model vision** | Side-by-side comparison of Gemini, GPT-4o, Llama-4 Scout, Qwen-VL on a single image. |
| 👨‍⚕️ **Doctor handoff** | SOAP / FHIR R4 / HL7 v2 / PDF export. Inbox + status workflow for the receiving clinician. |
| 🛡 **Safety stack** | Red-flag detector, hallucination verifier, PHI encryption (Fernet AES-256), rate limiting, audit log. |
| 📊 **Observability** | Prometheus metrics + OpenTelemetry traces + Sentry (prod-only, with PHI scrubber) + Grafana dashboard. |

---

## Quick start (5 commands)

```bash
git clone git@github.com:hossam7asan/MedAgent.git
cd MedAgent
cp backend/.env.example backend/.env       # fill LLM_API_KEY, GROQ_API_KEY, etc.
make up                                     # postgres, redis, mailpit, backend, frontend
docker compose exec backend /app/.venv/bin/python -u /app/scripts/seed_kb.py
```

| Service | URL | Credentials |
|---|---|---|
| Patient app | http://localhost:3000 | `patient@medagent.com / Patient123` |
| Doctor inbox | http://localhost:3000 (after login as doctor) | `doctor@medagent.com / Doctor123` |
| Admin console | http://localhost:3000/admin | `admin@medagent.com / Admin123` |
| API docs (Swagger) | http://localhost:8000/docs | — |
| Mailpit (dev SMTP) | http://localhost:8025 | — |

---

## Tech stack

| Layer | Choice |
|---|---|
| **Backend** | FastAPI · SQLAlchemy 2 (async + asyncpg) · PostgreSQL 17 + pgvector · Redis · Alembic |
| **Frontend** | Next.js 16 (App Router + Turbopack) · React 19 · TypeScript · Tailwind v4 · shadcn/ui · next-intl · Zustand |
| **AI/LLM** | Groq (Llama-4 Scout / Qwen3 / Allam) · OpenAI (GPT-4o) · Gemini 2.5 Flash · OpenRouter (Qwen-VL) — pluggable per request |
| **AI infrastructure** | ReAct agent · 14 clinical tools · clinical_lookup (RAG-grounded) · multilingual-e5 embeddings · bge-reranker-v2-m3 |
| **Safety** | YAML rules + AI semantic detector for red flags · post-LLM hallucination verifier · drug interaction matrix · PHI encryption |
| **Vision** | Multi-provider abstraction: Gemini, GPT-4o, Llama-4 Scout, Qwen-VL — side-by-side compare mode |
| **Testing** | pytest (305 backend tests, ≥75% coverage) · Playwright (12+ e2e specs) · CI gate in GitHub Actions |
| **Observability** | Prometheus exporter · OpenTelemetry · Sentry (PHI scrubber) · Grafana dashboard JSON |
| **Ops** | Docker Compose · production Dockerfiles · Cloudflare Tunnel (dev sharing) |

---

## Repository map

```
medagent/
├── backend/
│   ├── app/
│   │   ├── ai/               # Agent, LLM providers, RAG, safety, 14 tools, prompts (AR + EN)
│   │   ├── clinical/         # Curated KB: chief complaints + Egyptian formulary + specialty templates
│   │   ├── core/             # Config, DB, auth, encryption, logging, Sentry
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── modules/          # Domain routers: auth, conversations, handoff, admin, …
│   │   └── main.py
│   ├── alembic/              # Migrations
│   ├── tests/                # 305 tests + factories
│   └── scripts/              # seed.py (users), seed_kb.py (vectors)
├── frontend/
│   ├── app/[locale]/         # Next.js App Router (locale-segmented)
│   │   ├── (app)/            # Authenticated app: chat, doctor, admin, history, profile
│   │   └── (auth)/           # Login, register, forgot-password
│   ├── components/           # UI primitives + chat + handoff + landing
│   ├── lib/, store/, src/    # API client, Zustand store, i18n config
│   ├── e2e/                  # Playwright specs
│   ├── proxy.ts              # Forwarded-host middleware (replaces middleware.ts in Next.js 16)
│   └── next.config.ts        # allowedDevOrigins for tunnel hosts
├── docs/                     # Architecture, API, deployment, AI pipeline, safety, runbooks
├── infra/grafana/            # Pre-built Grafana dashboard
├── docker-compose.yml        # Local dev stack
├── docker-compose.prod.yml   # Production overlay
└── Makefile                  # `make up`, `make seed-kb`, `make test`, etc.
```

---

## Documentation

| Doc | What's inside |
|---|---|
| 📘 [docs/INDEX.md](docs/INDEX.md) | **Start here** — guided navigation for reviewers |
| 🎓 [docs/DEPI-final-report.md](docs/DEPI-final-report.md) | **Final delivery report** for DEPI program |
| 🏛 [docs/architecture.md](docs/architecture.md) | System design, layers, data flow |
| 🤖 [docs/ai-pipeline.md](docs/ai-pipeline.md) | Agent, tools, RAG, safety gates |
| 📖 [docs/CLINICAL_KB.md](docs/CLINICAL_KB.md) | How the medical content is curated + extended |
| 🛡 [docs/safety.md](docs/safety.md) | Red flags, hallucination gate, triage, PHI |
| 🔌 [docs/api-reference.md](docs/api-reference.md) | Endpoint reference (also see Swagger at /docs) |
| 🚀 [docs/deployment.md](docs/deployment.md) | Docker, CI/CD, production checklist |
| 🧑‍💻 [docs/development.md](docs/development.md) | Local setup, testing, code conventions |
| ✅ [docs/MANUAL_VERIFY.md](docs/MANUAL_VERIFY.md) | Manual smoke-test checklist for a PR/release |
| 📒 [ONBOARDING.md](ONBOARDING.md) | First-week onboarding for new contributors |

---

## Project status

| Phase | Status |
|---|---|
| **Phase 1 — Foundation** (auth, DB, Docker, CI) | ✅ Done |
| **Phase 2 — AI Core** (ReAct agent, 14 tools, streaming) | ✅ Done |
| **Phase 2.5 — Safety + UX polish** (hallucination gate, glassmorphic UI, optimistic mutations) | ✅ Done |
| **Phase 3 — Test coverage** (305 backend + 12 Playwright, CI gate ≥75%) | ✅ Done |
| **Phase 4 — Security hardening** (vision SSRF, DB pool tuning, CORS audit) | ✅ Done |
| **Phase 5 — Production readiness** (prod Dockerfiles, Sentry, Grafana, runbooks) | ✅ Done |
| **Phase 6 — Clinical KB v1** (10 chief complaints + Egyptian formulary + intake-first workflow) | ✅ Done |
| **Phase 7 — Pilot & validation** (clinical reviewer sign-off, real-clinic pilot) | 🟡 Next |

---

## License

MIT © 2026 Hossam Hassan
