from pathlib import Path

import fitz
import pytest

from campus_help.ingestion.extractor import (
    CorruptDocumentError,
    ScannedDocumentError,
    extract_pdf,
)


def _create_pdf(path: Path, text: str | None = None) -> None:
    document = fitz.open()
    page = document.new_page()
    if text is not None:
        page.insert_text((72, 72), text)
    document.set_metadata({"title": "Bennett Handbook", "author": "University"})
    document.save(path)
    document.close()


def test_extract_pdf_preserves_pages_and_metadata(tmp_path: Path):
    source = tmp_path / "handbook.pdf"
    _create_pdf(source, "Attendance policy: 75% minimum.")

    metadata, pages = extract_pdf(source, "academics")

    assert metadata.document_name == "handbook.pdf"
    assert metadata.category == "academics"
    assert metadata.pdf_metadata["title"] == "Bennett Handbook"
    assert pages[0].page_number == 1
    assert "Attendance policy" in pages[0].text


def test_extract_pdf_rejects_scanned_or_empty_text_pdf(tmp_path: Path):
    source = tmp_path / "scanned.pdf"
    _create_pdf(source)

    with pytest.raises(ScannedDocumentError, match="OCR"):
        extract_pdf(source, "general")


def test_extract_pdf_rejects_corrupted_pdf(tmp_path: Path):
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"not a PDF")

    with pytest.raises(CorruptDocumentError):
        extract_pdf(source, "general")
