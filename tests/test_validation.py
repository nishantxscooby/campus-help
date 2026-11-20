import json
from pathlib import Path

import pytest

from campus_help.answer.assembly import assemble_evidence
from campus_help.answer.evidence import score_source_units
from campus_help.answer.models import (
    AnswerStatus,
    EvidenceSelection,
    EvidenceCitation,
    ExtractiveDraft,
    QuotedEvidence,
    SelectionDiagnostics,
    SourceSpan,
    SourceUnit,
    UnitType,
    ExtractionMethod,
    ValidationContext,
    ValidationIssueCode,
    ValidationIssueSeverity,
)
from campus_help.answer.validation import (
    ProvenanceValidationError,
    validate_evidence,
)
from campus_help.hybrid.engine import HybridSearchResult


def _unit(
    text: str,
    *,
    chunk_id: str = "chunk-a",
    document_name: str = "rules.pdf",
    section: str = "Appeals",
    page_number: int = 5,
    full_text: str | None = None,
    start: int = 0,
    unit_type: UnitType = UnitType.SENTENCE,
    is_complete: bool = True,
) -> SourceUnit:
    full_text = text if full_text is None else full_text
    return SourceUnit(
        chunk_id=chunk_id,
        document_name=document_name,
        category="discipline",
        section=section,
        page_number=page_number,
        full_chunk_text=full_text,
        text=text,
        span=SourceSpan(start, start + len(text)),
        unit_type=unit_type,
        is_complete=is_complete,
        extraction_method=(
            ExtractionMethod.SENTENCE_SPLIT
            if unit_type is UnitType.SENTENCE
            else ExtractionMethod.HEADING_DETECTION
        ),
    )


def _retrieved(unit: SourceUnit) -> HybridSearchResult:
    return HybridSearchResult(
        chunk_id=unit.chunk_id,
        document_name=unit.document_name,
        category=unit.category,
        section=unit.section,
        page_number=unit.page_number,
        text=unit.full_chunk_text,
        bm25_rank=None,
        semantic_rank=None,
        rrf_score=0.0,
    )


def _selection(*units: SourceUnit) -> EvidenceSelection:
    selected = tuple(
        score_source_units("appeal deadline", [unit])[0]
        for unit in units
    )
    return EvidenceSelection(
        selected_candidates=selected,
        excluded_candidates=(),
        diagnostics=SelectionDiagnostics(
            candidate_count=len(units),
            selected_count=len(units),
            excluded_count=0,
            deduplicated_count=0,
            max_evidence=max(1, len(units)),
        ),
    )


def _context(units: tuple[SourceUnit, ...]) -> ValidationContext:
    selection = _selection(*units)
    draft = assemble_evidence("Appeal deadline", selection)
    return ValidationContext(
        question="Appeal deadline",
        retrieved_chunks=tuple(_retrieved(unit) for unit in units),
        selection=selection,
        draft=draft,
    )


def test_valid_exact_quotation_provenance():
    unit = _unit("A written appeal is due within 5 working days.")
    result = validate_evidence(_context((unit,)))

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert len(result.validated_evidence) == 1
    assert any(
        issue.code is ValidationIssueCode.SUFFICIENCY_NOT_EVALUATED
        for issue in result.issues
    )


def test_missing_chunk_id():
    unit = _unit("A written appeal is due.", chunk_id="missing")
    context = _context((unit,))
    object.__setattr__(context, "retrieved_chunks", ())

    with pytest.raises(ProvenanceValidationError, match="missing"):
        validate_evidence(context)


def test_mismatched_document_metadata():
    unit = _unit("A written appeal is due.")
    context = _context((unit,))
    retrieved = context.retrieved_chunks[0]
    mismatched = HybridSearchResult(
        chunk_id=retrieved.chunk_id,
        document_name="other.pdf",
        category=retrieved.category,
        section=retrieved.section,
        page_number=retrieved.page_number,
        text=retrieved.text,
        bm25_rank=None,
        semantic_rank=None,
        rrf_score=0.0,
    )
    object.__setattr__(context, "retrieved_chunks", (mismatched,))

    with pytest.raises(ProvenanceValidationError, match="metadata"):
        validate_evidence(context)


def test_incorrect_pdf_page():
    unit = _unit("A written appeal is due.")
    context = _context((unit,))
    retrieved = context.retrieved_chunks[0]
    mismatched = HybridSearchResult(
        chunk_id=retrieved.chunk_id,
        document_name=retrieved.document_name,
        category=retrieved.category,
        section=retrieved.section,
        page_number=99,
        text=retrieved.text,
        bm25_rank=None,
        semantic_rank=None,
        rrf_score=0.0,
    )
    object.__setattr__(context, "retrieved_chunks", (mismatched,))

    with pytest.raises(ProvenanceValidationError, match="PDF|metadata|conflicts"):
        validate_evidence(context)


def test_incorrect_section():
    unit = _unit("A written appeal is due.")
    context = _context((unit,))
    draft = context.draft
    citation = draft.quotations[0].citation
    mismatched_citation = EvidenceCitation(
        document_name=citation.document_name,
        section="Wrong section",
        pdf_page_number=citation.pdf_page_number,
        chunk_id=citation.chunk_id,
        source_span=citation.source_span,
    )
    mismatched_draft = ExtractiveDraft(
        question=draft.question,
        quotations=(QuotedEvidence(draft.quotations[0].exact_quotation, mismatched_citation),),
    )
    object.__setattr__(context, "draft", mismatched_draft)

    with pytest.raises(ProvenanceValidationError, match="metadata|conflicts"):
        validate_evidence(context)


def test_invalid_offsets():
    unit = _unit("A written appeal is due.")
    context = _context((unit,))
    citation = context.draft.quotations[0].citation
    mismatched_citation = EvidenceCitation(
        document_name=citation.document_name,
        section=citation.section,
        pdf_page_number=citation.pdf_page_number,
        chunk_id=citation.chunk_id,
        source_span=SourceSpan(0, 999),
    )
    mismatched_draft = ExtractiveDraft(
        question=context.draft.question,
        quotations=(QuotedEvidence(context.draft.quotations[0].exact_quotation, mismatched_citation),),
    )
    object.__setattr__(context, "draft", mismatched_draft)

    with pytest.raises(ProvenanceValidationError, match="span|outside|metadata"):
        validate_evidence(context)


def test_quotation_substring_mismatch():
    unit = _unit("A written appeal is due.")
    context = _context((unit,))
    mismatched_draft = ExtractiveDraft(
        question=context.draft.question,
        quotations=(
            QuotedEvidence(
                exact_quotation="Changed quotation.",
                citation=context.draft.quotations[0].citation,
            ),
        ),
    )
    object.__setattr__(context, "draft", mismatched_draft)

    with pytest.raises(ProvenanceValidationError, match="differs"):
        validate_evidence(context)


def test_quotation_not_present_in_selected_evidence():
    unit = _unit("A written appeal is due.")
    context = _context((unit,))
    wrong_unit = _unit("A different sentence.", chunk_id="other")
    selection = _selection(wrong_unit)
    object.__setattr__(context, "selection", selection)

    with pytest.raises(ProvenanceValidationError, match="chunk|source unit|differs"):
        validate_evidence(context)


def test_conflicting_duplicate_chunk_ids():
    unit = _unit("A written appeal is due.", chunk_id="duplicate")
    context = _context((unit,))
    other = HybridSearchResult(
        chunk_id="duplicate",
        document_name="rules.pdf",
        category="discipline",
        section="Appeals",
        page_number=5,
        text="A conflicting duplicate parent text.",
        bm25_rank=None,
        semantic_rank=None,
        rrf_score=0.0,
    )
    object.__setattr__(
        context,
        "retrieved_chunks",
        (context.retrieved_chunks[0], other),
    )

    with pytest.raises(ProvenanceValidationError, match="conflicting"):
        validate_evidence(context)


def test_empty_evidence():
    context = ValidationContext(
        question="Unsupported question",
        retrieved_chunks=(),
        selection=_selection(),
        draft=assemble_evidence("Unsupported question", _selection()),
    )
    result = validate_evidence(context)

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert result.validated_evidence == ()
    assert result.issues[0].code is ValidationIssueCode.EMPTY_EVIDENCE


def test_heading_only_evidence():
    unit = _unit(
        "APPEAL PROCEDURE",
        unit_type=UnitType.HEADING,
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert any(
        issue.code is ValidationIssueCode.HEADING_USED_AS_EVIDENCE
        for issue in result.issues
    )


def test_incomplete_numbered_item():
    unit = _unit(
        "1. Cancellation for a specified",
        unit_type=UnitType.NUMBERED_ITEM,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.INCOMPLETE_SOURCE_UNIT
        for issue in result.issues
    )


def test_table_fragment():
    unit = _unit(
        "•Expulsion from the University",
        unit_type=UnitType.TABLE_ROW,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.TABLE_FRAGMENT_USED_AS_EVIDENCE
        for issue in result.issues
    )


def test_continuation_unit():
    unit = _unit(
        "new submissions have been made",
        unit_type=UnitType.CONTINUATION,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.CONTINUATION_USED_AS_EVIDENCE
        for issue in result.issues
    )


def test_context_dependent_sentence_tail():
    full_text = "A student may appeal. 5 working days of the service of the order."
    unit = _unit(
        "5 working days of the service of the order.",
        full_text=full_text,
        start=full_text.find("5 working days"),
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION
        for issue in result.issues
    )


def test_multiple_valid_quotations():
    first = _unit("The appeal deadline is 5 working days.", chunk_id="a")
    second = _unit("The Vice-Chancellor reviews appeals.", chunk_id="b")
    result = validate_evidence(_context((first, second)))

    assert len(result.validated_evidence) == 2
    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE


def test_deterministic_ordering():
    first = _unit("First complete sentence.", chunk_id="a")
    second = _unit("Second complete sentence.", chunk_id="b")
    context = _context((first, second))

    result = validate_evidence(context)
    assert [
        item.quotation.citation.chunk_id
        for item in result.validated_evidence
    ] == ["a", "b"]


def test_structurally_valid_evidence_never_becomes_answered():
    unit = _unit("The university has an appeal procedure.")
    result = validate_evidence(_context((unit,)))

    assert result.status is not AnswerStatus.ANSWERED
    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE


def test_real_appeal_corpus_example():
    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    raw = next(
        chunk
        for chunk in payload["chunks"]
        if chunk["chunk_id"] == "74b85be0218069f0"
    )
    unit = _unit(
        "5 working days of the service of the order.",
        chunk_id=raw["chunk_id"],
        document_name=raw["document_name"],
        section=raw["section"],
        page_number=raw["page_number"],
        full_text=raw["text"],
        start=raw["text"].find("5 working days"),
        unit_type=UnitType.SENTENCE,
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert any(
        issue.code is ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION
        for issue in result.issues
    )


def test_complete_standalone_sentence_has_no_context_issue():
    unit = _unit("Expulsion is the final punishment.")
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.NO_CONTEXT_ISSUE
        for issue in result.issues
    )


def test_incomplete_sentence_tail_has_definite_or_likely_diagnostic():
    unit = _unit(
        "to the Vice-Chancellor",
        unit_type=UnitType.CONTINUATION,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code in (
            ValidationIssueCode.INCOMPLETE_SOURCE_UNIT,
            ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
            ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT,
        )
        for issue in result.issues
    )


def test_missing_preceding_subject_is_likely_dependency():
    unit = _unit(
        "It shall report the decision to the student.",
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY
        for issue in result.issues
    )


def test_independent_numbered_item_is_complete():
    unit = _unit(
        "3. Expulsion.",
        unit_type=UnitType.NUMBERED_ITEM,
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert not any(
        issue.code is ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT
        for issue in result.issues
    )


def test_numbered_item_requiring_context_is_definite_incomplete():
    unit = _unit(
        "1. Cancellation for a specified",
        unit_type=UnitType.NUMBERED_ITEM,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT
        and issue.severity is ValidationIssueSeverity.DEFINITE
        for issue in result.issues
    )


def test_table_row_nearby_column_heading_is_reported_as_nearby_context():
    full_text = "Acts | Penalties\nRow 1 | Expulsion."
    unit = _unit(
        "Expulsion.",
        full_text=full_text,
        start=full_text.find("Expulsion."),
        unit_type=UnitType.TABLE_ROW,
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code in (
            ValidationIssueCode.TABLE_FRAGMENT_USED_AS_EVIDENCE,
            ValidationIssueCode.CONTEXT_AVAILABLE_NEARBY,
            ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY,
        )
        for issue in result.issues
    )


def test_bullet_with_missing_introduction_is_likely_dependent():
    full_text = "•Penalty begins here"
    unit = _unit(
        "•Penalty begins here",
        full_text=full_text,
        start=0,
        unit_type=UnitType.TABLE_ROW,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))

    assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert any(
        issue.code is ValidationIssueCode.TABLE_FRAGMENT_USED_AS_EVIDENCE
        for issue in result.issues
    )


def test_pronoun_reference_is_likely_context_dependency():
    unit = _unit(
        "It shall be imposed by the competent authority.",
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY
        and issue.severity is ValidationIssueSeverity.LIKELY
        for issue in result.issues
    )


def test_conditional_rule_in_nearby_text_is_likely_dependency():
    full_text = "Unless the student appeals. The penalty is 5 days."
    unit = _unit(
        "The penalty is 5 days.",
        full_text=full_text,
        start=full_text.find("The penalty"),
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY
        for issue in result.issues
    )


def test_nearby_context_available_is_distinguished():
    full_text = "Written appeal. 5 working days of the service of the order."
    unit = _unit(
        "5 working days of the service of the order.",
        full_text=full_text,
        start=full_text.find("5 working"),
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.CONTEXT_AVAILABLE_NEARBY
        for issue in result.issues
    )


def test_context_missing_outside_chunk():
    unit = _unit(
        "The above penalty applies.",
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code in (
            ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY,
            ValidationIssueCode.CONTEXT_MISSING_OUTSIDE_CHUNK,
        )
        for issue in result.issues
    )


def test_multiple_quotes_keep_individual_context_diagnostics():
    first = _unit("The appeal deadline is 5 working days.", chunk_id="a")
    second = _unit("It shall be submitted to the committee.", chunk_id="b")
    result = validate_evidence(_context((first, second)))

    assert len(result.validated_evidence) == 2
    assert any(
        issue.chunk_id == "b"
        for issue in result.issues
    )


def test_source_quotation_is_not_rewritten():
    full_text = "A student may appeal within 5 working days."
    unit = _unit(
        "5 working days",
        full_text=full_text,
        start=full_text.find("5 working days"),
    )
    context = _context((unit,))
    result = validate_evidence(context)

    assert result.validated_evidence[0].quotation.exact_quotation == "5 working days"


def test_split_category_i_rule_is_not_reconstructed():
    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    raw = next(
        chunk
        for chunk in payload["chunks"]
        if chunk["chunk_id"] == "0320a43289fbdbe8"
    )
    unit = _unit(
        "1. Cancellation of admission or withdrawal of degree or denial "
        "of registration for a specified",
        chunk_id=raw["chunk_id"],
        document_name=raw["document_name"],
        section=raw["section"],
        page_number=raw["page_number"],
        full_text=raw["text"],
        start=0,
        unit_type=UnitType.NUMBERED_ITEM,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))

    assert any(
        issue.code is ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT
        for issue in result.issues
    )
    assert "period" not in result.validated_evidence[0].quotation.exact_quotation


def test_missing_item_22_is_not_reconstructed():
    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    raw = next(
        chunk
        for chunk in payload["chunks"]
        if chunk["chunk_id"] == "ff10accb8ee6929c"
    )
    start = raw["text"].find("25.")
    unit = _unit(
        raw["text"][start:],
        chunk_id=raw["chunk_id"],
        document_name=raw["document_name"],
        section=raw["section"],
        page_number=raw["page_number"],
        full_text=raw["text"],
        start=raw["text"].find("25."),
        unit_type=UnitType.NUMBERED_ITEM,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))

    assert "Possession, use, or distribution of drugs" not in (
        result.validated_evidence[0].quotation.exact_quotation
    )
