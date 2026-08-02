#!/usr/bin/env python3
"""Build the knowledge base: chunk → embed → store in pgvector.

Sources supported:
  - medlineplus  — JSON from MedlinePlus search API
  - who          — JSON from WHO topics API (EN + AR)
  - egypt_moh    — HTML pages from Egyptian Ministry of Health

Usage:
  python scripts/build_kb.py
  python scripts/build_kb.py --source medlineplus
  python scripts/build_kb.py --source all --clear
"""

import argparse
import asyncio
import json
import sys
from itertools import groupby
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base" / "raw"

SOURCE_LICENSES = {
    "MedlinePlus": {
        "license": "Public Domain (US National Library of Medicine)",
        "terms_url": "https://medlineplus.gov/about/using/terms/",
    },
    "WHO": {
        "license": "CC BY-NC-SA 3.0 IGO",
        "terms_url": "https://www.who.int/about/policies/publishing/copyright",
    },
    "Egypt_MoH": {
        "license": "Public Domain (Egyptian Ministry of Health)",
        "terms_url": "https://www.mohp.gov.eg/",
    },
}


def load_medlineplus_chunks(chunker) -> list:
    medlineplus_dir = RAW_DIR / "medlineplus"
    if not medlineplus_dir.exists():
        print("  ⚠ No MedlinePlus data. Run download_kb.py first.")
        return []

    docs = []
    for filepath in sorted(medlineplus_dir.glob("*.json")):
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # Source license recorded in every chunk's metadata
        source_meta = data.get("_source_meta", SOURCE_LICENSES["MedlinePlus"])

        documents = data.get("result", {}).get("documents", [])
        for doc in documents:
            title = doc.get("title", "")
            full_summary = doc.get("fullSummary", "")
            if not full_summary:
                continue

            text = f"{title}\n\n{full_summary}"
            chunks = chunker.chunk_document(
                text=text,
                source="MedlinePlus",
                source_url=doc.get("organizationName", "https://medlineplus.gov"),
                section_title=title,
                language="en",
            )
            for chunk in chunks:
                chunk.metadata["source_license"] = source_meta.get("license", "")
                chunk.metadata["license_terms_url"] = source_meta.get("terms_url", "")
            docs.extend(chunks)

    return docs


def load_who_chunks(chunker) -> list:
    """Parse WHO JSON files (EN + AR) downloaded by download_kb.py."""
    who_dir = RAW_DIR / "who"
    if not who_dir.exists():
        print("  ⚠ No WHO data. Run download_kb.py first.")
        return []

    docs = []
    for filepath in sorted(who_dir.glob("topics_*.json")):
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        source_meta = data.get("_source_meta", SOURCE_LICENSES["WHO"])
        lang = source_meta.get("language", "en")

        # Handle both real WHO API response format and fallback format
        items = data.get("value", [])
        if not items:
            items = data.get("result", {}).get("items", [])

        for item in items:
            title = item.get("Title") or item.get("title", "")
            summary = item.get("Summary") or item.get("summary", "")
            if not summary:
                continue

            text = f"{title}\n\n{summary}" if title else summary
            source_url = item.get("url", "https://www.who.int/health-topics")
            chunks = chunker.chunk_document(
                text=text,
                source="WHO",
                source_url=source_url,
                section_title=title or None,
                language=lang,
            )
            for chunk in chunks:
                chunk.metadata["source_license"] = source_meta.get(
                    "license", SOURCE_LICENSES["WHO"]["license"]
                )
                chunk.metadata["license_terms_url"] = source_meta.get(
                    "terms_url", SOURCE_LICENSES["WHO"]["terms_url"]
                )
            docs.extend(chunks)

    return docs


def load_egypt_moh_chunks(chunker) -> list:
    """Parse Egypt MoH HTML files."""
    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text: list[str] = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "nav", "footer", "header"):
                self._skip = True

        def handle_endtag(self, tag):
            if tag in ("script", "style", "nav", "footer", "header"):
                self._skip = False

        def handle_data(self, data):
            if not self._skip:
                text = data.strip()
                if text and len(text) > 10:
                    self.text.append(text)

    moh_dir = RAW_DIR / "egypt_moh"
    if not moh_dir.exists():
        print("  ⚠ No Egypt MoH data. Run download_kb.py first.")
        return []

    docs = []
    for filepath in sorted(moh_dir.glob("*.html")):
        with open(filepath, encoding="utf-8") as f:
            html = f.read()

        extractor = TextExtractor()
        extractor.feed(html)
        text = " ".join(extractor.text)

        if len(text) < 100:
            continue

        chunks = chunker.chunk_document(
            text=text,
            source="Egypt_MoH",
            source_url="https://www.mohp.gov.eg/",
            section_title="Egypt Ministry of Health",
            language="ar",
        )
        for chunk in chunks:
            chunk.metadata["source_license"] = SOURCE_LICENSES["Egypt_MoH"]["license"]
            chunk.metadata["license_terms_url"] = SOURCE_LICENSES["Egypt_MoH"]["terms_url"]
        docs.extend(chunks)

    return docs


async def build_kb(source: str, clear: bool = False, batch_size: int = 32) -> None:
    from app.ai.retrieval.chunker import MedicalChunker
    from app.ai.retrieval.embeddings import Embedder
    from app.ai.retrieval.vectorstore import VectorStore
    from app.core.database import get_session

    chunker = MedicalChunker(chunk_size=256, chunk_overlap=64)
    embedder = Embedder()

    print(f"\n🔨 Building KB — source: {source}")
    print(f"   Embedding model: {embedder.model_name}")
    print(f"   Chunk size: 256 tokens | Overlap: 64 tokens")

    all_chunks = []
    if source in ("all", "medlineplus"):
        print("\n📄 Loading MedlinePlus (EN)...")
        chunks = load_medlineplus_chunks(chunker)
        all_chunks.extend(chunks)
        print(f"   → {len(chunks)} chunks")

    if source in ("all", "who"):
        print("\n📄 Loading WHO topics (EN + AR)...")
        chunks = load_who_chunks(chunker)
        all_chunks.extend(chunks)
        print(f"   → {len(chunks)} chunks")

    if source in ("all", "egypt_moh"):
        print("\n📄 Loading Egypt MoH (AR)...")
        chunks = load_egypt_moh_chunks(chunker)
        all_chunks.extend(chunks)
        print(f"   → {len(chunks)} chunks")

    if not all_chunks:
        print("\n⚠ No documents to process. Run download_kb.py first.")
        return

    print(f"\n📊 Total chunks to embed: {len(all_chunks)}")

    async with get_session() as session:
        store = VectorStore(session)

        if clear:
            for src in set(c.source for c in all_chunks):
                deleted = await store.delete_by_source(src)
                print(f"   Cleared {deleted} rows from '{src}'")

        print(f"\n🧠 Embedding + storing (batch={batch_size})...")
        stored = 0
        skipped = 0

        sorted_chunks = sorted(all_chunks, key=lambda c: c.source)
        for source_name, group in groupby(sorted_chunks, key=lambda c: c.source):
            source_chunks = list(group)
            for i in range(0, len(source_chunks), batch_size):
                batch = source_chunks[i : i + batch_size]
                contents = [c.content for c in batch]
                embeddings = embedder.embed(contents)

                first = batch[0]
                indices = [c.chunk_index for c in batch]
                # Merge per-chunk license metadata into upsert
                extra_meta = {
                    "source_license": first.metadata.get("source_license", ""),
                    "license_terms_url": first.metadata.get("license_terms_url", ""),
                }

                inserted_ids = await store.upsert_chunks(
                    contents=contents,
                    embeddings=embeddings,
                    source=first.source,
                    source_url=first.source_url,
                    section_title=first.section_title,
                    language=first.language,
                    extra_meta=extra_meta,
                    chunk_indices=indices,
                )

                batch_stored = len(inserted_ids)
                batch_skipped = len(batch) - batch_stored
                stored += batch_stored
                skipped += batch_skipped

                print(
                    f"   [{source_name}] {stored}/{len(all_chunks)} stored"
                    f"{f' | {skipped} skipped (dedup)' if skipped else ''}"
                )

        counts = await store.count_by_language()
        print("\n📊 Chunk counts by language:")
        for lang, count in sorted(counts.items()):
            status = "✅" if count >= 1000 else "⚠"
            print(f"   {status} {lang}: {count:,}")

        total = sum(counts.values())
        if total < 5000:
            print(f"\n⚠ WARNING: Total chunks = {total:,} (target: ≥5,000).")
            print("   Run download_kb.py to fetch more data, then re-run this script.")
        else:
            print(f"\n✅ Target met: {total:,} total chunks (≥5,000 required)")

    print(f"\n✅ Done: {stored} new chunks stored, {skipped} skipped (duplicates)")


def main():
    parser = argparse.ArgumentParser(description="Build the medical knowledge base")
    parser.add_argument(
        "--source",
        default="all",
        choices=["all", "medlineplus", "who", "egypt_moh"],
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing chunks for selected sources before inserting",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size (default: 32)",
    )
    args = parser.parse_args()

    asyncio.run(build_kb(args.source, args.clear, args.batch_size))


if __name__ == "__main__":
    main()
