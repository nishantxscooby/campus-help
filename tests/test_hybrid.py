import numpy as np
import pytest

from campus_help.hybrid.engine import HybridRetriever
from campus_help.ingestion.models import DocumentChunk
from campus_help.retrieval.engine import BM25Retriever
from campus_help.semantic.engine import SemanticRetriever
from campus_help.semantic.model import EMBEDDING_DIMENSION


class FakeModel:
    def encode(self, texts, **_kwargs):
        vectors = {
            "question": self._vector(0),
            "fees": self._vector(1),
            "attendance": self._vector(2),
        }
        return np.asarray([vectors[text] for text in texts], dtype=np.float32)

    @staticmethod
    def _vector(axis):
        vector = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
        vector[axis] = 1
        return vector


def _chunk(chunk_id: str, text: str) -> DocumentChunk:
    return DocumentChunk(chunk_id, "rules.pdf", "Discipline", 3, "discipline", text)


def _hybrid(bm25_chunks, semantic_chunks=None, rrf_k=60):
    semantic_chunks = semantic_chunks or bm25_chunks
    model = FakeModel()
    embeddings = np.zeros((len(semantic_chunks), EMBEDDING_DIMENSION), dtype=np.float32)
    for index, chunk in enumerate(semantic_chunks):
        embeddings[index, 0] = 1
    return HybridRetriever(
        BM25Retriever(bm25_chunks),
        SemanticRetriever(model, semantic_chunks, embeddings),
        rrf_k=rrf_k,
    )


def test_rrf_known_calculation_and_diagnostics():
    retriever = _hybrid(
        [_chunk("a", "question"), _chunk("b", "fees")],
        [_chunk("b", "fees"), _chunk("a", "question")],
    )
    results = retriever.search("question", top_k=5)

    result_a = next(result for result in results if result.chunk_id == "a")
    assert result_a.bm25_rank == 1
    assert result_a.semantic_rank == 2
    assert result_a.rrf_score == pytest.approx(1 / 61 + 1 / 62)


def test_hybrid_deduplicates_and_preserves_metadata():
    retriever = _hybrid(
        [_chunk("shared", "question")],
        [_chunk("shared", "question")],
    )
    results = retriever.search("question")

    assert len(results) == 1
    assert results[0].chunk_id == "shared"
    assert results[0].document_name == "rules.pdf"
    assert results[0].category == "discipline"
    assert results[0].section == "Discipline"
    assert results[0].page_number == 3
    assert results[0].text == "question"


def test_missing_candidate_rank_is_none():
    retriever = _hybrid(
        [_chunk("keyword", "question"), _chunk("other", "fees")],
        [_chunk("keyword", "question"), _chunk("other", "question")],
    )
    results = retriever.search("question")
    other = next(result for result in results if result.chunk_id == "other")
    assert other.bm25_rank is None
    assert other.semantic_rank == 2
    assert other.to_dict()["bm25_rank"] is None


def test_empty_query_empty_indexes_and_invalid_parameters():
    retriever = _hybrid([], [])
    assert retriever.search("question") == []
    assert retriever.search("  ") == []
    with pytest.raises(ValueError, match="top_k"):
        retriever.search("question", top_k=0)
    with pytest.raises(ValueError, match="rrf_k"):
        HybridRetriever(BM25Retriever([]), SemanticRetriever(FakeModel(), [], np.empty((0, 384))), 0)


def test_deterministic_tie_breaking_uses_chunk_id():
    retriever = _hybrid(
        [_chunk("b", "question"), _chunk("a", "question")],
        [_chunk("a", "question"), _chunk("b", "question")],
    )
    results = retriever.search("question")
    assert [result.chunk_id for result in results] == ["a", "b"]
