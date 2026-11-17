"""Local embedding-based semantic retrieval for Campus Help."""

from .engine import SemanticRetriever, SemanticSearchResult
from .model import EMBEDDING_DIMENSION, MODEL_NAME, encode_texts, load_model
from .storage import load_embedding_index, save_embedding_index

__all__ = [
    "EMBEDDING_DIMENSION",
    "MODEL_NAME",
    "SemanticRetriever",
    "SemanticSearchResult",
    "encode_texts",
    "load_model",
    "load_embedding_index",
    "save_embedding_index",
]
