"""End-to-end ingestion orchestration and JSON serialization."""

import json
import logging
from pathlib import Path
from typing import Any

from .chunker import chunk_pages
from .extractor import extract_pdf

LOGGER = logging.getLogger(__name__)


def ingest_pdf(pdf_path: str | Path, category: str, max_chars: int = 1200) -> dict[str, Any]:
    """Process a PDF and return a JSON-serializable document payload."""
    metadata, pages = extract_pdf(pdf_path, category)
    chunks = chunk_pages(metadata, pages, max_chars=max_chars)
    if not chunks:
        raise ValueError(f"PDF '{pdf_path}' produced no text chunks")
    return {
        "document_name": metadata.document_name,
        "category": metadata.category,
        "metadata": metadata.pdf_metadata,
        "chunks": [chunk.to_dict() for chunk in chunks],
    }


def write_chunks_json(
    pdf_path: str | Path, output_path: str | Path, category: str, max_chars: int = 1200
) -> None:
    """Ingest a PDF and write formatted UTF-8 JSON, creating its parent directory."""
    payload = ingest_pdf(pdf_path, category, max_chars=max_chars)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOGGER.info("Wrote %d chunks to %s", len(payload["chunks"]), destination)
