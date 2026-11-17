"""Load Milestone 1 JSON output into retrieval records."""

import json
from pathlib import Path
from typing import Any

from ..ingestion.models import DocumentChunk

REQUIRED_FIELDS = ("chunk_id", "document_name", "section", "page_number", "category", "text")


def _chunk_from_mapping(raw_chunk: Any, source: Path) -> DocumentChunk:
    if not isinstance(raw_chunk, dict):
        raise ValueError(f"Chunk in '{source}' must be a JSON object")
    missing = [field for field in REQUIRED_FIELDS if field not in raw_chunk]
    if missing:
        raise ValueError(f"Chunk in '{source}' is missing fields: {', '.join(missing)}")
    try:
        return DocumentChunk(
            chunk_id=str(raw_chunk["chunk_id"]),
            document_name=str(raw_chunk["document_name"]),
            section=str(raw_chunk["section"]),
            page_number=int(raw_chunk["page_number"]),
            category=str(raw_chunk["category"]),
            text=str(raw_chunk["text"]),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Chunk in '{source}' contains invalid metadata") from exc


def load_chunks(json_path: str | Path) -> list[DocumentChunk]:
    """Load chunks from a Milestone 1 JSON document envelope."""
    source = Path(json_path)
    if not source.is_file():
        raise FileNotFoundError(f"Processed chunks file does not exist: '{source}'")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read processed chunks file '{source}': {exc}") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("chunks"), list):
        raise ValueError(f"Processed chunks file '{source}' must contain a 'chunks' array")
    return [_chunk_from_mapping(chunk, source) for chunk in payload["chunks"]]
