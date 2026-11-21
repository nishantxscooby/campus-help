from dataclasses import replace
from hashlib import sha256
import json

import fitz
import pytest
from fastapi.testclient import TestClient

from campus_help.answer.models import EvidenceCitation, SourceSpan
from campus_help.answer.verification_contracts import (
    ApprovedCorpus, DocumentVersion, FactRegistry, PolicyRelation, ReviewedPolicyFact,
    ReviewScope, SourceWitness,
)
from campus_help.web.api import create_app


QUESTION = "Who is authorized to archive Form Z under the records policy?"
STATEMENT = "The Records Office may archive Form Z under the records policy."


@pytest.fixture
def approved_fixture(tmp_path):
    pdf = tmp_path / "fictional-records.pdf"
    corpus = tmp_path / "fixture.json"
    with fitz.open() as document:
        document.new_page().insert_text((40, 50), STATEMENT)
        document.save(pdf)
    chunk = dict(chunk_id="test-records", document_name=pdf.name, category="fixture",
                 section="Records", page_number=1, text=STATEMENT)
    corpus.write_text(json.dumps(dict(document_name=pdf.name, category="fixture", chunks=[chunk])))
    config = ApprovedCorpus(DocumentVersion(pdf.name, sha256(pdf.read_bytes()).hexdigest()),
                            pdf, corpus, sha256(corpus.read_bytes()).hexdigest(), "test-only")
    citation = EvidenceCitation(pdf.name, "Records", 1, "test-records", SourceSpan(0, len(STATEMENT)))
    witness = SourceWitness(config.document, config.corpus_revision, config.review_revision,
                            sha256(STATEMENT.encode()).hexdigest(), citation, STATEMENT)
    fact = ReviewedPolicyFact("fictional-archive", "v1", "test-only", PolicyRelation.AUTHORITY_FOR,
                              (witness,), actor="The Records Office", action="archive", object="Form Z",
                              modality="may", polarity="affirmative", scope="the records policy",
                              conditions=(), exceptions=())
    scope = ReviewScope((config.document,), fact.relation, config.corpus_revision,
                        config.review_revision, (), (), (), (), True)
    return config, FactRegistry(scope, (fact,))


def test_public_endpoints_and_pdf():
    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok"}
        documents = client.get("/documents").json()
        assert len(documents) == 2 and all(d["status"] == "indexed" for d in documents)
        document = documents[0]
        response = client.get(document["pdf_url"])
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")


@pytest.mark.parametrize(("question", "reason"), [
    ("How much does lunch cost?", "no_evidence"),
    ("What is the deadline to file an appeal?", "awaiting_review"),
    ("Who reviews penalties and what is the deadline to appeal?", "clarify_appeal"),
])
def test_real_corpus_refusals(question, reason):
    with TestClient(create_app()) as client:
        result = client.post("/ask", json={"question": question})
        assert result.status_code == 200
        assert result.json()["status"] == "insufficient_evidence"
        assert result.json()["reason"] == reason and result.json()["citations"] == []


@pytest.mark.parametrize("payload", [{}, {"question": "   "}, {"question": "a" * 801},
                                     {"question": 123}, {"question": QUESTION, "is_verified": True}])
def test_malformed_request(payload):
    with TestClient(create_app()) as client:
        assert client.post("/ask", json=payload).status_code == 422


def test_reviewed_synthetic_authority_returns_exact_witness(approved_fixture):
    corpus, registry = approved_fixture
    with TestClient(create_app(corpus=corpus, registry=registry, title="Fictional records policy")) as client:
        result = client.post("/ask", json={"question": QUESTION}).json()
        assert result["status"] == "answered" and not result["message"]
        citation, = result["citations"]
        assert citation == dict(coordinates="parent_chunk", document_name="fictional-records.pdf", title="Fictional records policy",
                                section="Records", pdf_page_number=1, chunk_id="test-records", start=0,
                                end=len(STATEMENT), exact_quotation=STATEMENT,
                                pdf_url="/documents/handbook/pdf#page=1")
        assert client.get(citation["pdf_url"]).content == corpus.pdf_path.read_bytes()


@pytest.mark.parametrize("question", [
    QUESTION.replace("archive", "destroy"), QUESTION.replace("Form Z", "Form X"),
    QUESTION.replace("records policy", "housing policy"), QUESTION.replace("authorized", "forbidden"),
    QUESTION.replace("?", " unless a student objects?"), QUESTION.replace("Who", "Which student"),
])
def test_approval_does_not_transfer(approved_fixture, question):
    corpus, registry = approved_fixture
    with TestClient(create_app(corpus=corpus, registry=registry)) as client:
        result = client.post("/ask", json={"question": question}).json()
        assert result["status"] == "insufficient_evidence" and not result["citations"]


@pytest.mark.parametrize("change", [
    {"actor": "The Other Office"}, {"modality": "must"}, {"polarity": "negative"},
    {"conditions": None}, {"exceptions": ("except on Mondays",)},
])
def test_unknown_or_mismatched_fact_blocks_answer(approved_fixture, change):
    corpus, registry = approved_fixture
    fact = replace(registry.facts[0], **change)
    with TestClient(create_app(corpus=corpus, registry=replace(registry, facts=(fact,)))) as client:
        assert client.post("/ask", json={"question": QUESTION}).json()["status"] == "insufficient_evidence"


def test_conflict_or_absent_registry_blocks_answer(approved_fixture):
    corpus, registry = approved_fixture
    for configured in (None, replace(registry, scope=replace(registry.scope, known_conflicts=("other rule",))),
                       replace(registry, facts=registry.facts + (replace(registry.facts[0], fact_id="second"),))):
        with TestClient(create_app(corpus=corpus, registry=configured)) as client:
            assert client.post("/ask", json={"question": QUESTION}).json()["status"] == "insufficient_evidence"


def test_changed_source_returns_safe_service_error(approved_fixture):
    corpus, registry = approved_fixture
    with TestClient(create_app(corpus=corpus, registry=registry)) as client:
        assert client.post("/ask", json={"question": QUESTION}).json()["status"] == "answered"
        corpus.pdf_path.write_bytes(b"altered")
        for response in (client.post("/ask", json={"question": QUESTION}), client.get("/documents/handbook/pdf")):
            assert response.status_code == 503
            assert str(corpus.pdf_path) not in response.text


def test_local_cors_only():
    with TestClient(create_app()) as client:
        for origin, status in (("http://localhost:5173", 200), ("https://other.invalid", 400)):
            response = client.options("/ask", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
            assert response.status_code == status
