.PHONY: dev up down build reset
.PHONY: seed seed-kb seed-all verify-kb test test-backend test-frontend lint lint-backend lint-frontend format format-backend format-frontend migrate

# ── Docker lifecycle ────────────────────────────────────

dev:
	docker compose up

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

reset:
	docker compose down -v
	docker compose up -d

# ── Seeding ─────────────────────────────────────────────

# Seed test users: admin@medagent.com / patient@medagent.com / doctor@medagent.com
# (passwords: Admin123 / Patient123 / Doctor123) — idempotent
seed:
	docker compose exec -w /app/backend -e PYTHONPATH=/app/backend backend /app/.venv/bin/python -u scripts/seed.py

# Seed medical knowledge base into pgvector (21 chunks: 11 en + 10 ar)
seed-kb:
	docker compose exec backend /app/.venv/bin/python -u /app/scripts/seed_kb.py

verify-kb:
	docker compose exec backend /app/.venv/bin/python -u /app/scripts/seed_kb.py --verify

# Convenience: seed both users + knowledge base
seed-all: seed seed-kb verify-kb

# ── Testing ─────────────────────────────────────────────

test: test-backend test-frontend

test-backend:
	cd backend && uv run python -m pytest tests/ -v --tb=short

test-frontend:
	docker compose exec -w /app/frontend frontend pnpm exec vitest --run

# ── Linting ─────────────────────────────────────────────

lint: lint-backend lint-frontend

lint-backend:
	cd backend && uv run ruff check .

typecheck-backend:
	cd backend && uv run mypy app --ignore-missing-imports || echo "Type check completed with issues (see above)"

lint-frontend:
	docker compose exec -w /app/frontend frontend pnpm lint

# ── Formatting ──────────────────────────────────────────

format: format-backend format-frontend

format-backend:
	cd backend && uv run ruff format .
	cd backend && uv run ruff check . --fix

format-frontend:
	docker compose exec -w /app/frontend frontend pnpm format

# ── Database ────────────────────────────────────────────

migrate:
	cd backend && uv run alembic upgrade head

migrate-down:
	cd backend && uv run alembic downgrade -1

# ── Audit / Safety ──────────────────────────────────────

audit-verify:
	cd backend && uv run python ../scripts/audit_verify.py