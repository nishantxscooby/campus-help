import json
from pathlib import Path

import pytest

from campus_help.ingestion.models import DocumentChunk
from campus_help.retrieval.engine import BM25Retriever
from campus_help.retrieval.loader import load_chunks
from campus_help.retrieval.tokenizer import tokenize


def _chunk(chunk_id: str, text: str, section: str = "General") -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_name="handbook.pdf",
        section=section,
        page_number=2,
        category="academics",
        text=text,
    )


def test_tokenizer_normalizes_case_and_keeps_numbers():
    assert tokenize("Attendance is 75%, including policy.") == [
        "attendance",
        "is",
        "75",
        "including",
        "policy",
    ]


def test_search_ranks_matching_chunk_and_preserves_metadata():
    chunks = [
        _chunk("fees", "Tuition fees are due before registration.", "Fees"),
        _chunk("attendance", "Students must maintain 75 percent attendance.", "Attendance"),
        _chunk("housing", "Campus housing applications open in August.", "Housing"),
    ]
    results = BM25Retriever(chunks).search("attendance requirement", top_k=5)

    assert results[0].chunk_id == "attendance"
    assert results[0].document_name == "handbook.pdf"
    assert results[0].category == "academics"
    assert results[0].section == "Attendance"
    assert results[0].page_number == 2
    assert results[0].text == chunks[1].text
    assert results[0].score > 0


def test_search_respects_configurable_top_k():
    chunks = [_chunk(str(index), f"exam policy requirement {index}") for index in range(6)]
    assert len(BM25Retriever(chunks).search("exam policy", top_k=2)) == 2


def test_irrelevant_and_empty_queries_return_no_results():
    retriever = BM25Retriever([_chunk("one", "Library opening hours.")])
    assert retriever.search("quantum physics") == []
    assert retriever.search("   ") == []


def test_empty_index_and_invalid_top_k_are_handled():
    retriever = BM25Retriever([])
    assert retriever.size == 0
    assert retriever.search("anything") == []
    with pytest.raises(ValueError, match="top_k"):
        retriever.search("anything", top_k=0)


def test_load_chunks_reads_milestone_one_json(tmp_path: Path):
    source = tmp_path / "chunks.json"
    source.write_text(
        json.dumps({"document_name": "handbook.pdf", "chunks": [_chunk("a", "Policy text").__dict__]}),
        encoding="utf-8",
    )
    loaded = load_chunks(source)
    assert loaded[0].chunk_id == "a"
    assert loaded[0].text == "Policy text"


def test_load_chunks_reports_missing_file_and_invalid_shape(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_chunks(tmp_path / "missing.json")
    source = tmp_path / "invalid.json"
    source.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="chunks"):
        load_chunks(source)
