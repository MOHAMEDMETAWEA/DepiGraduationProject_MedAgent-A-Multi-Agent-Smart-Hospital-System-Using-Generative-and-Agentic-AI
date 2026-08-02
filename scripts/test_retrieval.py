#!/usr/bin/env python3
"""Quick smoke-test for the RAG retrieval path.

Hits the same retriever the agent uses and prints the top-K chunks for a
short list of representative queries (English + Arabic, emergency + routine).
Used to confirm a freshly-seeded KB is actually searchable.

Usage:
  docker compose exec backend /app/.venv/bin/python -u /app/scripts/test_retrieval.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

QUERIES = [
    ("en", "I have severe chest pain that radiates to my left arm"),
    ("en", "My 2-month-old has a fever of 38.5"),
    ("ar", "عندي صداع شديد ومفاجئ مش زي اللي بيجيلي عادة"),
    ("ar", "أنا حامل وعندي نزيف ايه أعمل"),
    ("en", "I have a runny nose and mild cough for two days"),
]


async def main() -> int:
    from app.ai.retrieval.embeddings import Embedder
    from app.ai.retrieval.vectorstore import VectorStore
    from app.core.database import get_session

    # Smoke-test the ANN path only (embedder + pgvector cosine search).
    # The reranker is exercised in the live agent flow — loading it here
    # alongside the embedder OOMs small dev containers. The agent flow
    # gets its own memory budget at request time.
    embedder = Embedder()
    print(f"Embedder ready (dim={embedder.dimension})\n")

    async with get_session() as session:
        store = VectorStore(session)
        for lang, query in QUERIES:
            print("─" * 70)
            print(f"[{lang}] Query: {query}")
            print("─" * 70)
            qvec = embedder.embed_query(query)
            results = await store.search(query_embedding=qvec, language=lang, top_k=3)
            if not results:
                print("  ❌ No results — KB may be empty for this language.")
                continue
            for i, r in enumerate(results, 1):
                title = r.get("section_title") or "(untitled)"
                score = r.get("similarity", 0.0)
                excerpt = (r.get("content") or "")[:150].replace("\n", " ")
                print(f"  {i}. [{score:.3f}] {title}")
                print(f"       {excerpt}…")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
