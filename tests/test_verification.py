from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import json
from pathlib import Path

import fitz
import pytest

from campus_help.answer.assembly import assemble_evidence
from campus_help.answer.evidence import score_source_units
from campus_help.answer.models import (
    EvidenceSelection, QuestionIntentType, SelectionDiagnostics, SourceSpan,
    ValidationContext, ValidationIssueCode,
)
from campus_help.answer.source_units import extract_source_units
from campus_help.answer.validation import validate_evidence
from campus_help.answer.verification import verify_question_evidence
from campus_help.answer.verification_contracts import (
    ApprovedCorpus, DocumentVersion, FactReference, FactRegistry, PolicyRelation,
    ProvenanceOutcome, ReviewedPolicyFact, ReviewScope, SourceWitness, VerificationOutcome,
)
from campus_help.hybrid.engine import HybridSearchResult


QUESTION = "Who is authorized to archive Form Z?"
STATEMENT = "The Records Office may archive Form Z."


def _context(parent, unit=None, question=QUESTION):
    if unit is None:
        unit = extract_source_units((parent,))[0]
    selected = EvidenceSelection(score_source_units(question, (unit,)), (), SelectionDiagnostics(1, 1, 0, 0, 1))
    return ValidationContext(question, (parent,), selected, assemble_evidence(question, selected))


@pytest.fixture
def source(tmp_path):
    pdf = tmp_path / "fictional.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), STATEMENT + "\n" + STATEMENT + "\npending further")
        document.new_page().insert_text((50, 50), "A different page.")
        document.save(pdf)
    row = dict(chunk_id="records", document_name=pdf.name, category="fixture",
               page_number=1, section="Archive", text=STATEMENT + " " + STATEMENT + "\n\npending further")
    path = tmp_path / "chunks.json"
    path.write_text(json.dumps(dict(document_name=pdf.name, category="fixture", chunks=[row])))
    parent = HybridSearchResult(**row, bm25_rank=None, semantic_rank=None, rrf_score=0.0)
    config = ApprovedCorpus(DocumentVersion(pdf.name, sha256(pdf.read_bytes()).hexdigest()),
                            pdf, path, sha256(path.read_bytes()).hexdigest(), "review-2")
    quote, = _context(parent).draft.quotations
    witness = SourceWitness(config.document, config.corpus_revision, config.review_revision,
                            sha256(parent.text.encode()).hexdigest(), quote.citation, quote.exact_quotation)
    fact = ReviewedPolicyFact("fixture-archive", "fact-1", "review-2", PolicyRelation.AUTHORITY_FOR,
                              (witness,), actor="Records Office", action="archive", object="Form Z")
    scope = ReviewScope((config.document,), fact.relation, config.corpus_revision, "review-2",
                        (), (), (), (), False)
    return config, FactRegistry(scope, (fact,)), parent


def _verify(config, registry, context):
    report = verify_question_evidence(context, approved_corpus=config, fact_registry=registry)
    assert report.is_verified is False
    assert report.obligations and all(item.unresolved_reason for item in report.obligations)
    return report


def test_authentication_is_version_bound_and_never_proves_a_fact(source):
    config, registry, parent = source
    report = _verify(config, registry, _context(parent))
    assert report.provenance is ProvenanceOutcome.CANONICAL_MATCH
    assert report.outcome is VerificationOutcome.NOT_ESTABLISHED
    assert report.witnesses == registry.facts[0].witnesses
    assert report.referenced_facts == (FactReference("fixture-archive", "fact-1"),)
    assert report.corpus_revision == config.corpus_revision and report.review_revision == "review-2"
    assert report.request.question == QUESTION and report.request.output_slots == ("actor",)
    assert report.request.requested_relation is PolicyRelation.AUTHORITY_FOR
    assert report.request.intent is QuestionIntentType.DISCIPLINARY_AUTHORITY
    assert {item.obligation for item in report.obligations} == set(report.request.required_obligations)
    with pytest.raises(FrozenInstanceError):
        report.outcome = "supported"
    with pytest.raises(TypeError):
        replace(registry.facts[0], conditions=[])
    assert _verify(config, registry, _context(parent)) == report


def test_rejects_validation_result_serialized_report_and_verified_keyword(source):
    config, registry, parent = source
    context = _context(parent)
    supplied = replace(validate_evidence(context), issues=(), validated_evidence=())
    for invalid in (supplied, {"is_verified": True}, _verify(config, registry, context)):
        with pytest.raises(TypeError, match="ValidationContext"):
            verify_question_evidence(invalid, approved_corpus=config, fact_registry=registry)
    with pytest.raises(TypeError):
        verify_question_evidence(context, approved_corpus=config, fact_registry=registry, is_verified=True)


@pytest.mark.parametrize("change", [
    {"text": "The Other Office may archive Form Z."},
    {"text": STATEMENT + " An invented exception."},
    {"document_name": "other.pdf"}, {"page_number": 2}, {"chunk_id": "unknown"},
    {"section": "Changed section"}, {"category": "different"},
])
def test_internally_consistent_context_still_requires_canonical_parent(source, change):
    config, registry, parent = source
    forged = _context(replace(parent, **change))
    assert validate_evidence(forged).validated_evidence
    report = _verify(config, registry, forged)
    assert report.provenance is ProvenanceOutcome.MISMATCH
    assert report.witnesses == report.referenced_facts == ()


def test_fresh_validation_checks_draft_and_request_question(source):
    config, registry, parent = source
    context = _context(parent)
    quote, = context.draft.quotations
    citation = replace(quote.citation, source_span=SourceSpan(1, len(STATEMENT) + 1))
    corrupt = replace(context.draft, quotations=(replace(quote, citation=citation),))
    for draft in (corrupt, replace(context.draft, question="Another question?")):
        report = _verify(config, registry, replace(context, draft=draft))
        assert report.provenance is ProvenanceOutcome.MISMATCH


def test_repeated_text_cannot_borrow_approval_at_another_offset(source):
    config, registry, parent = source
    first, second, _ = extract_source_units((parent,))
    assert first.text == second.text and first.span != second.span
    report = _verify(config, registry, _context(parent, second))
    assert report.provenance is ProvenanceOutcome.CANONICAL_MATCH
    assert report.outcome is VerificationOutcome.MISSING_APPROVED_FACT
    assert report.witnesses[0].citation.source_span == second.span
    assert not report.referenced_facts


@pytest.mark.parametrize("field", ["pdf_path", "corpus_path"])
def test_files_changed_after_pinning_fail_closed(source, field):
    config, registry, parent = source
    path = getattr(config, field)
    path.write_bytes(path.read_bytes() + b" ")
    report = _verify(config, registry, _context(parent))
    assert report.provenance is ProvenanceOutcome.STALE_SOURCE
    assert not report.witnesses


@pytest.mark.parametrize("target", ["scope", "fact", "witness", "scope_corpus", "witness_corpus", "witness_pdf"])
def test_stale_review_records_are_rejected(source, target):
    config, registry, parent = source
    fact, = registry.facts
    witness, = fact.witnesses
    if target == "scope":
        registry = replace(registry, scope=replace(registry.scope, review_revision="old"))
    elif target == "scope_corpus":
        registry = replace(registry, scope=replace(registry.scope, corpus_revision="0" * 64))
    elif target == "fact":
        registry = replace(registry, facts=(replace(fact, review_revision="old"),))
    else:
        changes = {"witness": {"review_revision": "old"}, "witness_corpus": {"corpus_revision": "0" * 64},
                   "witness_pdf": {"document": replace(config.document, pdf_sha256="0" * 64)}}
        registry = replace(registry, facts=(replace(fact, witnesses=(replace(witness, **changes[target]),)),))
    assert _verify(config, registry, _context(parent)).provenance is ProvenanceOutcome.STALE_SOURCE


@pytest.mark.parametrize("field", ["span", "parent_sha256", "quotation", "page"])
def test_malformed_approval_cannot_authenticate_itself(source, field):
    config, registry, parent = source
    fact, = registry.facts
    witness, = fact.witnesses
    if field == "span":
        witness = replace(witness, citation=replace(witness.citation, source_span=SourceSpan(1, len(STATEMENT) + 1)))
    elif field == "page":
        witness = replace(witness, citation=replace(witness.citation, pdf_page_number=2))
    elif field == "quotation":
        witness = replace(witness, exact_quotation=witness.exact_quotation.replace("Z", "X"))
    else:
        witness = replace(witness, parent_sha256="0" * 64)
    registry = replace(registry, facts=(replace(fact, witnesses=(witness,)),))
    assert _verify(config, registry, _context(parent)).provenance is ProvenanceOutcome.MISMATCH


def test_independently_pinned_json_still_has_to_match_pdf_page(source):
    config, registry, parent = source
    parent = replace(parent, page_number=2)
    envelope = json.loads(config.corpus_path.read_bytes())
    envelope["chunks"][0]["page_number"] = 2
    data = json.dumps(envelope).encode()
    config.corpus_path.write_bytes(data)
    config = replace(config, corpus_revision=sha256(data).hexdigest())
    assert _verify(config, None, _context(parent)).provenance is ProvenanceOutcome.MISMATCH


def test_canonical_extraction_checks_completeness_and_unit_boundaries(source):
    config, registry, parent = source
    unit, _, incomplete = extract_source_units((parent,))
    assert not incomplete.is_complete
    tail = replace(unit, text="Form Z.", span=SourceSpan(STATEMENT.index("Form Z."), len(STATEMENT)))
    for forged in (replace(unit, is_complete=False), replace(incomplete, is_complete=True), tail):
        assert _verify(config, registry, _context(parent, forged)).provenance is ProvenanceOutcome.MISMATCH


def test_missing_approvals_and_sources(source):
    config, registry, parent = source
    for absent in (None, replace(registry, facts=())):
        assert _verify(config, absent, _context(parent)).outcome is VerificationOutcome.MISSING_APPROVED_FACT
    for absent in (None, replace(config, pdf_path=config.pdf_path.with_name("missing.pdf"))):
        assert _verify(absent, registry, _context(parent)).provenance is ProvenanceOutcome.MISSING_SOURCE


def test_unbound_qualifiers_and_known_conflicts_remain_visible(source):
    config, registry, parent = source
    question = "Who is authorized to archive Form Z unless 4 working days have elapsed?"
    registry = replace(registry, scope=replace(registry.scope, known_conflicts=("review-note-4",)))
    report = _verify(config, registry, _context(parent, question=question))
    assert report.request.unresolved_qualifiers == (question,)
    assert report.request.explicit_constraints == ("4 working days",)
    assert report.conflict_findings == ("review-note-4",)
    unsupported = _verify(config, registry, _context(parent, question="What is the price of tea?"))
    assert unsupported.outcome is VerificationOutcome.UNSUPPORTED_REQUEST


def test_complete_review_with_authenticated_records_still_has_unresolved_obligations(source):
    config, registry, parent = source
    registry = replace(registry, scope=replace(registry.scope, complete=True))
    report = _verify(config, registry, _context(parent))
    assert report.outcome is VerificationOutcome.NOT_ESTABLISHED
    with pytest.raises(ValueError, match="obligation"):
        replace(report, obligations=())


def test_empty_evidence_cannot_authenticate_a_witness(source):
    config, registry, parent = source
    empty = EvidenceSelection((), (), SelectionDiagnostics(0, 0, 0, 0, 1))
    context = ValidationContext(QUESTION, (parent,), empty, assemble_evidence(QUESTION, empty))
    report = _verify(config, registry, context)
    assert report.provenance is ProvenanceOutcome.NO_EVIDENCE
    assert report.witnesses == report.referenced_facts == ()
    assert ValidationIssueCode.EMPTY_EVIDENCE in {issue.code for issue in report.context_findings}


@pytest.mark.parametrize(("chunk_id", "prefix"), [
    ("74b85be0218069f0", "A student having been awarded"), ("ff10accb8ee6929c", "25."),
])
def test_canonical_appeal_and_misleading_section_without_reviewed_facts(chunk_id, prefix):
    root = Path(__file__).resolve().parents[1] / "data"
    corpus = root / "output/discipline-rules.json"
    payload = json.loads(corpus.read_bytes())
    pdf = root / "input" / payload["document_name"]
    config = ApprovedCorpus(DocumentVersion(pdf.name, sha256(pdf.read_bytes()).hexdigest()),
                            pdf, corpus, sha256(corpus.read_bytes()).hexdigest(), "test-only")
    row = next(row for row in payload["chunks"] if row["chunk_id"] == chunk_id)
    parent = HybridSearchResult(**row, bm25_rank=None, semantic_rank=None, rrf_score=0)
    unit = next(unit for unit in extract_source_units((parent,)) if unit.text.startswith(prefix))
    report = _verify(config, None, _context(parent, unit))
    assert report.outcome is VerificationOutcome.MISSING_APPROVED_FACT
    witness, = report.witnesses
    assert witness.exact_quotation == parent.text[unit.span.start:unit.span.end]
    if chunk_id == "74b85be0218069f0":
        assert witness.citation.source_span == SourceSpan(346, 585)
        assert ValidationIssueCode.MISSING_PARENT_CONTEXT in {issue.code for issue in report.context_findings}
    else:
        assert witness.citation.section.startswith("22.") and witness.exact_quotation.startswith("25.")
