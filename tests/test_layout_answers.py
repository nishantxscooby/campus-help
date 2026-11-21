import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from campus_help.web.api import create_app
from campus_help.web.composition import reviewed_calculation
from campus_help.web.tables import cell_position

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT = json.loads((ROOT/"data/output/scholarship-layout.json").read_text())


@pytest.mark.parametrize("question", [
    "If I have 7.6 CGPA will I be able to retain my scholarship?",
    "What CGPA is required for scholarship renewal?",
    "Can I use SGPA instead of CGPA for scholarship renewal?",
    "What if I have a backlog?",
    "What are the renewal conditions?",
    "Does the scholarship continue in the next semester?",
])
def test_ocr_reading_evidence(question):
    body=TestClient(create_app()).post("/ask",json={"question":question}).json()
    assert body["status"]=="insufficient_evidence" and not body["citations"]
    relevant=[w for w in body["excerpts"] if w["pdf_page_number"] in (4,5) and w["coordinates"]=="ocr_transcript"]
    assert relevant
    for w in relevant:
        assert TRANSCRIPT["pages"][w["pdf_page_number"]-1]["text"][w["start"]:w["end"]]==w["exact_quotation"]
        assert len(w["bbox"])==4 and w["version"]=="2025–26"


def test_ocr_quality_and_version():
    assert len(TRANSCRIPT["pages"])==11
    assert all(p["method"]=="ocr" for p in TRANSCRIPT["pages"])
    assert any(r["low_confidence"] for r in TRANSCRIPT["pages"][3]["regions"])
    body=TestClient(create_app()).post("/ask",json={"question":"Can I renew my scholarship with 7.6 CGPA in 2024-25?"}).json()
    assert "2025–26" in body["message"] and body["status"]=="insufficient_evidence"


@pytest.mark.parametrize("operator,value,meets",[
    ("at least","8",True),("more than","8",False),("less than","7.6",True),("at most","8.1",False)
])
def test_reviewed_numeric_bound(operator,value,meets):
    record=SimpleNamespace(claim=f"The award requires {operator} 8 CGPA.",questions=["Does {value} CGPA meet the award minimum?"])
    result=reviewed_calculation(f"Does {value} CGPA meet the award minimum?",record)
    assert ("does not meet" not in result)==meets
    assert reviewed_calculation(f"Does {value} SGPA meet the award minimum?",record) is None
    record.claim += " Except in the first term."
    assert reviewed_calculation(f"Does {value} CGPA meet the award minimum?",record) is None


def test_table_relationship_requires_single_containing_cell():
    grid=[[((0,0,50,20),"Conduct"),((50,0,100,20),"II offence")],
          [((0,20,50,40),"A"),((50,20,100,40),"B")]]
    cell=cell_position([grid],(52,21,98,39))
    assert (cell["row"],cell["column"],cell["headers"])==(2,2,["II offence"])
    assert cell_position([grid],(30,21,70,39)) is None


def test_reviewed_bound_through_api(tmp_path, monkeypatch):
    from campus_help.web.passages import digest
    from review_fixture import fixture_files, write_release

    claim = "The fictional award requires more than 8 CGPA."
    template = "Does {value} CGPA meet the numerical condition for the fictional award?"
    config, _ = fixture_files(tmp_path, text=claim)
    card = dict(fact_id="fictional-bound", questions=[template], relation="source_statement", claim=claim,
                context="Fictional award only", exceptions="None in this fixture", passage_sha256=digest(claim),
                witnesses=[dict(page=1, chunk_id="fictional", start=0, end=len(claim),
                                quotation=claim, parent_sha256=digest(claim))],
                status="APPROVED", reviewer="Synthetic fixture", decision_date="2026-01-01", review_complete=True)
    release = dict(format="reviewed-passages-v1", document=config.document.document_name,
                   pdf_sha256=config.document.pdf_sha256, corpus_sha256=config.corpus_revision,
                   review_revision="fixture-1", entries=[card])
    path, pin = write_release(tmp_path, release)
    monkeypatch.setenv("CAMPUS_HELP_REVIEW_FILE", str(path))
    monkeypatch.setenv("CAMPUS_HELP_REVIEW_SHA256", pin)
    client = TestClient(create_app(corpus=config))
    for value, expected in (("8", "does not meet"), ("8.01", "meets")):
        body = client.post("/ask", json={"question": template.format(value=value)}).json()
        assert body["status"] == "answered" and expected in body["message"]
        assert body["citations"][0]["exact_quotation"] == claim
    unbound = template.format(value="9").replace("CGPA", "SGPA")
    assert client.post("/ask", json={"question": unbound}).json()["status"] == "insufficient_evidence"


def test_mixed_units_cannot_supply_operand():
    record = SimpleNamespace(claim="The award requires at least 8 CGPA.",
                             questions=["Does {value} SGPA satisfy the CGPA requirement?"])
    assert reviewed_calculation("Does 9 SGPA satisfy the CGPA requirement?", record) is None


def test_attendance_is_not_derived_from_scholarship_percentages():
    body = TestClient(create_app()).post("/ask", json={"question": "Is 70% attendance enough for my scholarship?"}).json()
    assert body["status"] == "insufficient_evidence"
    assert all("attendance" in s["exact_quotation"].casefold() for s in body["excerpts"])


def test_cross_document_reading_keeps_separate_scopes():
    body = TestClient(create_app()).post("/ask", json={"question": "scholarship renewal and drinking alcohol"}).json()
    assert body["status"] == "insufficient_evidence"
    assert {s["title"] for s in body["excerpts"]} == {"Students’ Discipline and Conduct Rules", "Scholarship Policy"}
    assert "joint rule" in body["message"]


def test_unavailable_edition_is_visible_and_excluded(tmp_path, monkeypatch):
    path = tmp_path / "library.json"
    path.write_text((ROOT / "data/library.json").read_text())  # The relative source files are missing.
    monkeypatch.setenv("CAMPUS_HELP_LIBRARY", str(path))
    client = TestClient(create_app())
    assert [d["status"] for d in client.get("/documents").json()] == ["indexed", "unavailable"]
    body = client.post("/ask", json={"question": "Is my scholarship renewable?"}).json()
    assert body["reason"] == "unavailable_document" and not body["citations"]


def test_exception_or_ineligible_threshold_is_not_a_positive_bound():
    for claim in ["A disqualification requires less than 8 CGPA.",
                  "The award requires more than 8 CGPA unless an exception applies."]:
        record = SimpleNamespace(claim=claim, questions=["Does {value} CGPA meet the award minimum?"])
        assert reviewed_calculation("Does 7.9 CGPA meet the award minimum?", record) is None
