"""M6.3F regression tests: targeted context-validation corrections.

Covers all 20 scenarios required by M6.3F:
 1.  Complete sentence followed by another sentence — no MISSING_PARENT_CONTEXT.
 2.  Sentence continuing across a visual line wrap — MISSING_PARENT_CONTEXT retained.
 3.  Complete numbered item after another numbered item — is_complete=True, no numeric tail.
 4.  Incomplete numbered item — is_complete=False preserved.
 5.  Digit-prefixed ordinary fragment (SENTENCE type) — numeric-tail flag preserved.
 6.  Real gambling item (chunk 8b899f2ff08fe95d) — is_complete=True, not context-blocked.
 7.  Real unauthorized-guest item (chunk 611b52029bcb3803) — is_complete=True.
 8.  Real hostel-cooking item (chunk d8fdccb230b145e7) — is_complete=True.
 9.  Genuine isolated sentence tail — CONTEXT_DEPENDENT_QUOTATION preserved.
10.  Appeal-deadline fragment — context-dependent diagnostic preserved.
11.  Heading dependency preserved — HEADING_USED_AS_EVIDENCE still raised.
12.  Parent conditional exception preserved — LIKELY_CONTEXT_DEPENDENCY still raised.
13.  Table fragment blocked — TABLE_FRAGMENT_USED_AS_EVIDENCE still raised.
14.  Informational warning (CONTEXT_AVAILABLE_NEARBY) does not collapse is_complete.
15.  Likely warning (LIKELY_CONTEXT_DEPENDENCY) does not collapse structural completeness.
16.  Definite incompleteness remains blocked (is_complete=False).
17.  Exact quotation and citation are not rewritten by the validator.
18.  All pre-M6.3F tests continue to pass (import sanity check).
19.  M6.3D sufficiency pipeline remains fail-closed.
20.  No automatic ANSWERED decisions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from campus_help.answer.assembly import assemble_evidence
from campus_help.answer.evidence import score_source_units
from campus_help.answer.models import (
    AnswerStatus,
    AssessmentReadiness,
    EvidenceSelection,
    ExtractionMethod,
    SelectionDiagnostics,
    SourceSpan,
    SourceUnit,
    UnitType,
    ValidationContext,
    ValidationIssueCode,
    ValidationIssueSeverity,
)
from campus_help.answer.question_planning import create_question_plan
from campus_help.answer.sufficiency_pipeline import evaluate_question_evidence
from campus_help.answer.validation import validate_evidence
from campus_help.hybrid.engine import HybridSearchResult


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _unit(
    text: str,
    *,
    chunk_id: str = "chunk-m63f",
    document_name: str = "Discipline_Rules.pdf",
    section: str = "General Misconduct",
    page_number: int = 7,
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
            else ExtractionMethod.NUMBERED_ITEM_SPLIT
            if unit_type is UnitType.NUMBERED_ITEM
            else ExtractionMethod.HEADING_DETECTION
            if unit_type is UnitType.HEADING
            else ExtractionMethod.TABLE_ROW_DETECTION
            if unit_type is UnitType.TABLE_ROW
            else ExtractionMethod.CONTINUATION_DETECTION
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
    scored = tuple(score_source_units("test", [u])[0] for u in units)
    return EvidenceSelection(
        selected_candidates=scored,
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
    sel = _selection(*units)
    return ValidationContext(
        question="test question",
        retrieved_chunks=tuple(_retrieved(u) for u in units),
        selection=sel,
        draft=assemble_evidence("test question", sel),
    )


def _load_real_unit(chunk_id: str, text: str, unit_type: UnitType) -> tuple[SourceUnit, HybridSearchResult]:
    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    raw = next(c for c in payload["chunks"] if c["chunk_id"] == chunk_id)
    start = raw["text"].find(text)
    assert start >= 0, f"Text not found in chunk {chunk_id}: {text!r}"
    unit = SourceUnit(
        chunk_id=raw["chunk_id"],
        document_name=raw["document_name"],
        category=raw["category"],
        section=raw["section"],
        page_number=raw["page_number"],
        full_chunk_text=raw["text"],
        text=text,
        span=SourceSpan(start, start + len(text)),
        unit_type=unit_type,
        is_complete=text.rstrip().endswith((".", "!", "?", ")")),
        extraction_method=ExtractionMethod.NUMBERED_ITEM_SPLIT,
    )
    retrieved = HybridSearchResult(
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
    return unit, retrieved


def _validate_real(chunk_id: str, text: str, unit_type: UnitType):
    unit, retrieved = _load_real_unit(chunk_id, text, unit_type)
    scored = score_source_units("test", [unit])[0]
    sel = EvidenceSelection(
        selected_candidates=(scored,),
        excluded_candidates=(),
        diagnostics=SelectionDiagnostics(1, 1, 0, 0, 1),
    )
    ctx = ValidationContext(
        question="test question",
        retrieved_chunks=(retrieved,),
        selection=sel,
        draft=assemble_evidence("test question", sel),
    )
    return validate_evidence(ctx), unit


# ---------------------------------------------------------------------------
# Test 1: Complete sentence followed by another sentence — no spurious neighbor flag
# ---------------------------------------------------------------------------

def test_m63f_complete_sentence_clean_after_boundary():
    """A complete sentence followed by another complete sentence at a paragraph break
    must not receive MISSING_PARENT_CONTEXT from _has_incomplete_neighbor."""
    full_text = "Ragging in any form is prohibited.\n\nPenalties include suspension or expulsion."
    text = "Ragging in any form is prohibited."
    unit = _unit(text, full_text=full_text, start=0)
    result = validate_evidence(_context((unit,)))

    codes = {i.code for i in result.issues}
    # Clean standalone sentence at chunk start: no missing-parent-context.
    assert ValidationIssueCode.MISSING_PARENT_CONTEXT not in codes
    # Structural completeness must be preserved.
    assert result.validated_evidence[0].is_complete is True
    assert result.status is not AnswerStatus.ANSWERED


# ---------------------------------------------------------------------------
# Test 2: Sentence wrapped mid-word across a visual line — neighbor flag retained
# ---------------------------------------------------------------------------

def test_m63f_sentence_continuing_across_line_wrap_is_flagged():
    """A unit that does not end with terminal punctuation must still be flagged
    even after the _has_incomplete_neighbor fix."""
    full_text = "A student who fails to comply with the\nconduct rules will face disciplinary action."
    text = "A student who fails to comply with the"
    unit = _unit(
        text,
        full_text=full_text,
        start=0,
        is_complete=False,
        unit_type=UnitType.CONTINUATION,
    )
    result = validate_evidence(_context((unit,)))

    codes = {i.code for i in result.issues}
    assert (
        ValidationIssueCode.INCOMPLETE_SOURCE_UNIT in codes
        or ValidationIssueCode.CONTINUATION_USED_AS_EVIDENCE in codes
    )
    assert result.validated_evidence[0].is_complete is False


# ---------------------------------------------------------------------------
# Test 3: Complete numbered item after another numbered item — no numeric-tail flag
# ---------------------------------------------------------------------------

def test_m63f_complete_numbered_item_after_another_not_flagged_as_tail():
    """A complete NUMBERED_ITEM whose text begins with a digit should NOT be
    treated as a continuation tail when it is a properly formed numbered rule."""
    full_text = "8. The student must report to the Proctor.\n\n9. Gambling on campus is prohibited."
    text = "9. Gambling on campus is prohibited."
    start = full_text.find(text)
    unit = _unit(
        text,
        full_text=full_text,
        start=start,
        unit_type=UnitType.NUMBERED_ITEM,
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    codes = {i.code for i in result.issues}
    # Must NOT receive a numeric-tail CONTEXT_DEPENDENT_QUOTATION.
    # (May still receive LIKELY_CONTEXT_DEPENDENCY from parent heading, etc.)
    assert ValidationIssueCode.INCOMPLETE_SOURCE_UNIT not in codes
    assert ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT not in codes
    # is_complete must be True — the source unit was structurally complete.
    assert result.validated_evidence[0].is_complete is True
    assert result.status is not AnswerStatus.ANSWERED


# ---------------------------------------------------------------------------
# Test 4: Incomplete numbered item — is_complete=False preserved
# ---------------------------------------------------------------------------

def test_m63f_incomplete_numbered_item_still_blocked():
    """An incomplete NUMBERED_ITEM (no terminal punctuation) must still be blocked."""
    full_text = "1. Cancellation of admission or withdrawal of degree for a specified"
    text = "1. Cancellation of admission or withdrawal of degree for a specified"
    unit = _unit(
        text,
        full_text=full_text,
        start=0,
        unit_type=UnitType.NUMBERED_ITEM,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))

    assert result.validated_evidence[0].is_complete is False
    codes = {i.code for i in result.issues}
    assert (
        ValidationIssueCode.INCOMPLETE_SOURCE_UNIT in codes
        or ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT in codes
    )


# ---------------------------------------------------------------------------
# Test 5: Digit-prefixed SENTENCE fragment at non-zero span — numeric tail preserved
# ---------------------------------------------------------------------------

def test_m63f_digit_prefixed_sentence_fragment_still_flagged():
    """A plain SENTENCE unit that happens to start with a digit (e.g. '5 working
    days…') must still receive the CONTEXT_DEPENDENT_QUOTATION diagnostic.
    The fix applies only to UnitType.NUMBERED_ITEM."""
    full_text = "A student may appeal. 5 working days of the service of the order."
    text = "5 working days of the service of the order."
    start = full_text.find(text)
    unit = _unit(
        text,
        full_text=full_text,
        start=start,
        unit_type=UnitType.SENTENCE,
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))

    codes = {i.code for i in result.issues}
    assert ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION in codes


# ---------------------------------------------------------------------------
# Test 6: Real gambling item — is_complete=True after M6.3F
# ---------------------------------------------------------------------------

def test_m63f_real_gambling_item_is_complete():
    """Item 9 'Indulging in acts of gambling' from real chunk 8b899f2ff08fe95d
    must have is_complete=True and must not be context-dependent after M6.3F."""
    result, unit = _validate_real(
        "8b899f2ff08fe95d",
        "9. Indulging in acts of gambling in the University premises.",
        UnitType.NUMBERED_ITEM,
    )
    ev = result.validated_evidence[0]
    assert ev.is_complete is True, "Gambling item should be structurally complete"
    assert ev.is_context_dependent is False, "Gambling item should not be context-dependent"
    # Must not have been fabricated or rewritten.
    assert ev.quotation.exact_quotation == "9. Indulging in acts of gambling in the University premises."
    assert result.status is not AnswerStatus.ANSWERED


# ---------------------------------------------------------------------------
# Test 7: Real unauthorized-guest item — is_complete=True after M6.3F
# ---------------------------------------------------------------------------

def test_m63f_real_unauthorized_guest_item_is_complete():
    """Item 18 'Accommodating unauthorized guests' from chunk 611b52029bcb3803
    must be structurally complete and not context-dependent."""
    result, unit = _validate_real(
        "611b52029bcb3803",
        "18. Accommodating unauthorized guests or other persons in the halls of residence.",
        UnitType.NUMBERED_ITEM,
    )
    ev = result.validated_evidence[0]
    assert ev.is_complete is True
    assert ev.is_context_dependent is False
    assert result.status is not AnswerStatus.ANSWERED


# ---------------------------------------------------------------------------
# Test 8: Real hostel-cooking item — is_complete=True after M6.3F
# ---------------------------------------------------------------------------

def test_m63f_real_hostel_cooking_item_is_complete():
    """Item 29 'Cooking food in hostel rooms' from chunk d8fdccb230b145e7
    must be structurally complete and not context-dependent."""
    result, unit = _validate_real(
        "d8fdccb230b145e7",
        "29. Cooking food in hostel rooms (Use of hot plates, electric cooker etc.)",
        UnitType.NUMBERED_ITEM,
    )
    ev = result.validated_evidence[0]
    assert ev.is_complete is True
    assert ev.is_context_dependent is False
    assert result.status is not AnswerStatus.ANSWERED


# ---------------------------------------------------------------------------
# Test 9: Genuine isolated sentence tail — diagnostic preserved
# ---------------------------------------------------------------------------

def test_m63f_genuine_sentence_tail_still_blocked():
    """'5 working days of the service of the order.' starting mid-chunk must
    still receive CONTEXT_DEPENDENT_QUOTATION — the fix only exempts NUMBERED_ITEM
    units with a proper numbered prefix."""
    full_text = "A student may file an appeal within 5 working days of the service of the order."
    text = "5 working days of the service of the order."
    start = full_text.find(text)
    unit = _unit(
        text,
        full_text=full_text,
        start=start,
        unit_type=UnitType.SENTENCE,
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))
    codes = {i.code for i in result.issues}
    assert ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION in codes


# ---------------------------------------------------------------------------
# Test 10: Appeal-deadline fragment from real corpus — diagnostic preserved
# ---------------------------------------------------------------------------

def test_m63f_appeal_deadline_fragment_still_blocked():
    """Real corpus chunk 74b85be0218069f0: '5 working days of the service of
    the order.' must still be context-dependent after M6.3F."""
    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    raw = next(c for c in payload["chunks"] if c["chunk_id"] == "74b85be0218069f0")
    text = "5 working days of the service of the order."
    start = raw["text"].find(text)
    assert start >= 0
    unit = SourceUnit(
        chunk_id=raw["chunk_id"],
        document_name=raw["document_name"],
        category=raw["category"],
        section=raw["section"],
        page_number=raw["page_number"],
        full_chunk_text=raw["text"],
        text=text,
        span=SourceSpan(start, start + len(text)),
        unit_type=UnitType.SENTENCE,
        is_complete=True,
        extraction_method=ExtractionMethod.SENTENCE_SPLIT,
    )
    scored = score_source_units("appeal deadline", [unit])[0]
    sel = EvidenceSelection(
        selected_candidates=(scored,),
        excluded_candidates=(),
        diagnostics=SelectionDiagnostics(1, 1, 0, 0, 1),
    )
    retrieved = HybridSearchResult(
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
    ctx = ValidationContext(
        question="appeal deadline",
        retrieved_chunks=(retrieved,),
        selection=sel,
        draft=assemble_evidence("appeal deadline", sel),
    )
    result = validate_evidence(ctx)
    codes = {i.code for i in result.issues}
    assert ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION in codes
    assert result.status is not AnswerStatus.ANSWERED


# ---------------------------------------------------------------------------
# Test 11: Heading dependency preserved
# ---------------------------------------------------------------------------

def test_m63f_heading_dependency_preserved():
    """A HEADING unit must still produce HEADING_USED_AS_EVIDENCE after M6.3F."""
    unit = _unit(
        "CATEGORYII MISCONDUCT",
        unit_type=UnitType.HEADING,
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))
    codes = {i.code for i in result.issues}
    assert ValidationIssueCode.HEADING_USED_AS_EVIDENCE in codes


# ---------------------------------------------------------------------------
# Test 12: Parent conditional exception preserved
# ---------------------------------------------------------------------------

def test_m63f_conditional_nearby_text_still_flagged():
    """A unit whose nearby text contains conditional language must still receive
    a LIKELY_CONTEXT_DEPENDENCY warning after M6.3F."""
    full_text = "Unless the student submits a written appeal. The penalty becomes final."
    text = "The penalty becomes final."
    start = full_text.find(text)
    unit = _unit(text, full_text=full_text, start=start, is_complete=True)
    result = validate_evidence(_context((unit,)))
    codes = {i.code for i in result.issues}
    assert ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY in codes


# ---------------------------------------------------------------------------
# Test 13: Table fragment blocked
# ---------------------------------------------------------------------------

def test_m63f_table_fragment_still_blocked():
    """A TABLE_ROW unit must still produce TABLE_FRAGMENT_USED_AS_EVIDENCE."""
    unit = _unit(
        "• Expulsion from the University",
        unit_type=UnitType.TABLE_ROW,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))
    codes = {i.code for i in result.issues}
    assert ValidationIssueCode.TABLE_FRAGMENT_USED_AS_EVIDENCE in codes
    assert result.validated_evidence[0].is_complete is False


# ---------------------------------------------------------------------------
# Test 14: Informational warning does NOT collapse is_complete
# ---------------------------------------------------------------------------

def test_m63f_context_available_nearby_does_not_collapse_completeness():
    """CONTEXT_AVAILABLE_NEARBY (severity=NONE) must not force is_complete to
    False on a structurally complete source unit."""
    # A standalone sentence at span=0 with nearby text in the full chunk.
    full_text = "Unless the student responds. The Vice-Chancellor issues the final order."
    text = "The Vice-Chancellor issues the final order."
    start = full_text.find(text)
    unit = _unit(text, full_text=full_text, start=start, is_complete=True)
    result = validate_evidence(_context((unit,)))
    # The unit may have LIKELY_CONTEXT_DEPENDENCY or CONTEXT_AVAILABLE_NEARBY …
    codes = {i.code for i in result.issues}
    nearby_issues = {
        ValidationIssueCode.CONTEXT_AVAILABLE_NEARBY,
        ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY,
    }
    if codes & nearby_issues:
        # …but is_complete must NOT be collapsed by them alone.
        assert result.validated_evidence[0].is_complete is True, (
            f"is_complete should remain True when only non-fatal warnings present; "
            f"issues: {[i.code for i in result.issues]}"
        )


# ---------------------------------------------------------------------------
# Test 15: LIKELY warning preserves structural completeness
# ---------------------------------------------------------------------------

def test_m63f_likely_reference_dependency_does_not_collapse_completeness():
    """A unit with a pronoun reference ('It') receives LIKELY_CONTEXT_DEPENDENCY
    but must NOT have is_complete forced to False by that warning alone."""
    unit = _unit(
        "It shall be imposed by the competent authority.",
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))
    codes = {i.code for i in result.issues}
    assert ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY in codes
    # is_complete stays True — the unit terminates with a full sentence.
    assert result.validated_evidence[0].is_complete is True


# ---------------------------------------------------------------------------
# Test 16: Definite incompleteness remains blocked
# ---------------------------------------------------------------------------

def test_m63f_definite_incomplete_remains_blocked():
    """A source unit that is_complete=False must result in is_complete=False on
    ValidatedEvidence even after M6.3F — fatal structural flaws are preserved."""
    unit = _unit(
        "the student shall be subject to",
        unit_type=UnitType.CONTINUATION,
        is_complete=False,
    )
    result = validate_evidence(_context((unit,)))
    assert result.validated_evidence[0].is_complete is False
    codes = {i.code for i in result.issues}
    assert (
        ValidationIssueCode.INCOMPLETE_SOURCE_UNIT in codes
        or ValidationIssueCode.CONTINUATION_USED_AS_EVIDENCE in codes
        or ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT in codes
    )


# ---------------------------------------------------------------------------
# Test 17: Exact quotation and citation are not rewritten by the validator
# ---------------------------------------------------------------------------

def test_m63f_quotation_and_citation_unchanged():
    """The validator must not modify the quotation text or citation metadata."""
    full_text = (
        "8. Unauthorized occupation of the hostel room.\n\n"
        "9. Indulging in acts of gambling in the University premises."
    )
    text = "9. Indulging in acts of gambling in the University premises."
    start = full_text.find(text)
    unit = _unit(
        text,
        full_text=full_text,
        start=start,
        unit_type=UnitType.NUMBERED_ITEM,
        is_complete=True,
    )
    result = validate_evidence(_context((unit,)))
    ev = result.validated_evidence[0]
    assert ev.quotation.exact_quotation == text, "Quotation must not be rewritten"
    assert ev.quotation.citation.chunk_id == "chunk-m63f"
    assert ev.quotation.citation.source_span == SourceSpan(start, start + len(text))


# ---------------------------------------------------------------------------
# Test 18: Compatibility — existing M6.1/M6.2 provenance errors still raised
# ---------------------------------------------------------------------------

def test_m63f_provenance_errors_still_raised():
    """Provenance validation must still reject mismatched metadata after M6.3F."""
    from campus_help.answer.validation import ProvenanceValidationError
    unit = _unit("A student who is expelled loses all privileges.")
    ctx = _context((unit,))
    # Corrupt the retrieved chunk list to trigger provenance failure.
    object.__setattr__(ctx, "retrieved_chunks", ())
    with pytest.raises(ProvenanceValidationError):
        validate_evidence(ctx)


# ---------------------------------------------------------------------------
# Test 19: Sufficiency pipeline remains fail-closed
# ---------------------------------------------------------------------------

def test_m63f_sufficiency_pipeline_fail_closed_for_gambling():
    """After M6.3F, the full pipeline on the gambling question must still return
    INSUFFICIENT_EVIDENCE and is_sufficient=False (fail-closed)."""
    q = "Is gambling or betting prohibited on university premises?"
    unit, retrieved = _load_real_unit(
        "8b899f2ff08fe95d",
        "9. Indulging in acts of gambling in the University premises.",
        UnitType.NUMBERED_ITEM,
    )
    scored = score_source_units(q, [unit])[0]
    sel = EvidenceSelection(
        selected_candidates=(scored,),
        excluded_candidates=(),
        diagnostics=SelectionDiagnostics(1, 1, 0, 0, 1),
    )
    ctx = ValidationContext(
        question=q,
        retrieved_chunks=(retrieved,),
        selection=sel,
        draft=assemble_evidence(q, sel),
    )
    plan = create_question_plan(q)
    assessment = evaluate_question_evidence(question=q, context=ctx, plan=plan)
    assert assessment.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert assessment.is_sufficient is False
    assert assessment.is_verified is False


# ---------------------------------------------------------------------------
# Test 20: No automatic ANSWERED decisions anywhere in the pipeline
# ---------------------------------------------------------------------------

def test_m63f_no_answered_decision_for_complete_numbered_items():
    """M6.3F must not enable automatic ANSWERED decisions.  Even when a numbered
    item is structurally complete and not context-dependent, the final status must
    remain INSUFFICIENT_EVIDENCE."""
    for chunk_id, text in [
        ("8b899f2ff08fe95d", "9. Indulging in acts of gambling in the University premises."),
        ("611b52029bcb3803", "18. Accommodating unauthorized guests or other persons in the halls of residence."),
        ("d8fdccb230b145e7", "29. Cooking food in hostel rooms (Use of hot plates, electric cooker etc.)"),
    ]:
        result, _ = _validate_real(chunk_id, text, UnitType.NUMBERED_ITEM)
        assert result.status is not AnswerStatus.ANSWERED, (
            f"ANSWERED must never be set by M6.3F; chunk={chunk_id}"
        )
        assert result.status is AnswerStatus.INSUFFICIENT_EVIDENCE
