"""Fictional source and operator release for API and browser integration tests."""

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz

from campus_help.answer.verification_contracts import ApprovedCorpus, DocumentVersion
from campus_help.web.api import create_app
from campus_help.web.reviews import load_release

QUESTION = "Who is authorized to archive Form Z under the records policy?"
QUOTE = "The Records Office may archive Form Z under the records policy."


def fixture_files(root, *, text=QUOTE):
    pdf = root / "fictional.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((30, 50), text)
        doc.save(pdf)
    row = dict(document_name=pdf.name, chunk_id="fictional", text=text, section="Records",
               category="fixture", page_number=1)
    corpus = root / "records.json"
    corpus.write_text(json.dumps(dict(document_name=pdf.name, category="fixture", chunks=[row])))
    config = ApprovedCorpus(DocumentVersion(pdf.name, sha256(pdf.read_bytes()).hexdigest()), pdf, corpus,
                            sha256(corpus.read_bytes()).hexdigest(), "unreviewed")
    entry = dict(fact_id="fixture-archive", status="APPROVED", reviewer="Synthetic test reviewer",
                 decision_date="2026-01-01", actor="The Records Office", action="archive", object="Form Z",
                 scope="the records policy", quotation=QUOTE, section="Records", page=1, chunk_id="fictional",
                 start=0, end=len(QUOTE), parent_sha256=sha256(QUOTE.encode()).hexdigest())
    release = dict(document=pdf.name, pdf_sha256=config.document.pdf_sha256, corpus_sha256=config.corpus_revision,
                   review_revision="fixture-1", relation="authority_for", modality="may", polarity="affirmative",
                   scope_complete=True, conditions=[], exceptions=[], conflicts=[], definitions=[],
                   governing_provisions=[], entries=[entry])
    return config, release


def write_release(root, release):
    path = root / "release.json"
    path.write_text(json.dumps(release))
    return path, sha256(path.read_bytes()).hexdigest()


def browser_app():
    import os

    directory = TemporaryDirectory()
    root = Path(directory.name)
    config, release = fixture_files(root)
    scenario = os.environ["REVIEW_TEST_CASE"]
    entry = release["entries"][0]
    if scenario in ("REJECTED", "PENDING_REVIEW"):
        entry["status"] = scenario
    if scenario == "wrong_page":
        entry["page"] = 2
    config, registry = load_release(*write_release(root, release), config)
    app = create_app(corpus=config, registry=registry, title="Fictional records policy")
    if scenario == "stale":
        config.pdf_path.write_bytes(b"changed")
    app.state.fixture_directory = directory
    return app
