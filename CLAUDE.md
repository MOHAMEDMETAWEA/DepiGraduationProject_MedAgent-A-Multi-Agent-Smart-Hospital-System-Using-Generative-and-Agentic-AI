# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in the MedAgent repository.

## Project Context

MedAgent is a bilingual (Arabic + English) AI medical triage assistant with:
- FastAPI backend under `backend/`
- Next.js frontend under `frontend/`
- Docker-based local stack via `docker-compose.yml` and `Makefile`

## Repository Layout

- `backend/` — FastAPI app, domain modules, AI pipeline, Alembic migrations, tests
- `frontend/` — Next.js 16 + React 19 app with locale routing and UI
- `docs/` — architecture and project documentation
- `scripts/` — utility and ops scripts
- `data/` / `notebooks/` — datasets and ML experimentation artifacts

## Working Conventions

- Treat this repository root as the working directory.
- Prefer project scripts/targets over ad-hoc commands when available.
- Keep changes scoped; avoid unrelated refactors.
- For medical logic and safety behavior, preserve conservative defaults and red-flag escalation paths.

## Common Commands

From repository root:

- `make dev` — start docker services in foreground
- `make up` — start docker services in background
- `make down` — stop docker services
- `make reset` — reset docker volumes and restart services

Service URLs (docker local):
- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- Mailpit: http://localhost:8025

Backend (`backend/`):
- `uv run uvicorn app.main:app --reload`
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format .`

Frontend (`frontend/`):
- `pnpm dev`
- `pnpm build`
- `pnpm lint`

Monorepo/root scripts:
- `pnpm lint`
- `pnpm format`
- `pnpm build`

## Backend Notes

- Entry point: `backend/app/main.py`
- Domain routes live under `backend/app/modules/*/router.py`
- AI pipeline lives under `backend/app/ai/` (agent, llm, retrieval, safety, tools)
- Migrations: `backend/alembic/` + `backend/alembic.ini`

## Knowledge Base (RAG)

The agent grounds responses against `kb_chunks` (pgvector). After a fresh
`make up` on a clean volume the table is empty — seed it before running
the agent in any demo:

```bash
docker compose exec backend /app/.venv/bin/python -u /app/scripts/seed_kb.py
docker compose exec backend /app/.venv/bin/python -u /app/scripts/seed_kb.py --verify
```

See `scripts/README.md` for editing the corpus, smoke-testing retrieval,
and the production ingestion path.

## Frontend Notes

- Uses Next.js App Router and `next-intl` locale routing under `frontend/app/[locale]/`
- UI includes Base UI/shadcn-style components and Tailwind v4
- State uses Zustand where needed

## Environment

- Python dependencies are managed with `uv` (`pyproject.toml` + `uv.lock`)
- JS dependencies are managed with `pnpm` (`package.json`, `pnpm-workspace.yaml`)
- Configure backend environment variables via `backend/.env` (from `backend/.env.example`)
