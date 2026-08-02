import pytest
from app.ai.retrieval.chunker import Chunk, MedicalChunker


class TestMedicalChunker:
    def setup_method(self):
        self.chunker = MedicalChunker(chunk_size=256, chunk_overlap=64)

    def test_init_rejects_invalid_overlap(self):
        with pytest.raises(ValueError):
            MedicalChunker(chunk_size=100, chunk_overlap=100)

    def test_chunk_short_text_returns_one_chunk(self):
        text = "Short text."
        chunks = self.chunker.chunk(text)
        assert len(chunks) == 1

    def test_chunk_long_text_produces_multiple_chunks(self):
        text = "The patient reports symptoms. " * 100
        chunks = self.chunker.chunk(text)
        assert len(chunks) > 1

    def test_chunk_preserves_content(self):
        text = "First sentence. Second sentence. Third sentence."
        chunks = self.chunker.chunk(text)
        combined = " ".join(chunks)
        assert "First" in combined
        assert "Second" in combined

    def test_chunk_document_returns_chunk_objects(self):
        text = "Patient has a headache. The pain started yesterday."
        result = self.chunker.chunk_document(
            text=text,
            source="TestSource",
            source_url="https://example.com",
            section_title="Headache",
            language="en",
        )
        assert len(result) > 0
        for c in result:
            assert isinstance(c, Chunk)
            assert c.source == "TestSource"

    def test_chunk_document_metadata(self):
        text = "Test symptom description."
        result = self.chunker.chunk_document(text=text, source="Test", language="ar")
        assert result[0].metadata["source"] == "Test"
        assert result[0].metadata["language"] == "ar"
        assert "chunk_index" in result[0].metadata

    def test_empty_text_returns_empty(self):
        assert self.chunker.chunk("") == []
