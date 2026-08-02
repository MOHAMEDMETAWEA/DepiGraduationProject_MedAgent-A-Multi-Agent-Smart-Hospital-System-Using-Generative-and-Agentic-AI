# MedAgent — Documentation Index

> **For DEPI reviewers:** follow the suggested reading order below. Estimated total reading time: **30–45 min**.

---

## 🎯 Suggested reading order

### 1. Get the elevator pitch (5 min)
- [`README.md`](../README.md) — what MedAgent does, tech stack, quick start
- [`DEPI-final-report.md`](DEPI-final-report.md) — **the official delivery report** (Arabic, comprehensive)

### 2. Understand the architecture (15 min)
- [`architecture.md`](architecture.md) — layers, modules, data flow, DB tables
- [`ai-pipeline.md`](ai-pipeline.md) — ReAct agent loop, tool registry, RAG stages
- [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) — file-by-file codebase tour (every folder + file explained)

### 3. Look at the clinical substance (10 min)
- [`CLINICAL_KB.md`](CLINICAL_KB.md) — how medical content is curated + extended
- [`safety.md`](safety.md) — red flags, hallucination gate, PHI encryption

### 4. Operate or extend it (15 min)
- [`api-reference.md`](api-reference.md) — endpoint reference (interactive at `/docs`)
- [`development.md`](development.md) — local setup, testing, conventions
- [`deployment.md`](deployment.md) — production stack, CI/CD, runbooks
- [`MANUAL_VERIFY.md`](MANUAL_VERIFY.md) — manual smoke-test checklist
- [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) — **live defense script** (intro + 3 demo flows + Q&A) ⭐

### 5. Operational runbooks
- [`runbooks/`](runbooks/) — incident playbooks (rate-limit, key rotation, …)

---

## 📂 What's in each doc

| File | One-liner | Audience |
|---|---|---|
| **[`../README.md`](../README.md)** | Project overview + 5-command quick start | Everyone |
| **[`DEPI-final-report.md`](DEPI-final-report.md)** | Final delivery report — problem, solution, tech, architecture, testing, deployment | DEPI evaluators |
| **[`architecture.md`](architecture.md)** | High-level system design — backend layers, frontend routing, DB schema, communication patterns | Engineers |
| **[`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)** | Codebase tour — every folder's role + one-line purpose for every file | New contributors, graders |
| **[`ai-pipeline.md`](ai-pipeline.md)** | ReAct agent loop, the 14 tools, RAG retrieval + reranking, multi-stage safety gates | AI/ML reviewers |
| **[`CLINICAL_KB.md`](CLINICAL_KB.md)** | YAML schema for chief complaints + drug formulary + specialty templates; how to add a new complaint | Clinical content authors |
| **[`safety.md`](safety.md)** | Red-flag detection, hallucination verifier, triage scoring, PHI handling, encryption | Safety / security reviewers |
| **[`api-reference.md`](api-reference.md)** | Auth, conversations, chat SSE, handoff, admin, vision — request / response shapes | Frontend devs, integrators |
| **[`deployment.md`](deployment.md)** | Local docker-compose, production overlay, GitHub Actions CI, environment matrix | DevOps |
| **[`development.md`](development.md)** | Tooling (uv, pnpm), code style, testing, debugging, common tasks | New contributors |
| **[`MANUAL_VERIFY.md`](MANUAL_VERIFY.md)** | Step-by-step manual UI checklist for PR / release verification | Reviewers |
| **[`../ONBOARDING.md`](../ONBOARDING.md)** | First-week onboarding for a new team member | New hires |

---

## 🧭 By role

### "I'm the DEPI grader, what should I read?"
1. [README.md](../README.md) (5 min) — get the pitch
2. [DEPI-final-report.md](DEPI-final-report.md) (20 min) — comprehensive Arabic report
3. [architecture.md](architecture.md) (10 min) — verify technical depth
4. Browse [docs/](.) for any specific deep-dive

### "I'm a developer joining the team"
1. [ONBOARDING.md](../ONBOARDING.md) — first-week setup
2. [development.md](development.md) — daily workflow
3. [architecture.md](architecture.md) — mental model
4. [api-reference.md](api-reference.md) — when you start writing UI

### "I'm a clinician evaluating the AI"
1. [README.md](../README.md) — what the system claims to do
2. [CLINICAL_KB.md](CLINICAL_KB.md) — see the actual evidence sources used (NICE CKS / WHO IMCI)
3. [safety.md](safety.md) — red-flag rules + escalation logic
4. [MANUAL_VERIFY.md](MANUAL_VERIFY.md) — try the system yourself

### "I need to deploy this"
1. [deployment.md](deployment.md) — production overlay
2. [runbooks/](runbooks/) — incident response
3. `docker-compose.prod.yml` — entry point
4. `infra/grafana/dashboards/medagent.json` — import into Grafana

---

## 🔗 External references

| What | Where |
|---|---|
| GitHub repo | https://github.com/hossam7asan/MedAgent |
| API docs (Swagger) | `http://localhost:8000/docs` (running locally) |
| Issue tracker | GitHub Issues |
| CI pipeline | `.github/workflows/` |

---

## 📊 Project numbers (at a glance)

| Metric | Value |
|---|---|
| Backend files | 115 Python modules |
| Frontend pages | 19 routes (App Router) |
| AI tools registered | 14 |
| Curated chief complaints | 10 (adult primary care, NICE/WHO sourced) |
| Drug formulary entries | 10 (Egyptian brand names + pediatric weight-based dosing) |
| Specialty intake templates | 3 (GP, Pediatrics, ENT) |
| Backend tests | 305 (≥75% coverage) |
| Frontend E2E tests | 12+ Playwright specs |
| Database tables | 15 (FHIR-aligned) |
| Supported languages | Arabic (MSA + Egyptian) + English |

---

_Last updated: 2026-05-24_
