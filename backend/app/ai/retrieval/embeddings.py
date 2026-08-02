from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        dim = self.model.get_embedding_dimension()
        if dim is None:
            raise RuntimeError(f"Model '{self.model_name}' did not return embedding dimension")
        return dim

    def embed(self, texts: list[str], prefix: str = "passage: ") -> list[list[float]]:
        prefixed = [f"{prefix}{t}" for t in texts]
        embeddings = self.model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        return self.embed([query], prefix="query: ")[0]
