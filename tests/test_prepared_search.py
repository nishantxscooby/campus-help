"""Release parity and cold-worker regressions for Render's BM25 configuration."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Barrier, Lock
import time

from fastapi.testclient import TestClient
import pytest

from campus_help.web import library, search
from campus_help.web.api import create_app
from campus_help.web.service import SourceUnavailable, bundled_corpus
from campus_help.web.span_store import SpanArtifact
from review_fixture import fixture_files, write_release
from campus_help.web.reviews import load_release

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST = DATA / "search-spans/manifest.json"
QUESTION = "Can I smoke around the campus?"


def books():
    return library.inventory(
        bundled_corpus(DATA),
        "Students’ Discipline and Conduct Rules",
        DATA / "library.json",
        span_manifest=MANIFEST,
        require_indexes=True,
    )


def test_every_packaged_span_matches_a_fresh_source_build():
    for book in books():
        assert book.artifact and not book.unavailable
        extracted = search.extract_spans(book)
        assert extracted and search.prepared_spans(book) == extracted


def test_cold_bm25_does_not_run_layout_or_load_encoder(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected geometry or semantic initialization")

    monkeypatch.setenv("CAMPUS_HELP_SEARCH_MODE", "bm25")
    monkeypatch.setattr(search, "extract_spans", forbidden)
    monkeypatch.setattr(library, "source_tables", forbidden)
    monkeypatch.setattr(search, "local_model", forbidden)
    search.cached_search.cache_clear()
    search.prepared_spans.cache_clear()
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200
        answer = client.post("/ask", json={"question": QUESTION}).json()
        assert answer["retrieval_mode"] == "bm25" and answer["excerpts"][0]["pdf_page_number"] == 9
        followup = client.post(
            "/ask",
            json={
                "question": "My course is BTech AI.",
                "history": ["Can I retain my scholarship with 7.6 CGPA?"],
            },
        ).json()
        assert followup["status"] == "insufficient_evidence"
        assert followup["excerpts"][0]["table"]["values"] == ["B. Tech AI", "8.5 & above"]


@pytest.mark.parametrize("target", ["pdf", "corpus", "artifact"])
def test_changed_or_missing_file_rejected_after_first_request(target, tmp_path, monkeypatch):
    monkeypatch.setenv("CAMPUS_HELP_SEARCH_MODE", "bm25")
    for folder in ["input", "output", "search-spans"]:
        (tmp_path / folder).mkdir()
    source = bundled_corpus(DATA)
    shutil.copy(source.pdf_path, tmp_path / "input")
    shutil.copy(source.corpus_path, tmp_path / "output")
    entry = json.loads(MANIFEST.read_text())["documents"][0]
    artifact = tmp_path / "search-spans" / entry["file"]
    shutil.copy(MANIFEST.parent / entry["file"], artifact)
    shutil.copy(MANIFEST, tmp_path / "search-spans")
    monkeypatch.setenv("CAMPUS_HELP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CAMPUS_HELP_SPAN_MANIFEST", str(tmp_path / "search-spans/manifest.json"))
    with TestClient(create_app()) as client:
        assert client.post("/ask", json={"question": QUESTION}).status_code == 200
        path = {
            "pdf": tmp_path / "input" / source.pdf_path.name,
            "corpus": tmp_path / "output" / source.corpus_path.name,
            "artifact": artifact,
        }[target]
        path.write_bytes(path.read_bytes() + b"!")
        assert client.post("/ask", json={"question": QUESTION}).status_code == 503
        path.unlink()
        assert client.post("/ask", json={"question": QUESTION}).status_code == 503


@pytest.mark.parametrize("damage", ["wrong_source", "wrong_offset", "wrong_row"])
def test_rehashed_index_still_checks_source_witnesses(damage, tmp_path):
    book = books()[1]
    payload = json.loads(gzip.decompress(book.artifact.path.read_bytes()))
    if damage == "wrong_source":
        payload["source"]["pdf_sha256"] = "0" * 64
    elif damage == "wrong_offset":
        payload["spans"][0]["start"] += 1
    else:
        rows = [s for s in payload["spans"] if s["table"] and "cells" in s["table"]]
        # The replacement cell is a real PDF slice but belongs to another programme.
        rows[0]["table"]["cells"][1] = rows[1]["table"]["cells"][1]
    path = tmp_path / "spans.gz"
    blob = gzip.compress(json.dumps(payload).encode())
    path.write_bytes(blob)
    forged = replace(book, artifact=SpanArtifact(path, sha256(blob).hexdigest()))
    with pytest.raises(SourceUnavailable):
        search.prepared_spans(forged)


def test_concurrent_cold_requests_build_one_index(monkeypatch):
    collection = books()
    search.cached_search.cache_clear()
    original = search.LibrarySearch.__init__
    calls = []
    lock = Lock()
    barrier = Barrier(4)

    def measured(self, *args, **kwargs):
        with lock:
            calls.append(1)
        time.sleep(0.05)
        original(self, *args, **kwargs)

    monkeypatch.setattr(search.LibrarySearch, "__init__", measured)

    def query(_):
        barrier.wait(timeout=10)
        return search.search(QUESTION, [], collection, False)[0][0].page

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(query, range(4))) == [9] * 4
    assert len(calls) == 1


def test_bm25_mode_overrides_legacy_embedding_path(tmp_path, monkeypatch):
    from review_fixture import QUESTION as authority_question

    source, release = fixture_files(tmp_path)
    source, registry = load_release(*write_release(tmp_path, release), source)
    monkeypatch.setenv("CAMPUS_HELP_SEMANTIC_INDEX", str(tmp_path / "missing.npz"))
    monkeypatch.setenv("CAMPUS_HELP_SEARCH_MODE", "bm25")
    with TestClient(create_app(corpus=source, registry=registry)) as client:
        assert client.post("/ask", json={"question": authority_question}).json()["status"] == "answered"


@pytest.mark.skipif(sys.platform not in {"linux", "darwin"}, reason="Unix RSS counters required")
def test_first_ask_cost_in_a_fresh_worker():
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.profile_bm25"],
        cwd=ROOT,
        env={k: v for k, v in os.environ.items() if not k.startswith("CAMPUS_HELP_")},
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["mode"] == "bm25" and 9 in result["pages"]
    assert {"torch", "sentence_transformers", "onnxruntime", "scipy"}.isdisjoint(result["imported"])
    # Generous cold-process ceilings; the former request took >7s and added >270 MiB.
    assert result["first_ask_seconds"] < 3
    assert result["peak_mib"] - result["ready_peak_mib"] < 64


def test_source_geometry_certificate_checked_without_rasterizing(monkeypatch):
    from campus_help.answer.verification import _canonical_chunks
    from campus_help.web.span_store import unpack

    book = books()[1]
    config = book.source
    pdf = config.pdf_path.read_bytes()
    chunks = _canonical_chunks(config)
    certificate = unpack(book.source, book.artifact)["layout_geometry"]
    monkeypatch.setattr(
        library, "source_tables", lambda *args: pytest.fail("Unexpected raster extraction")
    )
    library.validate_layout(config, pdf, chunks, certificate=certificate)
    with pytest.raises(ValueError, match="geometry certificate"):
        library.validate_layout(config, pdf, chunks, certificate={"4": "0" * 64})
