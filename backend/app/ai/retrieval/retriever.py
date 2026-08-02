"""Retriever: combines vector search + reranker for grounded medical queries."""

from app.ai.retrieval.embeddings import Embedder
from app.ai.retrieval.reranker import Reranker
from app.ai.retrieval.vectorstore import VectorStore


class Retriever:
    OVERFETCH = 20

    def __init__(self, store: VectorStore):

        self.store = store
        self._embedder: Embedder | None = None
        self._reranker: Reranker | None = None

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = Embedder()
        return self._embedder

    @property
    def reranker(self) -> Reranker:
        if self._reranker is None:
            self._reranker = Reranker()
        return self._reranker

    async def search(
        self,
        query: str,
        language: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:

        # 1. Embed the query
        query_embedding = self.embedder.embed_query(query)

        # 2. Vector search — over-fetch (نجيب أكتر من المطلوب)
        candidates = await self.store.search(
            query_embedding=query_embedding,
            language=language,
            top_k=self.OVERFETCH,
        )

        if not candidates:
            return []

        # 3. Rerank with cross-encoder
        texts = [c["content"] for c in candidates]
        reranked = self.reranker.rerank(query, texts, top_k=top_k)

        # 4. Return full candidate data with rerank scores
        results = []
        for item in reranked:
            candidate = candidates[item["index"]]
            results.append(
                {
                    "content": candidate["content"],
                    "source": candidate["source"],
                    "source_url": candidate.get("source_url"),
                    "section_title": candidate.get("section_title"),
                    "language": candidate["language"],
                    "similarity": item["score"],
                    "metadata": candidate.get("metadata"),
                }
            )

        return results
