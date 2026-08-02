# MedAgent — Engineer Onboarding

> Phase F (F9): the 30-minute version. Skim this first, then `plan.md` for
> the architecture deep-dive.

## TL;DR

MedAgent is a bilingual (Arabic + English) medical triage assistant. FastAPI
backend with a ReAct agent + 13 clinical tools, Next.js 16 frontend, Postgres
with pgvector for retrieval-augmented grounding.

## Prerequisites

- Docker + Compose v2 (≥ 24.0)
- ~6 GB free disk for the images
- An LLM API key (OpenRouter / Groq / OpenAI all work)

## First boot (5 minutes)

```bash
git clone git@github.com:hossam7asan/MedAgent.git
cd MedAgent

# Backend env (LLM key + a few defaults)
cp backend/.env.example backend/.env
$EDITOR backend/.env          # fill LLM_API_KEY at minimum

# Generate a real SECRET_KEY (required, no default in any env):
python -c "import secrets; print(secrets.token_urlsafe(48))"
# paste the output as SECRET_KEY in backend/.env

make up                       # postgres, redis, mailpit, backend, frontend
make seed-all                 # users (admin/patient/doctor) + KB chunks
```

Open:

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:3000 | sign in with `patient@medagent.com` / `Patient123` |
| Backend Swagger | http://localhost:8000/docs | explore the API |
| Mailpit (dev SMTP) | http://localhost:8025 | catches all outbound mail |
| Prometheus metrics | http://localhost:8000/metrics | scrape from Grafana later |

## Layout

```
backend/
  app/
    main.py                  # FastAPI app + lifespan (Sentry, OTel, scheduler)
    core/                    # config, security, deps, logging, middleware, metrics
    ai/                      # agent (ReAct), tools, safety gates, retrieval
    modules/                 # one folder per domain (auth, users, handoff, ...)
    models/                  # SQLAlchemy 2.0 models
  alembic/                   # migrations
  tests/                     # pytest (run via `make test-backend`)
frontend/
  app/[locale]/(app|auth)/   # Next.js App Router with locale routing
  components/                # UI primitives + chat/handoff/admin features
  e2e/                       # Playwright specs
  messages/                  # next-intl translations (ar/en)
scripts/                     # ops scripts (seed_kb, audit_verify, ...)
infra/                       # Grafana dashboards (more here later)
docs/                        # architecture, API ref, this file
```

## Daily commands

```bash
make up            # background
make dev           # foreground (logs streaming)
make down          # stop
make reset         # ⚠️ wipes volumes (DB + KB)

make seed          # 3 test users (idempotent)
make seed-kb       # 21 medical chunks
make verify-kb     # KB stats

make format        # ruff format + eslint --fix
make lint          # ruff check + eslint
make test          # backend pytest + frontend vitest
```

## Conventions

- Backend Python lives in `backend/app/`. New domain modules go under
  `app/modules/<name>/{router, service, schemas, ...}`.
- Tests mirror the source tree under `backend/tests/`. Use the helpers in
  `tests/factories.py` instead of hand-rolling fixtures.
- Frontend pages are in `app/[locale]/(group)/…`. Use `next-intl` (`useTranslations`)
  for any user-facing text — never hard-code strings.
- AI agents and tools live in `backend/app/ai/`. Tools follow the `Tool`
  base class (`app/ai/agent/base.py`) and self-register via `ToolRegistry`.
- Migrations: `cd backend && uv run alembic revision -m "T<N>_<name>"`.

## Where to look first when something breaks

| Symptom | First file |
|---|---|
| Auth not working | `app/modules/auth/service.py` |
| Chat hangs / no tokens | `app/modules/conversations/chat.py` + agent logs |
| Doctor inbox missing items | `app/modules/handoff/service.py::list_doctor_inbox` |
| Lint or test red | `make format && make lint && make test` then read the first failure |
| Migration won't apply | `alembic history -v` + check `alembic/versions/` |
| Frontend white screen | browser console + `docker compose logs frontend` |

## Where to look for the bigger picture

- `plan.md` — the master spec (Phase 1-4 breakdown, every clinical tool described)
- `docs/architecture.md` — system design, data flow, sequence diagrams
- `docs/safety.md` — red flags, hallucination gate, triage logic
- `docs/DEPLOYMENT.md` — production runbook
- `docs/ai-pipeline.md` — agent + RAG details
- `~/.claude/plans/optimized-forging-melody.md` — the multi-phase improvement
  plan currently being executed (Phase A → F)

## Asking for help

- Sentry (if `SENTRY_DSN` set in your env) shows live errors with the PHI
  scrubber active — feel free to attach an event link.
- The `audit_logs` table is your friend — every state-changing call lands there.

Welcome aboard.
