"""Cross-encoder reranker using BAAI/bge-reranker-v2-m3."""

from FlagEmbedding import FlagReranker


class Reranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model: FlagReranker | None = None

    @property
    def model(self) -> FlagReranker:
        if self._model is None:
            self._model = FlagReranker(self.model_name, use_fp16=True)
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list[str],
        top_k: int = 5,
    ) -> list[dict]:
        if not candidates:
            return []
        pairs = [[query, text] for text in candidates]
        scores = self.model.compute_score(pairs, normalize=True)
        if isinstance(scores, float):
            scores = [scores]
        indexed = [
            {"index": i, "score": float(s), "text": candidates[i]} for i, s in enumerate(scores)
        ]
        indexed.sort(key=lambda x: x["score"], reverse=True)

        return indexed[:top_k]
