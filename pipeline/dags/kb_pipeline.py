"""
T3.08 — Knowledge Base Pipeline (Airflow DAG)

Scheduled weekly: downloads medical sources → chunks → embeds → upserts → evaluates.
Run standalone with: python pipeline/dags/kb_pipeline.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"


def step_download():
    """Step 1: Download medical sources."""
    print("[1/4] Downloading knowledge base sources...")
    subprocess.run(
        [sys.executable, str(SCRIPTS / "download_kb.py")],
        check=False,
    )


def step_build():
    """Step 2: Chunk, embed, and upsert to pgvector."""
    print("[2/4] Building knowledge base...")
    subprocess.run(
        [sys.executable, str(SCRIPTS / "build_kb.py")],
        check=False,
    )


def step_verify():
    """Step 3: Verify KB has data."""
    print("[3/4] Verifying knowledge base...")
    from app.core.database import get_session
    from app.models.kb_chunk import KBChunk
    from sqlalchemy import select, func
    import asyncio

    async def _verify():
        async with get_session() as session:
            result = await session.execute(select(func.count()).select_from(KBChunk))
            count = result.scalar()
            print(f"  KB chunks: {count}")
            return count

    count = asyncio.run(_verify())
    if count == 0:
        print("  ⚠️  KB is empty — may need to re-run build step")
    else:
        print("  ✅ KB populated")


def step_evaluate():
    """Step 4: Evaluate retrieval quality."""
    print("[4/4] Evaluating retrieval quality...")
    from app.ai.retrieval.retriever import Retriever
    from app.ai.retrieval.vectorstore import VectorStore
    from app.core.database import get_session
    import asyncio

    test_queries = [
        ("headache treatment", "en"),
        ("diabetes management", "en"),
        ("علاج الصداع", "ar"),
        ("chest pain emergency", "en"),
    ]

    async def _eval():
        async with get_session() as session:
            store = VectorStore(session)
            retriever = Retriever(store)
            for query, lang in test_queries:
                results = await retriever.search(query, lang, top_k=3)
                print(f"  '{query}' ({lang}): {len(results)} results")
                for r in results:
                    print(f"    - {r.get('title', '?')[:60]}")

    asyncio.run(_eval())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--step", choices=["download", "build", "verify", "evaluate", "all"], default="all"
    )
    args = parser.parse_args()

    steps = {
        "download": step_download,
        "build": step_build,
        "verify": step_verify,
        "evaluate": step_evaluate,
    }

    if args.step == "all":
        for name, fn in steps.items():
            fn()
    else:
        steps[args.step]()

    print("\nKB pipeline complete.")
