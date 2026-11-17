"""Sentence-transformer loading and normalized embedding generation."""

from collections.abc import Sequence
from typing import Any

import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


def load_model(model_name: str = MODEL_NAME, local_files_only: bool = True) -> Any:
    """Load a sentence-transformer model, preferring the local cache."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, local_files_only=local_files_only)


def encode_texts(model: Any, texts: Sequence[str]) -> np.ndarray:
    """Encode texts and return float32 unit vectors with the expected dimension."""
    if not texts:
        return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)
    raw_embeddings = np.asarray(
        model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False),
        dtype=np.float32,
    )
    if len(texts) == 1 and raw_embeddings.ndim == 1:
        raw_embeddings = raw_embeddings.reshape(1, -1)
    if raw_embeddings.ndim != 2:
        raise ValueError(f"Model returned embeddings with shape {raw_embeddings.shape}; expected 2-D")
    if raw_embeddings.shape[0] != len(texts):
        raise ValueError(
            f"Model returned {raw_embeddings.shape[0]} embeddings for {len(texts)} texts"
        )
    if raw_embeddings.shape[1] != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSION}-dimensional embeddings, "
            f"received {raw_embeddings.shape[1]}"
        )
    norms = np.linalg.norm(raw_embeddings, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("Model returned a zero vector that cannot be normalized")
    return raw_embeddings / norms
