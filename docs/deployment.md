# MedAgent — Deployment Guide

## Local Development

### Prerequisites

- Python **3.11+** (managed via `uv`)
- Node.js **20+** and **pnpm 9+**
- Docker & Docker Compose

### Quick Start

```bash
# Clone and set up
git clone https://github.com/hossam7asan/medagent.git
cd medagent

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your values (LLM API key, etc.)

# Start all services
make up
# Or: docker compose up -d
```

### Service URLs (Docker local)

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API Docs | http://localhost:8000/docs |
| Mailpit (dev SMTP) | http://localhost:8025 |

### Makefile Commands

| Command | Action |
|---|---|
| `make dev` | Start services in foreground |
| `make up` | Start services in background |
| `make down` | Stop all services |
| `make build` | Build Docker images |
| `make reset` | Stop, remove volumes, restart |

## Backend Development (Without Docker)

```bash
cd backend

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start dev server
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest

# Lint & format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy app/
```

## Frontend Development (Without Docker)

```bash
cd frontend

# Install dependencies
pnpm install

# Start dev server
pnpm dev

# Build for production
pnpm build

# Lint
pnpm lint

# Run E2E tests
npx playwright test
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `VECTOR_STORE_URL` | No | Same as DB | Vector store connection |
| `REDIS_URL` | Yes | — | Redis connection string |
| `SECRET_KEY` | Yes | — | JWT signing secret |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `30` | Refresh token lifetime |
| `LLM_PROVIDER` | Yes | — | `openrouter`, `groq`, `hf` |
| `LLM_API_KEY` | Yes | — | API key for LLM provider |
| `LLM_MODEL` | No | `qwen/qwen-2.5-7b-instruct` | Model identifier |
| `LLM_BASE_URL` | No | — | Custom LLM API base URL |
| `VERIFIER_MODEL` | No | — | Model for hallucination verification |
| `SMTP_HOST` | No | `localhost` | SMTP server |
| `SMTP_PORT` | No | `1025` | SMTP port |
| `PHI_ENCRYPTION_ENABLED` | No | `false` | Encrypt patient health data |
| `DATA_ENCRYPTION_KEY` | Cond | — | Fernet key (required when encryption on) |
| `CORS_ORIGINS` | No | `*` | Allowed CORS origins |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `SENTRY_DSN` | No | — | Error monitoring DSN |

## Production Deployment

### Recommended Architecture

```
┌─────────┐     ┌─────────┐     ┌──────────────┐
│ Vercel  │────▶│ Railway │────▶│ Neon/Supabase │
│(Next.js)│     │(FastAPI)│     │ (PostgreSQL)  │
└─────────┘     └────┬─────┘     └──────────────┘
                     │
              ┌──────┴──────┐
              │  OpenRouter │
              │  (LLM API)  │
              └─────────────┘
```

### Frontend (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel --prod

# Set environment variables in Vercel dashboard:
# - NEXT_PUBLIC_API_URL = https://your-backend.railway.app/api/v1
```

### Backend (Railway)

1. Create a new Railway project
2. Connect your GitHub repository
3. Set root directory to `backend/`
4. Configure environment variables (see above)
5. Railway auto-detects the `Dockerfile` or Python build

### Database (Neon/Supabase)

1. Create a new project
2. Enable `pgvector` extension
3. Copy the connection URL
4. Run Alembic migrations: `uv run alembic upgrade head`
5. Set `DATABASE_URL` in backend environment

### Database Migrations

```bash
# Create a new migration
cd backend
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1
```

Migrations run automatically on startup in non-production environments.

### Vector Store Setup

The project uses `pgvector` within PostgreSQL. The vector extension is enabled in the initial migration.

```bash
# Build the knowledge base (one-time)
cd backend
uv run python scripts/build_kb.py
```

## Monitoring & Observability

### Health Checks

- **Liveness:** `GET /api/v1/health`
- **Readiness:** `GET /api/v1/health/ready` (checks DB connectivity)
- **Version:** `GET /api/v1/version`

### Metrics

Prometheus metrics exposed at `/metrics` (internal network only):
- Request counts and latencies
- LLM call durations
- Safety pipeline statistics
- Error rates

### Logging

Structured JSON logging via `structlog`. In production, logs can be forwarded to:
- Datadog / Grafana Loki
- ELK stack
- CloudWatch (if on AWS)

### Error Monitoring

Set `SENTRY_DSN` in production for automatic error tracking.

## Security Checklist

- [ ] Set strong `SECRET_KEY` (min 32 chars)
- [ ] Enable `PHI_ENCRYPTION_ENABLED=true` and set `DATA_ENCRYPTION_KEY`
- [ ] Set `CORS_ORIGINS` to your frontend domain only
- [ ] Use HTTPS in production
- [ ] Rotate JWT secrets periodically
- [ ] Enable rate limiting (via Redis-backed slowapi)
- [ ] Review admin account access
- [ ] Monitor audit log hash chain integrity via `/admin/audit-verify`
