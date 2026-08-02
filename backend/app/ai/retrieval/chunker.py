import re
from dataclasses import dataclass, field

import spacy
import tiktoken

try:
    nlp_en = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    import sys

    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp_en = spacy.load("en_core_web_sm")

# Arabic sentence boundaries: . ! ؟ \n followed by space or newline
_AR_SENTENCE_RE = re.compile(r"(?<=[.!؟\n])\s+")


@dataclass
class Chunk:
    content: str
    source: str
    source_url: str | None = None
    section_title: str | None = None
    language: str = "en"
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)


class MedicalChunker:
    """Splits medical documents into overlapping, sentence-aware chunks."""

    def __init__(self, chunk_size: int = 256, chunk_overlap: int = 64):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text))

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences. Uses spaCy for English, regex for Arabic."""
        # Detect if text has Arabic characters
        has_arabic = bool(re.search(r"[\u0600-\u06FF]", text))
        if has_arabic:
            raw = _AR_SENTENCE_RE.split(text)
            return [s.strip() for s in raw if s.strip()]
        doc = nlp_en(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    def chunk(self, text: str) -> list[str]:
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk: list[str] = []
        current_tokens = 0
        for sentence in sentences:
            sent_tokens = self._count_tokens(sentence)
            if current_tokens + sent_tokens > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                overlap_tokens = 0
                while current_chunk and overlap_tokens < self.chunk_overlap:
                    current_chunk.pop(0)
                    overlap_tokens = self._count_tokens(" ".join(current_chunk))

                current_tokens = self._count_tokens(" ".join(current_chunk))
            current_chunk.append(sentence)
            current_tokens += sent_tokens
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks

    def chunk_document(
        self,
        text: str,
        source: str,
        source_url: str | None = None,
        section_title: str | None = None,
        language: str = "en",
    ) -> list[Chunk]:
        raw_chunks = self.chunk(text)
        return [
            Chunk(
                content=c,
                source=source,
                source_url=source_url,
                section_title=section_title,
                language=language,
                chunk_index=i,
                metadata={
                    "source": source,
                    "section_title": section_title or "",
                    "language": language,
                    "chunk_index": i,
                    "total_chunks": len(raw_chunks),  # كام قطعة في المستند كله
                },
            )
            for i, c in enumerate(raw_chunks)
        ]
