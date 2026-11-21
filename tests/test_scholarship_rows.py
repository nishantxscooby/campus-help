from hashlib import sha256
import json
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from campus_help.ingestion.table_rows import extract_tables
from campus_help.web.api import create_app
from campus_help.web.eligibility import resolve
from campus_help.web.library import inventory
from campus_help.web.search import layout_rows
from campus_help.web.service import bundled_corpus

ROOT = Path(__file__).resolve().parents[1]
START = "If I have 7.6 CGPA will I be able to retain my scholarship?"
COURSE = "My course is BTech AI."


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def ask(client, question, history=()):
    result = client.post("/ask", json={"question": question, "history": list(history)})
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "insufficient_evidence" and not body["citations"]
    return body


def test_exact_real_conversation(client):
    assert "7.6 CGPA alone" in ask(client, START)["message"]
    reply = ask(client, COURSE, [START])
    assert "7.6 CGPA is below" in reply["message"] and "Which programme" not in reply["message"]
    assert "Is yours the Admission Scholarship" in reply["message"]
    spans = reply["excerpts"]
    assert spans[0]["table"]["values"] == ["B. Tech AI", "8.5 & above"]
    assert spans[0]["table"]["headers"] == ["Program Name", "Minimum CGPA Required"]
    assert any("FROM 2ND YEAR" in s["exact_quotation"] for s in spans)
    assert any("backlogs" in s["exact_quotation"] for s in spans)
    assert all(s["pdf_page_number"] == 4 and s["pdf_url"].endswith("#page=4") for s in spans)
    with pymupdf.open(stream=client.get(spans[0]["pdf_url"]).content, filetype="pdf") as pdf:
        for s in spans:
            assert pdf[3].get_text()[s["start"] : s["end"]] == s["exact_quotation"]


@pytest.mark.parametrize("course", ["BTech AI", "B.Tech AI", "B.Tech Artificial Intelligence"])
def test_aliases_and_one_turn(client, course):
    assert (
        "7.6 CGPA is below"
        in ask(client, f"{course}, 7.6 CGPA — will I retain my scholarship?")["message"]
    )
    assert "8.5 & above" in ask(client, f"What CGPA does {course} need?")["message"]


@pytest.mark.parametrize("course", ["BTech AI & ML", "BTech AI and ML", "B.Tech CSE AI"])
def test_specialisation_clarifies(client, course):
    reply = ask(client, course, [START])
    assert "exact programme" in reply["message"] and not reply["excerpts"]


def test_latest_grade_programme_and_scheme(client):
    history = [START, COURSE, "My scholarship is the Admission Scholarship."]
    correction = ask(client, "My CGPA is actually 8.1.", history)
    assert "8.1 CGPA is below" in correction["message"] and "Is yours" not in correction["message"]
    switched = ask(client, "No, I mean BTech CSE.", history + ["My CGPA is actually 8.1."])
    assert switched["excerpts"][0]["table"]["values"] == [
        "B. Tech Computer Science Engineering",
        "8 & above",
    ]
    assert "8.1 CGPA is at or above" in switched["message"]
    assert "backlogs" in switched["message"]


@pytest.mark.parametrize("q", ["I have one backlog.", "What if I had a supplementary exam?"])
def test_condition_followups(client, q):
    reply = ask(client, q, [START, COURSE])
    assert "no backlogs or supplementary exams" in reply["message"] and "7.6" in reply["message"]


def test_scheme_isolation_and_change_of_topic(client):
    reply = ask(client, "Academic Scholarship", [START, COURSE])
    assert reply["excerpts"] and all(s["pdf_page_number"] != 4 for s in reply["excerpts"])
    assert "doesn’t establish eligibility" in reply["message"]
    reply = ask(client, "smoking", [START, COURSE])
    assert reply["excerpts"] and "B. Tech AI" not in reply["message"]


@pytest.mark.parametrize(
    ("q", "needle"),
    [("Which scholarships are available?", "categories"), ("Can I hold two scholarships?", "highest")],
)
def test_open_scholarship_questions(client, q, needle):
    b = ask(client, q, [START, COURSE])
    assert needle in " ".join(r["exact_quotation"] for r in b["excerpts"]).lower()


def test_resolve_ambiguous_even_if_both_look_similar():
    labels = ["B. Tech AI", "B. Tech Artificial Intelligence"]
    names, unclear = resolve("BTech AI", labels)
    assert unclear and set(names) == set(labels)
    assert resolve("BTech CSE AI", ["B. Tech AI", "B. Tech Computer Science Engineering"])[1]


def test_synthetic_closed_cells_and_footnote():
    with pymupdf.open() as doc:
        p = doc.new_page()
        for x in (50, 240, 400):
            p.draw_line((x, 90), (x, 180))
        for y in (90, 120, 150, 180):
            p.draw_line((50, y), (400, y))
        for i, (left, right) in enumerate(
            [("Program Name", "Fee"), ("Track A", "100"), ("Track B", "250")]
        ):
            p.insert_text((60, 110 + 30 * i), left)
            p.insert_text((250, 110 + 30 * i), right)
        p.insert_text((50, 200), "Note: figures exclude tax.")
        (t,) = extract_tables(p)
        assert [[c[0]["text"] for c in row] for row in t["rows"]] == [
            ["Track A", "100"],
            ["Track B", "250"],
        ]
        assert t["notes"][0]["text"] == "Note: figures exclude tax."


def test_uncorroborated_cell_never_used_for_comparison(monkeypatch):
    from campus_help.web import eligibility

    book = inventory(bundled_corpus(ROOT / "data"), "Discipline", ROOT / "data/library.json")[1]
    row = next(s for s in layout_rows(book) if s.text == "B. Tech AI")
    from dataclasses import replace

    cells = json.loads(json.dumps(row.table["cells"]))
    cells[1][0]["image_agrees"] = False
    uncertain = replace(row, table={**row.table, "cells": cells})
    monkeypatch.setattr(eligibility, "layout_rows", lambda book: (uncertain,))
    message, _ = eligibility.row_response(COURSE, [START], [book])
    assert "check the original cell" in message.lower() and "below" not in message


@pytest.mark.parametrize(
    ("grade", "expected"), [("8.49", "below"), ("8.50", "at or above"), ("8.51", "at or above")]
)
def test_inclusive_threshold_and_unit(client, grade, expected):
    reply = ask(client, f"BTech AI, {grade} CGPA on the Admission Scholarship")
    assert f"{grade} CGPA is {expected}" in reply["message"]
    assert (
        "can’t be compared directly"
        in ask(client, f"BTech AI, {grade} SGPA on the Admission Scholarship")["message"]
    )


def test_warmed_row_cache_checks_current_bytes(tmp_path, monkeypatch):
    (row,) = json.loads((ROOT / "data/library.json").read_text())
    pdf = tmp_path / "scholarship_policy_25-26.pdf"
    pdf.write_bytes((ROOT / "data" / row["pdf"]).read_bytes())
    row.update(pdf=pdf.name, corpus=str(ROOT / "data" / row["corpus"]))
    path = tmp_path / "library.json"
    path.write_text(json.dumps([row]))
    monkeypatch.setenv("CAMPUS_HELP_LIBRARY", str(path))
    c = TestClient(create_app())
    assert "8.5 & above" in ask(c, COURSE, [START])["message"]
    pdf.write_bytes(pdf.read_bytes() + b"replacement version")
    assert c.post("/ask", json={"question": COURSE, "history": [START]}).status_code == 503
    row["pdf_sha256"] = sha256(pdf.read_bytes()).hexdigest()
    path.write_text(json.dumps([row]))
    assert TestClient(create_app()).get("/documents").json()[1]["status"] == "unavailable"


def test_native_fee_lookup_returns_only_the_requested_row(tmp_path, monkeypatch):
    from campus_help.answer.verification_contracts import ApprovedCorpus, DocumentVersion

    pdf = tmp_path / "fixture.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 70), "COURSE FEES")
        for x in (50, 240, 400):
            page.draw_line((x, 90), (x, 180))
        for y in (90, 120, 150, 180):
            page.draw_line((50, y), (400, y))
        for i, (name, fee) in enumerate(
            [("Program Name", "Fee"), ("Track Alpha", "100"), ("Track Beta", "250")]
        ):
            page.insert_text((60, 110 + 30 * i), name)
            page.insert_text((250, 110 + 30 * i), fee)
        page.insert_text((50, 200), "Note: fees exclude tax.")
        text = page.get_text()
        doc.save(pdf)
    corpus = tmp_path / "fixture.json"
    corpus.write_text(
        json.dumps(
            dict(
                document_name=pdf.name,
                category="fees",
                chunks=[
                    dict(
                        chunk_id="page1",
                        text=text,
                        document_name=pdf.name,
                        category="fees",
                        page_number=1,
                        section="Fees",
                    )
                ],
            )
        )
    )
    config = ApprovedCorpus(
        DocumentVersion(pdf.name, sha256(pdf.read_bytes()).hexdigest()),
        pdf,
        corpus,
        sha256(corpus.read_bytes()).hexdigest(),
        "unreviewed",
    )
    monkeypatch.setenv("CAMPUS_HELP_SEARCH_MODE", "bm25")
    body = ask(
        TestClient(create_app(corpus=config, title="Fee schedule")), "What is the fee for Track Alpha?"
    )
    assert body["excerpts"][0]["table"]["values"] == ["Track Alpha", "100"]
    assert any(s["exact_quotation"] == "Note: fees exclude tax." for s in body["excerpts"])
    assert not any(
        "Track Beta" in s["exact_quotation"] or s["exact_quotation"] == "250" for s in body["excerpts"]
    )


@pytest.mark.parametrize(
    ("header", "value", "expected"),
    [
        ("Minimum CGPA", "8 & above", (">=", "8")),
        ("CGPA", "greater than 8", (">", "8")),
        ("CGPA", "≤ 8.00", ("<=", "8.00")),
        ("Minimum CGPA", "<8", None),
        ("Minimum SGPA", "8", None),
        ("Minimum CGPA", "8 or 9", None),
    ],
)
def test_table_comparison_operators(header, value, expected):
    from campus_help.web.eligibility import numeric_bound

    assert numeric_bound(header, value) == expected


def test_reordered_thresholds_fail_source_geometry_validation(tmp_path, monkeypatch):
    (row,) = json.loads((ROOT / "data/library.json").read_text())
    pdf = ROOT / "data" / row["pdf"]
    transcript = json.loads((ROOT / "data" / row["corpus"]).read_text())
    entries = transcript["pages"][3]["tables"][0]["rows"]
    entries[0][1], entries[1][1] = entries[1][1], entries[0][1]
    altered = tmp_path / "misaligned.json"
    altered.write_text(json.dumps(transcript))
    row.update(
        pdf=str(pdf), corpus=altered.name, corpus_sha256=sha256(altered.read_bytes()).hexdigest()
    )
    path = tmp_path / "library.json"
    path.write_text(json.dumps([row]))
    monkeypatch.setenv("CAMPUS_HELP_LIBRARY", str(path))
    client = TestClient(create_app())
    assert client.get("/documents").json()[1]["status"] == "unavailable"
    assert not ask(client, START)["excerpts"]


def test_tiered_discipline_headers_stay_with_the_printed_row():
    from campus_help.ingestion.table_rows import tiered_rows
    from campus_help.web.tables import grid

    src = bundled_corpus(ROOT / "data")
    with pymupdf.open(src.pdf_path) as pdf:
        page = pdf[8]
        (table,) = tiered_rows(page, grid(page))
        headers = [" ".join(r["text"] for r in col).split() for col in table["headers"]]
        assert headers[1] == ["Acts", "of", "Indiscipline"]
        assert [words[-2:] for words in headers[2:5]] == [
            ["I", "offence"],
            ["II", "offence"],
            ["III", "Offence"],
        ]
        cooking, pets = table["rows"][:2]
        assert "Cooking" in cooking[1][0]["text"] and "pet/s" in pets[1][0]["text"]
        for cell in cooking:
            for ref in cell:
                assert page.get_text()[ref["start"] : ref["end"]] == ref["text"]


def test_unrelated_correction_and_unlisted_degree_never_reuse_the_old_row(client):
    body = ask(client, "My course is an unlisted MSc.", [START, COURSE])
    assert "exact programme" in body["message"] and not body["excerpts"]
    body = ask(client, "BTech AI with Data Science", [START])
    assert "exact programme" in body["message"] and not body["excerpts"]
