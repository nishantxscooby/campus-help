"""Local NumPy storage for semantic embeddings and chunk metadata."""

from pathlib import Path

import numpy as np

from ..ingestion.models import DocumentChunk
from .model import EMBEDDING_DIMENSION

_FIELDS = ("chunk_ids", "document_names", "categories", "sections", "page_numbers", "texts")


def save_embedding_index(
    index_path: str | Path, chunks: list[DocumentChunk], embeddings: np.ndarray
) -> None:
    """Save normalized embeddings and their source chunk metadata in one NPZ file."""
    destination = Path(index_path)
    vectors = np.asarray(embeddings, dtype=np.float32)
    _validate_embeddings(vectors, len(chunks))
    if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
        raise ValueError("Chunk IDs must be unique when saving an embedding index")
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        embeddings=vectors,
        chunk_ids=np.asarray([chunk.chunk_id for chunk in chunks]),
        document_names=np.asarray([chunk.document_name for chunk in chunks]),
        categories=np.asarray([chunk.category for chunk in chunks]),
        sections=np.asarray([chunk.section for chunk in chunks]),
        page_numbers=np.asarray([chunk.page_number for chunk in chunks], dtype=np.int64),
        texts=np.asarray([chunk.text for chunk in chunks]),
    )


def load_embedding_index(index_path: str | Path) -> tuple[list[DocumentChunk], np.ndarray]:
    """Load an embedding index and validate dimensions and metadata alignment."""
    source = Path(index_path)
    if not source.is_file():
        raise FileNotFoundError(f"Embedding index does not exist: '{source}'")
    try:
        with np.load(source, allow_pickle=False) as archive:
            missing = [field for field in ("embeddings", *_FIELDS) if field not in archive]
            if missing:
                raise ValueError(f"Embedding index is missing fields: {', '.join(missing)}")
            embeddings = np.asarray(archive["embeddings"], dtype=np.float32)
            _validate_embeddings(embeddings, len(archive["chunk_ids"]))
            arrays = {field: archive[field] for field in _FIELDS}
    except (OSError, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Unable to read embedding index '{source}': {exc}") from exc

    count = len(arrays["chunk_ids"])
    if any(len(values) != count for values in arrays.values()):
        raise ValueError("Embedding index metadata lengths do not match")
    chunks = [
        DocumentChunk(
            chunk_id=str(arrays["chunk_ids"][index]),
            document_name=str(arrays["document_names"][index]),
            category=str(arrays["categories"][index]),
            section=str(arrays["sections"][index]),
            page_number=int(arrays["page_numbers"][index]),
            text=str(arrays["texts"][index]),
        )
        for index in range(count)
    ]
    if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
        raise ValueError("Embedding index contains duplicate chunk IDs")
    return chunks, embeddings


def _validate_embeddings(embeddings: np.ndarray, chunk_count: int) -> None:
    if embeddings.ndim != 2:
        raise ValueError(f"Embeddings must be a 2-D array, received shape {embeddings.shape}")
    if embeddings.shape != (chunk_count, EMBEDDING_DIMENSION):
        raise ValueError(
            f"Expected embeddings with shape ({chunk_count}, {EMBEDDING_DIMENSION}), "
            f"received {embeddings.shape}"
        )
    if not np.all(np.isfinite(embeddings)):
        raise ValueError("Embeddings must contain only finite values")
