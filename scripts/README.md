# MedAgent Scripts

Operational scripts that sit outside the FastAPI app — used to seed data,
verify infrastructure, and run one-off jobs against a running stack.

## `seed_kb.py` — Seed the medical knowledge base

Populates the `kb_chunks` table (pgvector) with the curated demo corpus at
`data/knowledge_base/seed/medical_seed.json`. Required before the agent can
ground responses with citations or before the post-LLM safety gate has any
sources to verify against.

### What it does

1. Reads 21 hand-curated medical chunks (English + Arabic) covering
   emergency, urgent, routine, and specialized (peds/pregnancy) scenarios.
2. Embeds each chunk with `intfloat/multilingual-e5-large` (1024-dim) in
   batches of 4 to avoid OOM on small containers.
3. Upserts into `kb_chunks` under the source tag `medagent_seed_v1`,
   deduping by content hash so re-runs are safe.

All chunks are paraphrased from publicly accessible patient-education
material (MedlinePlus, WHO, CDC, AAP) with citations preserved in metadata.

### Running it (Docker)

The backend container has the ML stack pre-installed in `/app/.venv`.

```bash
# 1. Make sure the stack is up
make up

# 2. Run the seed (uses the venv python explicitly)
docker compose exec backend /app/.venv/bin/python -u /app/scripts/seed_kb.py

# 3. Confirm it landed
docker compose exec backend /app/.venv/bin/python -u /app/scripts/seed_kb.py --verify
```

Expected verification output:

```
KB rows total              : 21
Rows from seed source      : 21
Seed by language           : {'ar': 10, 'en': 11}
Embedding dim              : 1024
```

> **Tip:** the `-u` flag forces unbuffered stdout so you see embedding
> progress in real time. Without it, the model load + first encoding pass
> looks like a hang.

### Running it (local, outside Docker)

```bash
cd backend
uv run python ../scripts/seed_kb.py
```

The script connects to `DATABASE_URL` from `backend/.env`, so `make up`
must have started Postgres first.

### Flags

| Flag | What it does |
|---|---|
| (none) | Embed + upsert. Idempotent — skips chunks already present. |
| `--dry-run` | Show what would be ingested. No DB writes, no model load. |
| `--clear` | Delete existing rows for `medagent_seed_v1` before inserting. Use after editing the JSON to start clean. |
| `--verify` | Print current DB stats only. Useful to confirm seed state before a demo. |
| `--file PATH` | Use an alternate JSON corpus (same schema). |

### Editing the corpus

Edit `data/knowledge_base/seed/medical_seed.json` and re-run with `--clear`:

```bash
docker compose exec backend /app/.venv/bin/python -u /app/scripts/seed_kb.py --clear
```

Each chunk needs:

```jsonc
{
  "id": "stable-slug",
  "category": "emergency | urgent | routine | specialized",
  "language": "en | ar",
  "source": "MedlinePlus",            // upstream source name
  "source_url": "https://...",        // canonical URL
  "section_title": "Heart Attack — Warning Signs",
  "content": "Long-form medical text (200–500 words) …"
}
```

### Production sourcing (next step)

This seed is for **demo and development**. Production should ingest from
real APIs — see `scripts/build_kb.py` and `scripts/download_kb.py` which
target MedlinePlus, WHO, and Egyptian MoH endpoints with proper licensing.

---

## `test_retrieval.py` — Smoke-test the RAG path

Hits the same `Retriever` the agent uses with five representative queries
(English + Arabic, varying urgency) and prints the top-3 chunks per query.
Used to confirm that a freshly seeded KB is searchable end-to-end.

```bash
docker compose exec backend /app/.venv/bin/python -u /app/scripts/test_retrieval.py
```

First run downloads the cross-encoder reranker (`BAAI/bge-reranker-v2-m3`,
~600 MB) — subsequent runs are fast.

---

## Other scripts

- `audit_verify.py` — replays the hash-chained audit log to detect tampering.
- `build_kb.py` / `download_kb.py` — production KB pipeline (MedlinePlus +
  WHO + MoH). Out of scope for the demo path.
- `build_curated_kb.py` — alternative curated builder kept for reference.
