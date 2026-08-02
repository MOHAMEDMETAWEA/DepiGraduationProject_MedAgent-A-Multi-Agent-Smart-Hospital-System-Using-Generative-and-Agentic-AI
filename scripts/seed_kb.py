#!/usr/bin/env python3
"""Seed the knowledge base with curated medical chunks for demos.

Reads `data/knowledge_base/seed/medical_seed.json`, embeds each chunk with the
project's standard embedder (multilingual-e5-large), and upserts to pgvector
via the existing VectorStore. Idempotent — re-running skips chunks already
present (deduped by content hash within source).

Usage:
  uv run python scripts/seed_kb.py                       # default seed
  uv run python scripts/seed_kb.py --dry-run             # show what would happen
  uv run python scripts/seed_kb.py --clear               # wipe seed source first
  uv run python scripts/seed_kb.py --file path/to.json   # alternate corpus
  uv run python scripts/seed_kb.py --verify              # only print DB stats

The script connects to the database via DATABASE_URL from backend/.env.
Inside docker compose run with: docker compose exec backend python /app/scripts/seed_kb.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

# Make backend importable so we reuse the project's embedder + vectorstore
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

DEFAULT_SEED = ROOT / "data" / "knowledge_base" / "seed" / "medical_seed.json"
SEED_SOURCE_TAG = "medagent_seed_v1"  # all seed chunks share this source tag


def _print_header(title: str) -> None:
    bar = "─" * max(40, len(title) + 4)
    print(f"\n{bar}\n  {title}\n{bar}")


def load_corpus(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    chunks = data.get("chunks", [])
    if not chunks:
        raise ValueError(f"No chunks found in {path}")
    return chunks


def report_distribution(chunks: list[dict]) -> None:
    by_lang = Counter(c.get("language", "?") for c in chunks)
    by_cat = Counter(c.get("category", "?") for c in chunks)
    by_src = Counter(c.get("source", "?") for c in chunks)
    print(f"  Total chunks         : {len(chunks)}")
    print(f"  By language          : {dict(by_lang)}")
    print(f"  By category          : {dict(by_cat)}")
    print(f"  By upstream source   : {dict(by_src)}")


async def seed(corpus_path: Path, *, clear: bool, dry_run: bool, verify_only: bool) -> int:
    from app.ai.retrieval.embeddings import Embedder
    from app.ai.retrieval.vectorstore import VectorStore
    from app.core.database import get_session
    from app.models.kb_chunk import KBChunk
    from sqlalchemy import select

    if verify_only:
        _print_header("Verifying KB state")
        async with get_session() as session:
            total = (await session.execute(select(KBChunk))).scalars().all()
            seed_chunks = [c for c in total if c.source == SEED_SOURCE_TAG]
            print(f"  KB rows total              : {len(total)}")
            print(f"  Rows from seed source      : {len(seed_chunks)}")
            if seed_chunks:
                langs = Counter(c.language for c in seed_chunks)
                print(f"  Seed by language           : {dict(langs)}")
                sample = seed_chunks[0]
                print(f"  Sample title               : {sample.section_title}")
                print(f"  Sample language            : {sample.language}")
                # pgvector returns numpy arrays; check identity, not truthiness
                emb = sample.embedding
                dim = "NULL" if emb is None else len(emb)
                print(f"  Embedding dim              : {dim}")
        return 0

    chunks = load_corpus(corpus_path)
    _print_header(f"Loaded corpus: {corpus_path.name}")
    report_distribution(chunks)

    if dry_run:
        _print_header("DRY RUN — no DB writes will occur")
        for c in chunks[:3]:
            preview = c["content"][:120].replace("\n", " ")
            print(f"  [{c['language']}/{c['category']}] {c['section_title']}")
            print(f"      {preview}…")
        if len(chunks) > 3:
            print(f"  …(+{len(chunks) - 3} more)")
        return 0

    _print_header("Loading embedder (this may take a moment on first run)")
    embedder = Embedder()
    print(f"  Model      : {embedder.model_name}")
    print(f"  Dimension  : {embedder.dimension}")

    contents = [c["content"] for c in chunks]
    # Embed in small batches — multilingual-e5-large is ~560M params and
    # encoding 20+ long chunks at once OOMs on a small container.
    BATCH = 4
    print(f"\n  Embedding {len(contents)} chunks (batch size = {BATCH})…")
    embeddings: list[list[float]] = []
    for start in range(0, len(contents), BATCH):
        sl = contents[start : start + BATCH]
        batch_emb = embedder.embed(sl)
        embeddings.extend(batch_emb)
        print(f"    {min(start + BATCH, len(contents))}/{len(contents)} done", flush=True)
    print(f"  All embedded. Dim = {len(embeddings[0])}")

    async with get_session() as session:
        store = VectorStore(session)

        if clear:
            _print_header(f"Clearing existing chunks for source={SEED_SOURCE_TAG}")
            deleted = await store.delete_by_source(SEED_SOURCE_TAG)
            print(f"  Deleted {deleted} existing seed rows.")

        _print_header("Upserting chunks (deduped by content hash)")
        # Group by language so each insert batch shares a language tag.
        # The vector store dedups by (source, content_hash) — re-running
        # without --clear is safe and silently skips existing rows.
        inserted_total = 0
        for lang in sorted({c["language"] for c in chunks}):
            lang_indices = [i for i, c in enumerate(chunks) if c["language"] == lang]
            lang_contents = [contents[i] for i in lang_indices]
            lang_embeddings = [embeddings[i] for i in lang_indices]
            lang_chunks = [chunks[i] for i in lang_indices]

            for i, chunk in enumerate(lang_chunks):
                ids = await store.upsert_chunks(
                    contents=[lang_contents[i]],
                    embeddings=[lang_embeddings[i]],
                    source=SEED_SOURCE_TAG,
                    source_url=chunk.get("source_url"),
                    section_title=chunk.get("section_title"),
                    language=lang,
                    extra_meta={
                        "seed_id": chunk["id"],
                        "category": chunk.get("category"),
                        "upstream_source": chunk.get("source"),
                    },
                )
                inserted_total += len(ids)

        print(f"  Inserted {inserted_total} new chunks (skipped {len(chunks) - inserted_total} duplicates).")

    _print_header("Done")
    print(f"  Source tag in DB    : {SEED_SOURCE_TAG}")
    print("  Verify with         : uv run python scripts/seed_kb.py --verify")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_SEED,
        help="Path to the seed JSON corpus.",
    )
    p.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing rows for the seed source before inserting.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be ingested without writing to the DB.",
    )
    p.add_argument(
        "--verify",
        action="store_true",
        help="Print current DB state for the seed source and exit.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(
        seed(
            corpus_path=args.file,
            clear=args.clear,
            dry_run=args.dry_run,
            verify_only=args.verify,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
