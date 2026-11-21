from hashlib import sha256
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_help.answer.verification import _canonical_chunks, _check_pages
from campus_help.answer.source_units import extract_source_units
from campus_help.web.api import create_app
from campus_help.web.reviews import load_release
from campus_help.web.service import bundled_corpus
from review_fixture import QUESTION, fixture_files, write_release


@pytest.mark.parametrize("status,expected", [("APPROVED", "answered"), ("PENDING_REVIEW", "insufficient_evidence"),
                                              ("REJECTED", "insufficient_evidence")])
def test_operator_release(tmp_path, monkeypatch, status, expected):
    config, release = fixture_files(tmp_path)
    release["entries"][0]["status"] = status
    path, digest = write_release(tmp_path, release)
    monkeypatch.setenv("CAMPUS_HELP_REVIEW_FILE", str(path))
    monkeypatch.setenv("CAMPUS_HELP_REVIEW_SHA256", digest)
    with TestClient(create_app(corpus=config)) as client:
        assert client.post("/ask", json={"question": QUESTION}).json()["status"] == expected


@pytest.mark.parametrize("change", ["pdf_sha256", "corpus_sha256", "digest", "reviewer", "status", "duplicate"])
def test_invalid_release(tmp_path, change):
    config, release = fixture_files(tmp_path)
    if change in ("pdf_sha256", "corpus_sha256"):
        release[change] = "a" * 64
    elif change in ("reviewer", "status"):
        release["entries"][0][change] = ""
    elif change == "duplicate":
        release["entries"] *= 2
    path, digest = write_release(tmp_path, release)
    with pytest.raises(ValueError):
        load_release(path, "a" * 64 if change == "digest" else digest, config)


def test_real_review_leads_match_complete_pinned_units():
    config = bundled_corpus(Path("data"))
    parents = _canonical_chunks(config)
    manifest = json.loads(Path("docs/discipline-review.json").read_text())
    assert manifest["document"] == config.document.document_name
    pdf = config.pdf_path.read_bytes()
    assert manifest["pdf_sha256"] == sha256(pdf).hexdigest() == config.document.pdf_sha256
    assert manifest["corpus_sha256"] == config.corpus_revision
    for entry in manifest["entries"]:
        p = parents[entry["chunk_id"]]
        _check_pages(pdf, (p,))
        assert p.page_number == entry["page"] and p.section == entry["section"]
        assert sha256(p.text.encode()).hexdigest() == entry["parent_sha256"]
        assert entry["status"] == "PENDING_REVIEW" and entry["eligible"] is False
        assert any(u.is_complete and (u.span.start, u.span.end, u.text) ==
                   (entry["start"], entry["end"], entry["quotation"]) for u in extract_source_units((p,)))
