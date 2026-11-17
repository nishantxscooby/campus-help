from campus_help.ingestion.chunker import chunk_pages
from campus_help.ingestion.models import DocumentMetadata, ExtractedPage


def test_chunking_preserves_sections_pages_and_unique_ids():
    metadata = DocumentMetadata("rules.pdf", "academics", {})
    pages = [
        ExtractedPage(1, "ACADEMIC POLICIES\nAttendance is mandatory.\nMinimum is 75%."),
        ExtractedPage(2, "EXAMINATION\nBring your university ID."),
    ]
    chunks = chunk_pages(metadata, pages, max_chars=500)

    assert [chunk.section for chunk in chunks] == ["ACADEMIC POLICIES", "EXAMINATION"]
    assert [chunk.page_number for chunk in chunks] == [1, 2]
    assert all(chunk.document_name == "rules.pdf" for chunk in chunks)
    assert all(chunk.category == "academics" for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_chunking_splits_long_paragraphs_without_dropping_content():
    metadata = DocumentMetadata("rules.pdf", "student-life", {})
    pages = [ExtractedPage(1, "Conduct\n" + "Important policy. " * 20)]
    chunks = chunk_pages(metadata, pages, max_chars=100)

    assert len(chunks) > 1
    assert "Important policy." in " ".join(chunk.text for chunk in chunks)
