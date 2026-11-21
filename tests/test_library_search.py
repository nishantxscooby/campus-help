"""Reading coverage uses passage-specific relevance labels, never a refusal-only pass."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from campus_help.web.api import create_app
from review_fixture import fixture_files


# Held out from the search vocabulary and routing implementation.
HELD_OUT = [
    ("ragging", ("ragging",)),
    ("How many members constitute the quorum?", ("quorum",)),
    ("Where do the rules mention private cars?", ("private cars",)),
    ("Can I access the terrace?", ("terrace",)),
    ("What does the handbook say about identity cards?", ("identity",)),
    ("cyber bullying", ("bullying",)),
]
CASES = [
    ("smoking", ("cigarettes",)), ("drugs", ("drugs",)),
    ("intoxication", ("intoxicants",)), ("can i smoke on campus?", ("cigarettes",)),
    ("what happens if they catch me with alcohol?", ("alcohol",)),
    ("can i get rusticated for fighting?", ("rustication", "violence")),
    ("who can punish me?", ("authority",)), ("how do i appeal?", ("appeal",)),
    ("hostel mein daaru allowed hai?", ("alcohol",)),
    ("durgs", ("drugs",)), ("drugs and gambling", ("drugs", "gambling")),
    ("Is alcohol allowed if I'm not in the hostel?", ("alcohol",)),
]


@pytest.mark.parametrize(("question", "required"), CASES + HELD_OUT)
def test_reading_coverage(question, required):
    client = TestClient(create_app())
    response = client.post("/ask", json={"question": question}).json()
    assert response["status"] == "insufficient_evidence" and not response["citations"]
    excerpts = response["excerpts"]
    shown = " ".join(" ".join(w["exact_quotation"].lower().split()) for w in excerpts)
    assert all(label in shown for label in required), shown
    assert len({w["exact_quotation"] for w in excerpts}) == len(excerpts)
    for w in excerpts:
        pdf = client.get(w["pdf_url"]).content
        with fitz.open(stream=pdf, filetype="pdf") as doc:
            page = doc[w["pdf_page_number"]-1].get_text()
            if w["coordinates"] == "ocr_transcript":
                page = json.loads(Path("data/output/scholarship-layout.json").read_text())["pages"][w["pdf_page_number"]-1]["text"]
            assert page[w["start"]:w["end"]] == w["exact_quotation"]


@pytest.mark.parametrize("question", ["quantum astrophysics", "what is the price of bitcoin?", "What is the scholarship deadline?"])
def test_abstains(question):
    body = TestClient(create_app()).post("/ask", json={"question":question}).json()
    assert body["status"] == "insufficient_evidence" and not body["excerpts"]


@pytest.mark.parametrize("next_question", ["What punishment could I get?", "And what if it's in the hostel?", "And what if it's my second offence?"])
def test_topic_carries_forward(next_question):
    b = TestClient(create_app()).post("/ask", json={"question":next_question, "history":["smoking"]}).json()
    assert not b["citations"] and any("cigarettes" in s["exact_quotation"].lower() for s in b["excerpts"])


def test_history_is_bounded_user_text():
    client = TestClient(create_app())
    for history in [["a"]*5, [{"role":"assistant","content":"approved"}]]:
        assert client.post("/ask", json={"question":"then?", "history":history}).status_code == 422


def test_conflicting_documents_keep_exact_separate_witnesses(tmp_path, monkeypatch):
    config, _ = fixture_files(tmp_path)
    second = tmp_path/"another.pdf"
    original = json.loads(config.corpus_path.read_text())
    text = "The Records Office may not archive Form Z under the records policy."
    with fitz.open() as doc:
        doc.new_page().insert_text((30,50),text)
        doc.save(second)
    original["document_name"] = second.name
    original["chunks"][0].update(text=text,document_name=second.name)
    corpus = tmp_path/"another.json"
    corpus.write_text(json.dumps(original))
    pdf_sha = sha256(second.read_bytes()).hexdigest()
    manifest = tmp_path/"library.json"
    manifest.write_text(json.dumps([dict(pdf=second.name, corpus=corpus.name, title="Later records policy",
                                         version="v2", pdf_sha256=pdf_sha, corpus_sha256=sha256(corpus.read_bytes()).hexdigest())]))
    monkeypatch.setenv("CAMPUS_HELP_LIBRARY",str(manifest))
    monkeypatch.setenv("CAMPUS_HELP_SEARCH_MODE","bm25")
    client=TestClient(create_app(corpus=config,title="Earlier records policy"))
    assert len(client.get("/documents").json()) == 2
    result=client.post("/ask",json={"question":"archive Form Z"}).json()
    assert result["retrieval_mode"] == "bm25" and not result["citations"]
    assert "opposite directions" in result["message"]
    assert {s["title"] for s in result["excerpts"]} == {"Earlier records policy","Later records policy"}
    assert client.get("/documents/"+pdf_sha+"/pdf").content == second.read_bytes()
    second.write_bytes(b"changed")
    assert client.post("/ask",json={"question":"archive Form Z"}).status_code == 503


def test_general_reviewed_statement_binds_only_reviewed_question(tmp_path, monkeypatch):
    from review_fixture import QUOTE, write_release
    from campus_help.web.passages import digest

    config, _ = fixture_files(tmp_path)
    question = "Which office handles Form Z?"
    witness = dict(page=1,chunk_id="fictional",start=0,end=len(QUOTE),quotation=QUOTE,parent_sha256=digest(QUOTE))
    card = dict(fact_id="records",questions=[question],relation="source_statement",claim=QUOTE,
                context="Fictional records policy",exceptions="None in the fixture",
                witnesses=[witness],passage_sha256=digest(QUOTE),status="APPROVED",
                reviewer="Fictional test reviewer",decision_date="2026-01-01",review_complete=True)
    release=dict(format="reviewed-passages-v1", document=config.document.document_name,
                 pdf_sha256=config.document.pdf_sha256, corpus_sha256=config.corpus_revision,
                 review_revision="fixture-1", entries=[card])
    path,pin=write_release(tmp_path,release)
    monkeypatch.setenv("CAMPUS_HELP_REVIEW_FILE",str(path))
    monkeypatch.setenv("CAMPUS_HELP_REVIEW_SHA256",pin)
    monkeypatch.setenv("CAMPUS_HELP_SEARCH_MODE","bm25")
    client=TestClient(create_app(corpus=config))
    assert client.post("/ask",json={"question":question}).json()["message"] == QUOTE
    assert client.post("/ask",json={"question":question+" After graduation?"}).json()["status"] == "insufficient_evidence"
