from pathlib import Path

import numpy as np
import pytest

from campus_help.ingestion.models import DocumentChunk
from campus_help.semantic.engine import SemanticRetriever
from campus_help.semantic.model import EMBEDDING_DIMENSION, encode_texts
from campus_help.semantic.storage import load_embedding_index, save_embedding_index


class FakeModel:
    def __init__(self, vectors: dict[str, np.ndarray]) -> None:
        self.vectors = vectors

    def encode(self, texts, **_kwargs):
        return np.asarray([self.vectors[text] for text in texts], dtype=np.float32)


def _vector(axis: int, value: float = 1.0) -> np.ndarray:
    vector = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    vector[axis] = value
    return vector


def _chunk(chunk_id: str, text: str, page: int = 1) -> DocumentChunk:
    return DocumentChunk(chunk_id, "handbook.pdf", "Attendance", page, "academics", text)


def test_encode_texts_normalizes_384_dimensional_embeddings():
    model = FakeModel({"policy": _vector(0, 3), "query": _vector(0, 4)})
    embeddings = encode_texts(model, ["policy", "query"])
    assert embeddings.shape == (2, 384)
    np.testing.assert_allclose(np.linalg.norm(embeddings, axis=1), [1.0, 1.0])


def test_semantic_search_ranks_by_cosine_similarity_and_preserves_metadata():
    chunks = [_chunk("a", "fees"), _chunk("b", "attendance", page=4)]
    model = FakeModel({"fees": _vector(0), "attendance": _vector(1), "question": _vector(1)})
    retriever = SemanticRetriever.from_chunks(model, chunks)
    results = retriever.search("question", top_k=5)

    assert results[0].chunk_id == "b"
    assert results[0].document_name == "handbook.pdf"
    assert results[0].category == "academics"
    assert results[0].section == "Attendance"
    assert results[0].page_number == 4
    assert results[0].text == "attendance"
    assert results[0].score == pytest.approx(1.0)


def test_semantic_search_handles_empty_and_irrelevant_queries():
    chunks = [_chunk("a", "fees")]
    model = FakeModel({"fees": _vector(0), "unrelated": _vector(1)})
    retriever = SemanticRetriever.from_chunks(model, chunks)
    assert retriever.search("   ") == []
    assert retriever.search("unrelated") == []


def test_embedding_storage_round_trip_preserves_chunks_and_vectors(tmp_path: Path):
    chunks = [_chunk("a", "fees")]
    embeddings = np.asarray([_vector(0)], dtype=np.float32)
    destination = tmp_path / "index.npz"
    save_embedding_index(destination, chunks, embeddings)
    loaded_chunks, loaded_embeddings = load_embedding_index(destination)
    assert loaded_chunks == chunks
    np.testing.assert_allclose(loaded_embeddings, embeddings)


def test_missing_and_incompatible_embedding_indexes_are_reported(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_embedding_index(tmp_path / "missing.npz")
    with pytest.raises(ValueError, match="384"):
        save_embedding_index(
            tmp_path / "bad.npz",
            [_chunk("a", "fees")],
            np.zeros((1, 3), dtype=np.float32),
        )


def test_model_dimension_and_invalid_top_k_are_reported():
    model = FakeModel({"bad": np.zeros(3, dtype=np.float32)})
    with pytest.raises(ValueError, match="384"):
        encode_texts(model, ["bad"])
    good_model = FakeModel({"fees": _vector(0)})
    retriever = SemanticRetriever.from_chunks(good_model, [_chunk("a", "fees")])
    with pytest.raises(ValueError, match="top_k"):
        retriever.search("fees", top_k=0)
