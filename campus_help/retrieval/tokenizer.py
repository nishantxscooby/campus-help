"""Tokenization and normalization for BM25 indexing and queries."""

import re

TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Return lowercase word/number tokens while retaining policy numbers."""
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]
