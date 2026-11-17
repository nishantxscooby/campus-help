"""BM25 keyword retrieval over processed Campus Help chunks."""

from dataclasses import dataclass
import logging

from rank_bm25 import BM25Okapi

from ..ingestion.models import DocumentChunk
from .tokenizer import tokenize

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    """A retrieved chunk with its BM25 relevance score."""

    chunk_id: str
    document_name: str
    category: str
    section: str
    page_number: int
    text: str
    score: float

    @classmethod
    def from_chunk(cls, chunk: DocumentChunk, score: float) -> "SearchResult":
        return cls(
            chunk_id=chunk.chunk_id,
            document_name=chunk.document_name,
            category=chunk.category,
            section=chunk.section,
            page_number=chunk.page_number,
            text=chunk.text,
            score=float(score),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "document_name": self.document_name,
            "category": self.category,
            "section": self.section,
            "page_number": self.page_number,
            "text": self.text,
            "score": self.score,
        }


class BM25Retriever:
    """Build and query a BM25 index over document chunks."""

    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self._chunks = list(chunks)
        self._tokenized_chunks = [tokenize(chunk.text) for chunk in self._chunks]
        self._index = BM25Okapi(self._tokenized_chunks) if self._chunks else None
        LOGGER.info("Built BM25 index with %d chunks", len(self._chunks))

    @property
    def size(self) -> int:
        """Return the number of indexed chunks."""
        return len(self._chunks)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Return up to top_k positively scoring chunks for a student query."""
        if top_k < 1:
            raise ValueError("top_k must be a positive integer")
        query_tokens = tokenize(query)
        if not query_tokens or self._index is None:
            return []

        scores = self._index.get_scores(query_tokens)
        query_vocabulary = set(query_tokens)
        ranked_indexes = sorted(
            (
                (index, score)
                for index, score in enumerate(scores)
                if query_vocabulary.intersection(self._tokenized_chunks[index])
            ),
            key=lambda item: (-item[1], item[0]),
        )[:top_k]
        return [
            SearchResult.from_chunk(self._chunks[index], score)
            for index, score in ranked_indexes
        ]
