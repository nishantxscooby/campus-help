from dataclasses import replace
from hashlib import sha256
import json

import fitz
import pytest
from fastapi.testclient import TestClient

from campus_help.web.api import create_app
from campus_help.web.passages import compact, digest
from review_fixture import fixture_files, write_release


@pytest.mark.parametrize(("question", "reason", "page"), [
    ("What is the deadline to file an appeal?", "awaiting_review", 5),
    ("What gets me restigate", "possible_typo", 8),
    ("what makes me debar", "student_debarment", 4),
    ("How many working days do I have to appeal?", "awaiting_review", 5),
    ("Can I be rusticated?", "awaiting_review", 8),
    ("What is the difference between rustication and debarment?", "comparison", 4),
    ("Who reviews major disciplinary penalties?", "awaiting_review", 5),
    ("Who reviews minor disciplinary penalties?", "awaiting_review", 5),
    ("Does making a complaint to a committee member debar that member from sitting?", "awaiting_review", 4),
    ("Can I gamble on university premises?", "awaiting_review", 6),
    ("What happens if I break hostel rules?", "clarify_hostel", None),
    ("Does the Registrar review major penalties?", "related_only", 5),
    ("Can I appeal within 5 calendar days?", "related_only", 5),
    ("Does my appeal deadline start from the incident?", "related_only", 5),
    ("Can I be rustigated?", "possible_typo", 8),
    ("What punishment can I get?", "clarify_penalty", None),
    ("What is the scholarship deadline?", "unsupported_document", None),
])
def test_student_questions(question, reason, page):
    from pathlib import Path
    from campus_help.web.service import bundled_corpus
    response = TestClient(create_app(corpus=bundled_corpus(Path("data")))).post("/ask", json={"question": question})
    assert response.status_code == 200
    body = response.json()
    assert body["reason"] == reason and body["status"] == "insufficient_evidence" and not body["citations"]
    if page:
        assert page in [w["pdf_page_number"] for w in body["excerpts"]]


@pytest.mark.parametrize("change", ["none", "wrong_trigger", "reordered", "tampered_interval", "wrong_offset"])
def test_approved_fictional_deadline(tmp_path, monkeypatch, change):
    config, _ = fixture_files(tmp_path)
    heading = "Appeal:"
    rule = "A member may appeal in writing within 3 working days of receipt of the notice."
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 50), heading)
        page.insert_text((50, 72), rule)
        doc.save(config.pdf_path)
        raw = page.get_text()
    envelope = json.loads(config.corpus_path.read_text())
    envelope["chunks"][0]["text"] = rule
    config.corpus_path.write_text(json.dumps(envelope))
    config = replace(config, document=replace(config.document, pdf_sha256=sha256(config.pdf_path.read_bytes()).hexdigest()),
                     corpus_revision=sha256(config.corpus_path.read_bytes()).hexdigest())
    witnesses = [dict(page=1, chunk_id=chunk, start=parent.index(text), end=parent.index(text)+len(text),
                      quotation=text, parent_sha256=digest(parent))
                 for chunk, parent, text in [(None, raw, heading), ("fictional", rule, rule)]]
    question = "When can a member appeal?"
    card = dict(fact_id="fixture", relation="deadline", claim=rule, questions=[question], context="Written appeal",
                exceptions="None in this fictional scope", review_complete=True, witnesses=witnesses,
                passage_sha256=digest(compact(raw)), status="APPROVED", reviewer="Test fixture", decision_date="2026-01-01")
    if change == "reordered":
        witnesses.reverse()
    if change == "tampered_interval":
        card["passage_sha256"] = "0"*64
    if change == "wrong_offset":
        witnesses[-1]["start"] += 1
    release = dict(format="reviewed-passages-v1", document=config.document.document_name,
                   pdf_sha256=config.document.pdf_sha256, corpus_sha256=config.corpus_revision,
                   review_revision="fictional-1", entries=[card])
    path, pin = write_release(tmp_path, release)
    monkeypatch.setenv("CAMPUS_HELP_REVIEW_FILE", str(path))
    monkeypatch.setenv("CAMPUS_HELP_REVIEW_SHA256", pin)
    if change == "wrong_trigger":
        question += " From the incident?"
    response = TestClient(create_app(corpus=config)).post("/ask", json={"question": question})
    if change == "none":
        assert response.json()["status"] == "answered"
        assert [w["exact_quotation"] for w in response.json()["citations"]] == [heading, rule]
    elif change == "wrong_trigger":
        assert response.json()["status"] == "insufficient_evidence"
    else:
        assert response.status_code == 503
