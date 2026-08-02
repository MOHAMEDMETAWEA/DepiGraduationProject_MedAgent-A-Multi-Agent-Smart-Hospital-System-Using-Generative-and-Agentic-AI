# MedAgent — Development Guide

## Repository Structure

```
MedAgent/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── main.py             # Application entry point
│   │   ├── core/               # Cross-cutting concerns
│   │   ├── modules/            # Domain modules (auth, chat, admin, etc.)
│   │   ├── ai/                 # AI agent, tools, RAG, safety
│   │   ├── models/             # SQLAlchemy ORM models
│   │   └── common/             # Shared utilities
│   ├── tests/                  # Backend tests (pytest)
│   ├── alembic/                # Database migrations
│   └── scripts/                # Utility scripts
├── frontend/                   # Next.js application
│   ├── app/[locale]/           # Localized pages (App Router)
│   ├── components/             # React components
│   ├── lib/api/                # API client layer
│   ├── store/                  # Zustand state stores
│   ├── messages/               # Translation files (ar.json, en.json)
│   └── src/i18n/               # next-intl configuration
├── docs/                       # Documentation
├── data/                       # Datasets (gitignored)
├── notebooks/                  # ML experimentation
├── scripts/                    # Project-level scripts
├── docker-compose.yml          # Local development stack
├── Makefile                    # Convenience commands
└── plan.md                     # Master project specification
```

## Getting Started as a Developer

### 1. Clone and Install

```bash
git clone https://github.com/hossam7asan/medagent.git
cd medagent

# Backend
cd backend && uv sync && cd ..

# Frontend
cd frontend && pnpm install && cd ..
```

### 2. Set Up Environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your development values
```

### 3. Start Development

```bash
# Option A: Full Docker stack
make up

# Option B: Individual services
# Terminal 1 - Database & Redis
docker compose up postgres redis mailpit -d

# Terminal 2 - Backend
cd backend && uv run uvicorn app.main:app --reload

# Terminal 3 - Frontend
cd frontend && pnpm dev
```

## Backend Development

### Project Conventions

- **Module pattern:** Each module in `modules/` has `router.py`, `service.py`, `schemas.py`
- **Router:** HTTP concerns only — parse, validate, call service, format response
- **Service:** Business logic — never knows about HTTP
- **Repository pattern:** Database queries in service layer via SQLAlchemy
- **Async all the way:** All I/O operations are async

### Adding a New API Endpoint

1. Create schemas in `schemas.py`
2. Add business logic in `service.py`
3. Add route handler in `router.py`
4. Register router in `main.py`

Example:

```python
# modules/example/schemas.py
from pydantic import BaseModel

class ExampleResponse(BaseModel):
    message: str

# modules/example/service.py
async def get_message() -> str:
    return "Hello from example module"

# modules/example/router.py
from fastapi import APIRouter
from .schemas import ExampleResponse
from .service import get_message

router = APIRouter(prefix="/example", tags=["example"])

@router.get("/", response_model=ExampleResponse)
async def example_endpoint():
    msg = await get_message()
    return ExampleResponse(message=msg)
```

### Adding a New Agent Tool

1. Implement the `Tool` ABC in `ai/tools/`
2. Register it in the tool registry at application startup

```python
# ai/tools/my_tool.py
from ai.agent.base import Tool, ToolResult

class MyTool(Tool):
    name = "my_tool"
    description = "Description of what this tool does"

    async def run(self, **kwargs) -> ToolResult:
        # Tool logic
        return ToolResult(output={"result": "..."})

# Registration (in app startup or tool __init__)
from ai.agent.registry import registry
registry.register(MyTool())
```

### Database Migrations

```bash
cd backend

# Auto-generate from model changes
uv run alembic revision --autogenerate -m "add new table"

# Apply
uv run alembic upgrade head

# Create empty migration
uv run alembic revision -m "description"
```

### Testing

```bash
cd backend

# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_security.py

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run specific test
uv run pytest tests/auth/test_login.py::test_login_success
```

Test fixtures are defined in `tests/conftest.py`:
- `client` — Async HTTP test client
- `db_session` — Isolated database session
- `auth_headers` — Pre-authenticated request headers

## Frontend Development

### Project Conventions

- **Client components:** `"use client"` directive at top
- **State:** Zustand for auth, react-hook-form for forms
- **API:** All calls go through `lib/api/client.ts` (auto-refresh tokens)
- **i18n:** `useTranslations()` from next-intl for all user-facing text
- **Styling:** Tailwind v4 utility classes + shadcn/ui components

### Adding a New Page

1. Create page in `app/[locale]/...` directory
2. Add translations to `messages/ar.json` and `messages/en.json`
3. Add navigation entries if needed

### Adding a New API Client Method

```typescript
// lib/api/myModule.ts
import { apiRequest } from "./client";

export const myModuleApi = {
  getData: () => apiRequest("/my-module"),
  postData: (body: object) =>
    apiRequest("/my-module", { method: "POST", body }),
};
```

### Translation Workflow

```typescript
// Using translations in components
import { useTranslations } from "next-intl";
const t = useTranslations("section");

// With interpolation
t("greeting", { name: user.name });
```

Translation files:
- `messages/ar.json` — Arabic (default)
- `messages/en.json` — English

### Adding UI Components

Use shadcn/ui convention:

```tsx
// components/ui/my-component.tsx
import { cn } from "@/lib/utils";

interface MyComponentProps {
  className?: string;
  children: React.ReactNode;
}

export function MyComponent({ className, children }: MyComponentProps) {
  return (
    <div className={cn("base-styles", className)}>
      {children}
    </div>
  );
}
```

### Frontend Testing

```bash
cd frontend

# Run E2E tests
npx playwright test

# Run E2E with UI
npx playwright test --ui

# Run unit tests
npx vitest
```

## Code Quality

### Backend

```bash
cd backend
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run mypy app/           # Type check
```

### Frontend

```bash
cd frontend
pnpm lint                  # ESLint
```

### Pre-commit (Root)

```bash
pnpm lint                  # Run all linting
pnpm format                # Run all formatting
```

## Git Workflow

1. Create feature branch from `main`
2. Make changes with conventional commits
3. Run tests: `uv run pytest` (backend) + `npx playwright test` (frontend)
4. Run linting: `pnpm lint`
5. Open pull request

## Common Issues & Solutions

### Database connection refused

```bash
# Ensure PostgreSQL is running
docker compose up postgres -d

# Check connection
docker compose exec postgres pg_isready
```

### Migration errors

```bash
# Reset database (development only)
docker compose down -v
docker compose up postgres -d
uv run alembic upgrade head
```

### LLM API errors

- Verify `LLM_API_KEY` in `.env`
- Check `LLM_BASE_URL` for custom providers
- Test connectivity: `curl -H "Authorization: Bearer $LLM_API_KEY" $LLM_BASE_URL/models`

### Next.js build errors

```bash
# Clear cache
rm -rf frontend/.next
pnpm dev
```
