"""Hybrid retrieval using Reciprocal Rank Fusion (RRF)."""

from dataclasses import dataclass
import logging
from typing import Optional

from ..retrieval.engine import BM25Retriever, SearchResult
from ..semantic.engine import SemanticRetriever, SemanticSearchResult

LOGGER = logging.getLogger(__name__)
DEFAULT_CANDIDATE_K = 10
DEFAULT_RRF_K = 60


@dataclass(frozen=True)
class HybridSearchResult:
    """A fused result with source ranks and its RRF diagnostic score."""

    chunk_id: str
    document_name: str
    category: str
    section: str
    page_number: int
    text: str
    bm25_rank: Optional[int]
    semantic_rank: Optional[int]
    rrf_score: float

    @classmethod
    def from_candidate(
        cls,
        result: SearchResult | SemanticSearchResult,
        bm25_rank: Optional[int],
        semantic_rank: Optional[int],
        rrf_score: float,
    ) -> "HybridSearchResult":
        return cls(
            chunk_id=result.chunk_id,
            document_name=result.document_name,
            category=result.category,
            section=result.section,
            page_number=result.page_number,
            text=result.text,
            bm25_rank=bm25_rank,
            semantic_rank=semantic_rank,
            rrf_score=float(rrf_score),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable result including fusion diagnostics."""
        return {
            "chunk_id": self.chunk_id,
            "document_name": self.document_name,
            "category": self.category,
            "section": self.section,
            "page_number": self.page_number,
            "text": self.text,
            "bm25_rank": self.bm25_rank,
            "semantic_rank": self.semantic_rank,
            "rrf_score": self.rrf_score,
        }


class HybridRetriever:
    """Fuse the existing BM25 and semantic retrievers with RRF."""

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        semantic_retriever: SemanticRetriever,
        rrf_k: int = DEFAULT_RRF_K,
        candidate_k: int = DEFAULT_CANDIDATE_K,
    ) -> None:
        if rrf_k < 1:
            raise ValueError("rrf_k must be a positive integer")
        if candidate_k < 1:
            raise ValueError("candidate_k must be a positive integer")
        self._bm25 = bm25_retriever
        self._semantic = semantic_retriever
        self._rrf_k = rrf_k
        self._candidate_k = candidate_k

    def search(self, query: str, top_k: int = 5) -> list[HybridSearchResult]:
        """Return top fused results from ten candidates per retrieval method."""
        if top_k < 1:
            raise ValueError("top_k must be a positive integer")
        if not query.strip():
            return []

        bm25_results = self._bm25.search(query, top_k=self._candidate_k)
        semantic_results = self._semantic.search(query, top_k=self._candidate_k)
        candidates: dict[str, dict[str, object]] = {}

        for rank, result in enumerate(bm25_results, start=1):
            candidate = candidates.setdefault(result.chunk_id, {"result": result})
            candidate["bm25_rank"] = rank
            candidate["rrf_score"] = float(candidate.get("rrf_score", 0.0)) + self._rrf(rank)

        for rank, result in enumerate(semantic_results, start=1):
            candidate = candidates.setdefault(result.chunk_id, {"result": result})
            candidate["semantic_rank"] = rank
            candidate["rrf_score"] = float(candidate.get("rrf_score", 0.0)) + self._rrf(rank)

        ranked_candidates = sorted(
            candidates.values(),
            key=lambda candidate: (
                -float(candidate["rrf_score"]),
                self._best_rank(candidate),
                str(candidate["result"].chunk_id),
            ),
        )[:top_k]
        return [
            HybridSearchResult.from_candidate(
                candidate["result"],
                candidate.get("bm25_rank"),
                candidate.get("semantic_rank"),
                float(candidate["rrf_score"]),
            )
            for candidate in ranked_candidates
        ]

    def _rrf(self, rank: int) -> float:
        return 1.0 / (self._rrf_k + rank)

    @staticmethod
    def _best_rank(candidate: dict[str, object]) -> int:
        ranks = [
            rank
            for key in ("bm25_rank", "semantic_rank")
            if (rank := candidate.get(key)) is not None
        ]
        return min(ranks) if ranks else 0
