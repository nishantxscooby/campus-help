"""PDF extraction using PyMuPDF."""

import logging
from pathlib import Path

import fitz

from .models import DocumentMetadata, ExtractedPage

LOGGER = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Base error for expected document-processing failures."""


class EmptyDocumentError(DocumentProcessingError):
    """Raised when a PDF has no pages or no extractable text."""


class ScannedDocumentError(DocumentProcessingError):
    """Raised when a PDF appears to contain only images."""


class CorruptDocumentError(DocumentProcessingError):
    """Raised when PyMuPDF cannot open or read a PDF."""


def extract_pdf(pdf_path: str | Path, category: str) -> tuple[DocumentMetadata, list[ExtractedPage]]:
    """Extract page text and source metadata from a text-based PDF."""
    path = Path(pdf_path)
    try:
        document = fitz.open(path)
    except (fitz.FileDataError, OSError, ValueError) as exc:
        raise CorruptDocumentError(f"Unable to open PDF '{path}': {exc}") from exc

    try:
        if document.page_count == 0:
            raise EmptyDocumentError(f"PDF '{path}' contains no pages")

        pdf_metadata = {key: value for key, value in document.metadata.items() if value}
        pages: list[ExtractedPage] = []
        for index, page in enumerate(document):
            try:
                text = page.get_text("text")
            except (RuntimeError, ValueError) as exc:
                raise CorruptDocumentError(
                    f"Unable to read page {index + 1} of '{path}': {exc}"
                ) from exc
            pages.append(ExtractedPage(page_number=index + 1, text=text))
    finally:
        document.close()

    if not any(page.text.strip() for page in pages):
        raise ScannedDocumentError(
            f"PDF '{path}' contains no extractable text; OCR is not implemented"
        )

    metadata = DocumentMetadata(
        document_name=path.name,
        category=category,
        pdf_metadata=pdf_metadata,
    )
    LOGGER.info("Extracted %d pages from %s", len(pages), path)
    return metadata, pages
