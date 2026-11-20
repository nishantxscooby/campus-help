import json

import pytest

from campus_help.answer.assembly import (
    AssemblyValidationError,
    assemble_evidence,
    format_citation,
)
from campus_help.answer.models import (
    EvidenceSelection,
    ExtractionMethod,
    SelectionDiagnostics,
    SourceSpan,
    SourceUnit,
    UnitType,
)
from campus_help.answer.evidence import score_source_units


def _source_unit(
    text: str,
    *,
    full_text: str | None = None,
    start: int = 0,
    chunk_id: str = "chunk-a",
    document_name: str = "rules.pdf",
    section: str = "Appeals",
    page_number: int = 5,
) -> SourceUnit:
    if full_text is None:
        full_text = text
    return SourceUnit(
        chunk_id=chunk_id,
        document_name=document_name,
        category="discipline",
        section=section,
        page_number=page_number,
        full_chunk_text=full_text,
        text=text,
        span=SourceSpan(start, start + len(text)),
        unit_type=UnitType.SENTENCE,
        is_complete=True,
        extraction_method=ExtractionMethod.SENTENCE_SPLIT,
    )


def _scored(unit: SourceUnit):
    return score_source_units("appeal deadline", [unit])[0]


def _selection(*units: SourceUnit) -> EvidenceSelection:
    scored = tuple(_scored(unit) for unit in units)
    diagnostics = SelectionDiagnostics(
        candidate_count=len(units),
        selected_count=len(units),
        excluded_count=0,
        deduplicated_count=0,
        max_evidence=max(1, len(units)),
    )
    return EvidenceSelection(
        selected_candidates=scored,
        excluded_candidates=(),
        diagnostics=diagnostics,
    )


def test_single_exact_quotation():
    unit = _source_unit("A written appeal is due within 5 working days.")
    draft = assemble_evidence("How do I appeal?", _selection(unit))

    assert len(draft.quotations) == 1
    assert draft.quotations[0].exact_quotation == unit.text
    assert draft.quotations[0].citation.chunk_id == "chunk-a"


def test_multiple_quotations_preserve_selection_order():
    first = _source_unit("The appeal deadline is 5 working days.", chunk_id="first")
    second = _source_unit("The Vice-Chancellor reviews appeals.", chunk_id="second")
    draft = assemble_evidence("Appeal deadline and authority", _selection(first, second))

    assert [quotation.citation.chunk_id for quotation in draft.quotations] == [
        "first",
        "second",
    ]


def test_empty_selection_produces_empty_draft():
    selection = EvidenceSelection(
        selected_candidates=(),
        excluded_candidates=(),
        diagnostics=SelectionDiagnostics(
            candidate_count=0,
            selected_count=0,
            excluded_count=0,
            deduplicated_count=0,
            max_evidence=3,
        ),
    )
    draft = assemble_evidence("Unsupported question", selection)

    assert draft.question == "Unsupported question"
    assert draft.quotations == ()


def test_exact_source_span_is_preserved():
    full_text = "Prefix. The appeal deadline is 5 working days."
    unit = _source_unit(
        "The appeal deadline is 5 working days.",
        full_text=full_text,
        start=8,
    )
    draft = assemble_evidence("Appeal deadline", _selection(unit))
    quotation = draft.quotations[0]

    exact_text = "The appeal deadline is 5 working days."
    assert quotation.citation.source_span == SourceSpan(8, 8 + len(exact_text))
    assert full_text[
        quotation.citation.source_span.start:
        quotation.citation.source_span.end
    ] == quotation.exact_quotation


def test_invalid_source_span_is_rejected():
    unit = _source_unit("Exact text.")
    object.__setattr__(unit.span, "end", 999)

    with pytest.raises(AssemblyValidationError, match="outside chunk"):
        assemble_evidence("Question", _selection(unit))


def test_mismatched_quotation_is_rejected():
    unit = _source_unit("Exact text.")
    object.__setattr__(unit, "text", "Changed text.")

    with pytest.raises(AssemblyValidationError, match="does not match"):
        assemble_evidence("Question", _selection(unit))


def test_citation_metadata_is_correct():
    unit = _source_unit(
        "A student may appeal.",
        chunk_id="appeal-123",
        document_name="STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf",
        section="6. Appeal",
        page_number=5,
    )
    draft = assemble_evidence("Appeal process", _selection(unit))
    citation = draft.quotations[0].citation

    assert citation.document_name == unit.document_name
    assert citation.section == unit.section
    assert citation.pdf_page_number == 5
    assert citation.chunk_id == unit.chunk_id
    assert citation.source_span == unit.span


def test_pdf_page_number_is_not_replaced_by_printed_label():
    unit = _source_unit("Exact policy text.", page_number=20)
    draft = assemble_evidence("Policy", _selection(unit))

    assert draft.quotations[0].citation.pdf_page_number == 20


def test_deterministic_citation_formatting():
    unit = _source_unit(
        "Exact policy text.",
        chunk_id="chunk-20",
        document_name="rules.pdf",
        section="Appeals",
        page_number=5,
    )
    draft = assemble_evidence("Policy", _selection(unit))

    from campus_help.answer.assembly import format_citation

    assert format_citation(draft.quotations[0].citation) == (
        "Document: rules.pdf\n"
        "PDF Page: 5\n"
        "Section: Appeals\n"
        "Chunk ID: chunk-20"
    )


def test_json_serialization():
    unit = _source_unit(
        "The deadline is 5 working days.",
        chunk_id="deadline",
        page_number=5,
    )
    draft = assemble_evidence("What is the deadline?", _selection(unit))
    payload = draft.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False)

    assert '"exact_quotation": "The deadline is 5 working days."' in encoded
    assert '"pdf_page_number": 5' in encoded
    assert '"chunk_id": "deadline"' in encoded
    assert '"start": 0' in encoded
    assert '"end": 31' in encoded


def test_unicode_and_punctuation_are_preserved():
    text = "The student’s appeal — including “all evidence” — is due in 5 working days."
    unit = _source_unit(text)
    draft = assemble_evidence("Unicode appeal", _selection(unit))

    assert draft.quotations[0].exact_quotation == text


def test_duplicate_text_with_different_provenance_is_preserved():
    first = _source_unit(
        "The rule applies.",
        chunk_id="chunk-a",
        page_number=3,
    )
    second = _source_unit(
        "The rule applies.",
        chunk_id="chunk-b",
        page_number=4,
    )
    draft = assemble_evidence("Rule", _selection(first, second))

    assert len(draft.quotations) == 2
    assert [item.citation.chunk_id for item in draft.quotations] == [
        "chunk-a",
        "chunk-b",
    ]
    assert [item.citation.pdf_page_number for item in draft.quotations] == [3, 4]


def test_no_text_is_invented_or_completed():
    unit = _source_unit(
        "The appeal is filed",
        full_text="The appeal is filed",
    )
    draft = assemble_evidence("Appeal", _selection(unit))

    assert draft.quotations[0].exact_quotation == "The appeal is filed"
    assert draft.quotations[0].exact_quotation != "The appeal is filed within 5 working days."


def test_draft_has_no_answerability_status():
    unit = _source_unit("Candidate policy text.")
    draft = assemble_evidence("Candidate question", _selection(unit))
    payload = draft.to_dict()

    assert "status" not in payload
    assert "answerability" not in payload
    assert "refusal" not in payload


def test_real_discipline_corpus_example():
    import json
    from pathlib import Path

    from campus_help.answer.source_units import extract_source_units
    from campus_help.hybrid.engine import HybridSearchResult

    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    raw = next(
        chunk
        for chunk in payload["chunks"]
        if chunk["chunk_id"] == "74b85be0218069f0"
    )
    chunk = HybridSearchResult(
        chunk_id=raw["chunk_id"],
        document_name=raw["document_name"],
        category=raw["category"],
        section=raw["section"],
        page_number=raw["page_number"],
        text=raw["text"],
        bm25_rank=None,
        semantic_rank=None,
        rrf_score=0.0,
    )
    units = extract_source_units([chunk])
    candidates = [
        unit
        for unit in units
        if unit.is_complete
    ]
    selection = _selection(*candidates[:2])
    draft = assemble_evidence("Appeal procedure", selection)

    assert draft.quotations
    assert all(
        quotation.citation.document_name == raw["document_name"]
        for quotation in draft.quotations
    )
    assert all(
        quotation.citation.pdf_page_number == 5
        for quotation in draft.quotations
    )
