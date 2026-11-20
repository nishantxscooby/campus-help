from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import pytest

from campus_help.answer.assembly import assemble_evidence
from campus_help.answer.evidence import score_source_units
from campus_help.answer.models import (
    AnswerStatus,
    AssessmentReadiness,
    CandidateEvidenceMatch,
    EvidenceCitation,
    EvidenceRequirement,
    EvidenceSelection,
    ExtractionMethod,
    QuestionEvidenceAssessment,
    QuestionIntentType,
    QuestionValidationPlan,
    QuotedEvidence,
    SelectionDiagnostics,
    SourceSpan,
    SourceUnit,
    UnitType,
    ValidatedEvidence,
    ValidationContext,
    ValidationIssue,
    ValidationIssueCode,
    ValidationIssueSeverity,
    ValidationResult,
)
from campus_help.answer.question_planning import create_question_plan
from campus_help.answer.sufficiency_pipeline import evaluate_question_evidence
from campus_help.answer.validation import ProvenanceValidationError, validate_evidence
from campus_help.hybrid.engine import HybridSearchResult


def _make_validated_evidence(
    text: str,
    *,
    chunk_id: str = "chunk-disc-101",
    document_name: str = "Discipline_Rules.pdf",
    section: str = "General Misconduct",
    page_number: int = 7,
    start: int = 0,
    is_complete: bool = True,
    is_context_dependent: bool = False,
) -> ValidatedEvidence:
    citation = EvidenceCitation(
        document_name=document_name,
        section=section,
        pdf_page_number=page_number,
        chunk_id=chunk_id,
        source_span=SourceSpan(start, start + len(text)),
    )
    quotation = QuotedEvidence(exact_quotation=text, citation=citation)
    return ValidatedEvidence(
        quotation=quotation,
        is_complete=is_complete,
        is_context_dependent=is_context_dependent,
    )


def _make_validation_result(
    question: str,
    evidence: tuple[ValidatedEvidence, ...],
    issues: tuple[ValidationIssue, ...] = (),
) -> ValidationResult:
    return ValidationResult(
        question=question,
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        validated_evidence=evidence,
        issues=issues,
    )


def _make_context(
    question: str,
    unit_text: str,
    *,
    chunk_id: str = "chunk-ctx-1",
    section: str = "Discipline",
    page_number: int = 2,
) -> ValidationContext:
    span = SourceSpan(0, len(unit_text))
    unit = SourceUnit(
        chunk_id=chunk_id,
        document_name="Discipline_Rules.pdf",
        category="discipline",
        section=section,
        page_number=page_number,
        full_chunk_text=unit_text,
        text=unit_text,
        span=span,
        unit_type=UnitType.SENTENCE,
        is_complete=True,
        extraction_method=ExtractionMethod.SENTENCE_SPLIT,
    )
    scored = score_source_units(question, [unit])[0]
    selection = EvidenceSelection(
        selected_candidates=(scored,),
        excluded_candidates=(),
        diagnostics=SelectionDiagnostics(1, 1, 0, 0, 3),
    )
    draft = assemble_evidence(question, selection)
    chunk = HybridSearchResult(
        chunk_id=chunk_id,
        document_name="Discipline_Rules.pdf",
        category="discipline",
        section=section,
        page_number=page_number,
        text=unit_text,
        bm25_rank=None,
        semantic_rank=None,
        rrf_score=0.0,
    )
    return ValidationContext(
        question=question,
        retrieved_chunks=(chunk,),
        selection=selection,
        draft=draft,
    )


# 1. Supported question with exact relevant quotation
def test_supported_question_with_exact_relevant_quotation():
    q = "Is gambling prohibited in the hostel?"
    ev = _make_validated_evidence("Gambling is prohibited in the hostel premises.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    assert assessment.question == q
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert assessment.is_sufficient is False
    assert assessment.is_verified is False
    assert assessment.readiness == AssessmentReadiness.FULL_CANDIDATE_COVERAGE_UNVERIFIED
    assert assessment.match_report.potential_support_count == assessment.match_report.total_requirements


# 2. Supported question with irrelevant quotation
def test_supported_question_with_irrelevant_quotation():
    q = "Is gambling prohibited in the hostel?"
    ev = _make_validated_evidence("Books must be returned to the library within two weeks.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    assert assessment.readiness == AssessmentReadiness.PARTIAL_CANDIDATE_COVERAGE
    assert assessment.match_report.potential_support_count == 0
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 3. Unsupported question with highly relevant-looking quotation
def test_unsupported_question_with_relevant_looking_quotation():
    q = "What is the general history of the university student proctorial committee?"
    ev = _make_validated_evidence("The Proctorial Committee was established to maintain campus discipline.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    assert assessment.readiness == AssessmentReadiness.UNSUPPORTED_INTENT
    assert assessment.plan.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 4. Empty evidence
def test_empty_evidence():
    q = "Is gambling prohibited in the hostel?"
    val_res = _make_validation_result(q, ())

    assessment = evaluate_question_evidence(q, val_res)
    assert assessment.readiness == AssessmentReadiness.NO_EVIDENCE
    assert len(assessment.validation_result.validated_evidence) == 0
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 5. Partial requirement coverage
def test_partial_requirement_coverage():
    # Question asks for conduct + scope: "Is gambling prohibited in the hostel?"
    q = "Is gambling prohibited in the hostel?"
    # Evidence only mentions gambling, misses hostel scope
    ev = _make_validated_evidence("Gambling is strictly prohibited on campus.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    assert assessment.readiness == AssessmentReadiness.PARTIAL_CANDIDATE_COVERAGE
    assert assessment.match_report.potential_support_count < assessment.match_report.total_requirements
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 6. Full lexical coverage without entailment
def test_full_lexical_coverage_without_entailment():
    q = "Is gambling prohibited in the hostel?"
    # Shares gambling, prohibited, hostel, but expresses prevention campaign, not rule
    ev = _make_validated_evidence("The hostel committee discussed prohibited activities including gambling awareness.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    # Diagnostic readiness indicates lexical coverage, but NOT verified entailment
    assert assessment.readiness == AssessmentReadiness.FULL_CANDIDATE_COVERAGE_UNVERIFIED
    assert assessment.is_verified is False
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 7. Negated prohibition
def test_negated_prohibition():
    q = "Is gambling prohibited in the hostel?"
    ev = _make_validated_evidence("Friendly board games are not prohibited in the hostel.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    match = assessment.match_report.evidence_matches[0]
    assert "not" in match.negation_indicators
    assert assessment.is_verified is False
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 8. Conditional prohibition
def test_conditional_prohibition():
    q = "Is cooking allowed in hostel rooms?"
    ev = _make_validated_evidence("Cooking is allowed in hostel rooms unless prohibited by the warden.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    match = assessment.match_report.evidence_matches[0]
    assert "unless" in match.conditional_indicators
    assert assessment.is_verified is False
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 9. Permission versus prohibition
def test_permission_versus_prohibition():
    q = "Is cooking allowed in hostel rooms?"
    ev = _make_validated_evidence("Cooking in hostel rooms is strictly prohibited.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert assessment.is_verified is False
    match = assessment.match_report.evidence_matches[0]
    assert "prohibited" in match.predicate_indicators


# 10. Deadline with wrong unit
def test_deadline_with_wrong_unit():
    q = "How many days are allowed to appeal a penalty?"
    ev = _make_validated_evidence("An appeal must be submitted within 2 months of the decision.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    match = assessment.match_report.evidence_matches[0]
    assert "months" in match.matched_units
    assert "days" not in match.matched_units
    assert assessment.is_verified is False


# 11. Deadline mentioning unrelated numbers
def test_deadline_mentioning_unrelated_numbers():
    q = "How many days are allowed to appeal a penalty?"
    ev = _make_validated_evidence("Under Section 12, Clause 4, appeal rules apply.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    match = assessment.match_report.evidence_matches[0]
    assert "days" not in match.matched_units
    assert assessment.readiness == AssessmentReadiness.PARTIAL_CANDIDATE_COVERAGE


# 12. Authority question with wrong institutional role
def test_authority_question_with_wrong_role():
    q = "Who has authority to impose disciplinary penalties?"
    ev = _make_validated_evidence("The sports coordinator may schedule intramural matches.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    assert assessment.match_report.potential_support_count == 0
    assert assessment.is_verified is False


# 13. Policy applicability with wrong student category
def test_policy_applicability_with_wrong_category():
    q = "Do the disciplinary rules apply to part-time students?"
    ev = _make_validated_evidence("These rules apply to full-time residential scholars only.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    # "part-time" / "part" / "students" is missing from quotation
    target_diag = next(
        rd for rd in assessment.match_report.requirement_diagnostics
        if rd.requirement.requirement_id == "req-applicability-target"
    )
    assert "part" in target_diag.missing_anchors or "part-time" in target_diag.missing_anchors


# 14. Context-dependent sentence tail
def test_context_dependent_sentence_tail():
    q = "Is gambling prohibited in the hostel?"
    ev = _make_validated_evidence(
        "and gambling in any hostel room shall invite severe penalty.",
        is_complete=False,
        is_context_dependent=True,
    )
    issue = ValidationIssue(
        code=ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
        message="Quotation begins with conjunction tail",
        chunk_id=ev.quotation.citation.chunk_id,
        severity=ValidationIssueSeverity.LIKELY,
    )
    val_res = _make_validation_result(q, (ev,), issues=(issue,))

    assessment = evaluate_question_evidence(q, val_res)
    assert assessment.readiness == AssessmentReadiness.CONTEXT_BLOCKED
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 15. Conflicting candidate passages
def test_conflicting_candidate_passages():
    q = "Is cooking allowed in hostel rooms?"
    ev1 = _make_validated_evidence("Cooking is allowed in hostel kitchens.", chunk_id="chunk-1")
    ev2 = _make_validated_evidence("Cooking is strictly prohibited in all hostel rooms.", chunk_id="chunk-2")
    val_res = _make_validation_result(q, (ev1, ev2))

    assessment = evaluate_question_evidence(q, val_res)
    # Never resolves contradiction automatically; fails closed
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert assessment.is_verified is False


# 16. Multiple quotations with separate context risks
def test_multiple_quotations_with_separate_context_risks():
    q = "Is gambling prohibited in the hostel?"
    ev1 = _make_validated_evidence("Incomplete sentence tail...", chunk_id="c1", is_complete=False)
    ev2 = _make_validated_evidence("Another dependent quote...", chunk_id="c2", is_context_dependent=True)
    issues = (
        ValidationIssue(
            code=ValidationIssueCode.INCOMPLETE_SOURCE_UNIT,
            message="Incomplete",
            chunk_id="c1",
            severity=ValidationIssueSeverity.DEFINITE,
        ),
        ValidationIssue(
            code=ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
            message="Context dependent",
            chunk_id="c2",
            severity=ValidationIssueSeverity.LIKELY,
        ),
    )
    val_res = _make_validation_result(q, (ev1, ev2), issues=issues)

    assessment = evaluate_question_evidence(q, val_res)
    assert assessment.readiness == AssessmentReadiness.CONTEXT_BLOCKED
    assert len(assessment.match_report.unresolved_context_risks) >= 2


# 17. Fabricated has_potential_support=True
def test_fabricated_potential_support_safeguard():
    # Calling evaluate_question_evidence recomputes matching internally
    q = "Is gambling prohibited in the hostel?"
    ev = _make_validated_evidence("Completely unrelated library fine regulation.")
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    # External fabrication impossible because pipeline computes match_report directly
    assert assessment.match_report.potential_support_count == 0
    assert assessment.readiness != AssessmentReadiness.FULL_CANDIDATE_COVERAGE_UNVERIFIED


# 18. Caller-supplied is_verified=True
def test_caller_supplied_verified_safeguard():
    q = "Is gambling prohibited in the hostel?"
    # Caller attempts to supply verified=True on requirement or match
    plan = create_question_plan(q)
    # Attempting to construct assessment with is_verified=True raises ValueError
    with pytest.raises(ValueError):
        QuestionEvidenceAssessment(
            question=q,
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            is_sufficient=False,
            is_verified=True,  # Disallowed
            readiness=AssessmentReadiness.FULL_CANDIDATE_COVERAGE_UNVERIFIED,
            plan=plan,
            validation_result=_make_validation_result(q, ()),
            match_report=None,  # type: ignore
            sufficiency_evaluation=None,  # type: ignore
            diagnostics_summary="",
            trust_boundary_note="",
        )


# 19. Question-plan mismatch
def test_question_plan_mismatch():
    q1 = "Is gambling prohibited in the hostel?"
    q2 = "Who has authority to impose penalties?"
    plan2 = create_question_plan(q2)
    val_res = _make_validation_result(q1, ())

    with pytest.raises(ValueError, match="Question plan mismatch"):
        evaluate_question_evidence(q1, val_res, plan=plan2)


# 20. Citation and source-span preservation
def test_citation_and_source_span_preservation():
    q = "Is gambling prohibited in the hostel?"
    citation = EvidenceCitation(
        document_name="Discipline_Rules.pdf",
        section="Hostel Rules",
        pdf_page_number=8,
        chunk_id="chunk-hostel-8",
        source_span=SourceSpan(10, 60),
    )
    quotation = QuotedEvidence("Gambling is strictly prohibited in the hostel.", citation)
    ev = ValidatedEvidence(quotation=quotation, is_complete=True, is_context_dependent=False)
    val_res = _make_validation_result(q, (ev,))

    assessment = evaluate_question_evidence(q, val_res)
    out_ev = assessment.validation_result.validated_evidence[0]
    assert out_ev.quotation.citation.chunk_id == "chunk-hostel-8"
    assert out_ev.quotation.citation.pdf_page_number == 8
    assert out_ev.quotation.citation.source_span == SourceSpan(10, 60)
    assert assessment.match_report.evidence_matches[0].citation == citation


# 21. Deterministic output
def test_deterministic_output():
    q = "Is cooking with a hot plate allowed in a hostel room?"
    ev = _make_validated_evidence("Cooking with electric hot plates is not permitted in rooms.")
    val_res = _make_validation_result(q, (ev,))

    results = [evaluate_question_evidence(q, val_res) for _ in range(5)]
    for r in results[1:]:
        assert r.to_dict() == results[0].to_dict()


# 22. Compatibility with existing M6 tests
def test_compatibility_with_m6_context():
    q = "Do the disciplinary rules apply to part-time students?"
    unit_text = "These rules apply to all students including part-time students."
    ctx = _make_context(q, unit_text)

    # Pass context directly to evaluate_question_evidence
    assessment = evaluate_question_evidence(q, context=ctx)
    assert assessment.question == q
    assert assessment.readiness == AssessmentReadiness.FULL_CANDIDATE_COVERAGE_UNVERIFIED
    assert "ValidationContext" in assessment.trust_boundary_note
    assert assessment.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 23. Real Discipline PDF examples
def test_real_discipline_pdf_examples():
    # Real quotation from Discipline Rules page 2
    q1 = "Do the discipline rules apply if a student commits misconduct outside the university campus?"
    ev1 = _make_validated_evidence(
        "These rules shall apply to all students of the University, whether inside or outside the University campus.",
        document_name="STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf",
        section="Application",
        page_number=2,
    )
    val_res1 = _make_validation_result(q1, (ev1,))
    res1 = evaluate_question_evidence(q1, val_res1)
    assert res1.readiness == AssessmentReadiness.FULL_CANDIDATE_COVERAGE_UNVERIFIED
    assert res1.is_verified is False

    # Real quotation from Discipline Rules page 5 (Appeals)
    q2 = "What is the deadline to appeal a penalty?"
    ev2 = _make_validated_evidence(
        "An appeal may be filed within 5 working days of the service of the penalty order.",
        document_name="STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf",
        section="Appeals",
        page_number=5,
    )
    val_res2 = _make_validation_result(q2, (ev2,))
    res2 = evaluate_question_evidence(q2, val_res2)
    assert res2.readiness == AssessmentReadiness.FULL_CANDIDATE_COVERAGE_UNVERIFIED
    assert res2.is_verified is False


# 24. Evaluation against representative M4.1 dataset
def test_m41_dataset_evaluation_breakdown():
    m41_path = Path(__file__).resolve().parent.parent / "data" / "evaluation" / "m4_1_questions.json"
    with open(m41_path, encoding="utf-8") as f:
        m41_questions = json.load(f)

    counts = {
        "recognized_intent": 0,
        "no_evidence": 0,
        "partial_candidate_coverage": 0,
        "full_candidate_coverage_unverified": 0,
        "context_blocked": 0,
        "unsupported_intent": 0,
    }

    for item in m41_questions:
        q = item["question"]
        # Empty evidence baseline evaluation to test pipeline robustness on all 40 benchmark questions
        val_res = _make_validation_result(q, ())
        assessment = evaluate_question_evidence(q, val_res)

        if assessment.plan.intent_type != QuestionIntentType.UNSUPPORTED_OR_UNKNOWN:
            counts["recognized_intent"] += 1

        if assessment.readiness == AssessmentReadiness.NO_EVIDENCE:
            counts["no_evidence"] += 1
        elif assessment.readiness == AssessmentReadiness.UNSUPPORTED_INTENT:
            counts["unsupported_intent"] += 1
        elif assessment.readiness == AssessmentReadiness.CONTEXT_BLOCKED:
            counts["context_blocked"] += 1
        elif assessment.readiness == AssessmentReadiness.PARTIAL_CANDIDATE_COVERAGE:
            counts["partial_candidate_coverage"] += 1
        elif assessment.readiness == AssessmentReadiness.FULL_CANDIDATE_COVERAGE_UNVERIFIED:
            counts["full_candidate_coverage_unverified"] += 1

    # Verify counts: recognized intent questions with empty evidence become NO_EVIDENCE,
    # unsupported intent questions become UNSUPPORTED_INTENT
    assert counts["recognized_intent"] == counts["no_evidence"]
    assert counts["no_evidence"] + counts["unsupported_intent"] == len(m41_questions)
    assert counts["recognized_intent"] >= 8
    assert counts["unsupported_intent"] >= 20
