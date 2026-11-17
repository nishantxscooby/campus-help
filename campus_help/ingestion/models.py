"""Data structures used by the ingestion pipeline."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class DocumentMetadata:
    document_name: str
    category: str
    pdf_metadata: dict[str, Any]


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    document_name: str
    section: str
    page_number: int
    category: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
