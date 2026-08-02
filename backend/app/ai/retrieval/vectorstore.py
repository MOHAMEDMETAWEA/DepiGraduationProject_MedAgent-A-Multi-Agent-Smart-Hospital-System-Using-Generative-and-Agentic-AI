import uuid
from hashlib import sha256

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kb_chunk import KBChunk


class VectorStore:
    """Manages pgvector storage and ANN search for knowledge base chunks."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_chunks(
        self,
        contents: list[str],
        embeddings: list[list[float]],
        source: str,
        source_url: str | None = None,
        section_title: str | None = None,
        language: str = "en",
        extra_meta: dict | None = None,
        chunk_indices: list[int] | None = None,
    ) -> list[uuid.UUID]:
        """Insert chunks with their embeddings into kb_chunks. Skips duplicates by content hash."""
        ids: list[uuid.UUID] = []
        meta = extra_meta or {}

        for i, (content, embedding) in enumerate(zip(contents, embeddings, strict=False)):
            # Dedup: check if content hash exists for this source
            content_hash = sha256(content.encode()).hexdigest()
            existing = await self.session.execute(
                select(KBChunk).where(
                    KBChunk.source == source,
                    KBChunk.extra_meta["content_hash"].as_string() == content_hash,
                )
            )
            if existing.scalar_one_or_none():
                continue

            chunk_id = uuid.uuid4()
            chunk_meta = {
                **meta,
                "chunk_index": chunk_indices[i] if chunk_indices else i,
                "content_hash": content_hash,
            }
            db_chunk = KBChunk(
                id=chunk_id,
                source=source,
                source_url=source_url,
                section_title=section_title,
                content=content,
                language=language,
                embedding=embedding,
                extra_meta=chunk_meta,
            )
            self.session.add(db_chunk)
            ids.append(chunk_id)

        await self.session.commit()
        return ids

    async def delete_by_source(self, source: str) -> int:
        """Remove all chunks from a specific source. Returns count deleted."""
        result = await self.session.execute(
            text("DELETE FROM kb_chunks WHERE source = :source"),
            {"source": source},
        )
        await self.session.commit()
        return result.rowcount or 0

    async def search(
        self,
        query_embedding: list[float],
        language: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """ANN search by cosine distance using pgvector."""
        # asyncpg has no type for a Python list, so we serialize the embedding
        # to pgvector's textual literal `[v1,v2,…]` and cast it inside the SQL.
        # We also omit the language filter entirely when None (asyncpg can't
        # infer the type of `:language IS NULL` with a NULL bind).
        embedding_literal = "[" + ",".join(repr(float(v)) for v in query_embedding) + "]"

        if language:
            sql = text("""
                SELECT id, source, source_url, section_title, content,
                       language, metadata, created_at,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM kb_chunks
                WHERE embedding IS NOT NULL
                  AND language = :language
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """)
            params = {
                "embedding": embedding_literal,
                "language": language,
                "top_k": top_k,
            }
        else:
            sql = text("""
                SELECT id, source, source_url, section_title, content,
                       language, metadata, created_at,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM kb_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """)
            params = {
                "embedding": embedding_literal,
                "top_k": top_k,
            }

        result = await self.session.execute(sql, params)
        return [dict(row._mapping) for row in result.fetchall()]

    async def count_by_language(self) -> dict[str, int]:
        """Count chunks grouped by language."""
        result = await self.session.execute(
            text("SELECT language, count(*) FROM kb_chunks GROUP BY language")
        )
        return {row.language: row.count for row in result.fetchall()}
