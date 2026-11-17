"""Structure-aware chunking for extracted pages."""

import hashlib
import re

from .cleaner import clean_text
from .models import DocumentChunk, DocumentMetadata, ExtractedPage

HEADING_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*[\s.)-]+)?[A-Z][A-Za-z0-9 ,/&()'’:-]{2,79}$"
)


def _is_heading(line: str) -> bool:
    candidate = line.strip()
    if not candidate or len(candidate.split()) > 12:
        return False
    if candidate.endswith((".", ",", ";", ":")):
        return False
    return bool(HEADING_RE.fullmatch(candidate)) or candidate.isupper()


def _chunk_id(document_name: str, page: int, section: str, index: int, text: str) -> str:
    source = f"{document_name}|{page}|{section}|{index}|{text}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()[:16]


def chunk_pages(
    metadata: DocumentMetadata,
    pages: list[ExtractedPage],
    max_chars: int = 1200,
) -> list[DocumentChunk]:
    """Split text at headings and paragraphs, combining small adjacent blocks."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")

    chunks: list[DocumentChunk] = []
    current_section = "General"
    pending: list[str] = []
    pending_page = 1
    chunk_index = 0

    def emit() -> None:
        nonlocal pending, pending_page, chunk_index
        text = clean_text("\n\n".join(pending))
        if text:
            chunks.append(
                DocumentChunk(
                    chunk_id=_chunk_id(
                        metadata.document_name, pending_page, current_section, chunk_index, text
                    ),
                    document_name=metadata.document_name,
                    section=current_section,
                    page_number=pending_page,
                    category=metadata.category,
                    text=text,
                )
            )
            chunk_index += 1
        pending = []

    def add_text(text: str, page_number: int) -> None:
        nonlocal pending_page
        words = text.split()
        while words:
            candidate = " ".join(words)
            if pending:
                candidate = clean_text("\n\n".join(pending) + "\n\n" + candidate)
            if len(candidate) <= max_chars:
                if not pending:
                    pending_page = page_number
                pending.append(" ".join(words))
                return

            if pending:
                emit()
                continue

            prefix = ""
            consumed = 0
            for word in words:
                proposed = f"{prefix} {word}".strip()
                if prefix and len(proposed) > max_chars:
                    break
                prefix = proposed
                consumed += 1
            if consumed == 0:
                prefix = words[0][:max_chars]
                consumed = 1
            pending_page = page_number
            pending.append(prefix)
            emit()
            words = words[consumed:]

    for page in pages:
        lines = clean_text(page.text).split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if _is_heading(stripped):
                emit()
                current_section = stripped
                continue
            add_text(stripped, page.page_number)
    emit()
    return chunks
