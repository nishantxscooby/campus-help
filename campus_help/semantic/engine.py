"""Cosine-similarity semantic retrieval over local embeddings."""

from dataclasses import dataclass
import logging

import numpy as np

from ..ingestion.models import DocumentChunk
from .model import encode_texts
from .storage import load_embedding_index, save_embedding_index

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SemanticSearchResult:
    """A semantically retrieved chunk with its cosine similarity."""

    chunk_id: str
    document_name: str
    category: str
    section: str
    page_number: int
    text: str
    score: float

    @classmethod
    def from_chunk(cls, chunk: DocumentChunk, score: float) -> "SemanticSearchResult":
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


class SemanticRetriever:
    """Search normalized chunk embeddings with locally generated query vectors."""

    def __init__(self, model: object, chunks: list[DocumentChunk], embeddings: np.ndarray) -> None:
        self._model = model
        self._chunks = list(chunks)
        self._embeddings = np.asarray(embeddings, dtype=np.float32)
        if self._embeddings.ndim != 2 or self._embeddings.shape[0] != len(self._chunks):
            raise ValueError("Embedding rows must match the number of chunks")
        if self._embeddings.shape[1] != 384:
            raise ValueError("Semantic embeddings must have 384 dimensions")
        norms = np.linalg.norm(self._embeddings, axis=1)
        if np.any(norms == 0):
            raise ValueError("Semantic embeddings must not contain zero vectors")
        self._embeddings = self._embeddings / norms[:, np.newaxis]

    @classmethod
    def from_chunks(cls, model: object, chunks: list[DocumentChunk]) -> "SemanticRetriever":
        embeddings = encode_texts(model, [chunk.text for chunk in chunks])
        return cls(model, chunks, embeddings)

    @classmethod
    def from_index(cls, model: object, index_path: str) -> "SemanticRetriever":
        chunks, embeddings = load_embedding_index(index_path)
        return cls(model, chunks, embeddings)

    def save(self, index_path: str) -> None:
        """Persist the current normalized index for later offline searches."""
        save_embedding_index(index_path, self._chunks, self._embeddings)

    @property
    def size(self) -> int:
        return len(self._chunks)

    def search(
        self, query: str, top_k: int = 5, min_similarity: float = 0.2
    ) -> list[SemanticSearchResult]:
        """Return the top cosine-similarity chunks for a non-empty query."""
        if top_k < 1:
            raise ValueError("top_k must be a positive integer")
        if not -1.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between -1 and 1")
        if not query.strip() or not self._chunks:
            return []
        query_embedding = encode_texts(self._model, [query])[0]
        scores = self._embeddings @ query_embedding
        ranked_indexes = np.argsort(-scores, kind="stable")
        return [
            SemanticSearchResult.from_chunk(self._chunks[index], scores[index])
            for index in ranked_indexes
            if scores[index] >= min_similarity
        ][:top_k]
