from dataclasses import FrozenInstanceError
import pytest

from campus_help.answer.assembly import assemble_evidence
from campus_help.answer.evidence import score_source_units
from campus_help.answer.models import (
    AnswerStatus,
    EvidenceCitation,
    EvidenceRequirement,
    EvidenceSelection,
    ExtractionMethod,
    QuestionIntentType,
    QuestionValidationPlan,
    QuotedEvidence,
    SelectionDiagnostics,
    SourceSpan,
    SourceUnit,
    SufficiencyEvaluation,
    UnitType,
    ValidatedEvidence,
    ValidationContext,
    ValidationIssue,
    ValidationIssueCode,
    ValidationIssueSeverity,
    ValidationResult,
)
from campus_help.answer.sufficiency import evaluate_evidence_sufficiency
from campus_help.answer.validation import validate_evidence
from campus_help.hybrid.engine import HybridSearchResult


def _make_unit(
    text: str,
    *,
    chunk_id: str = "chunk-101",
    document_name: str = "Discipline_Rules.pdf",
    section: str = "Discipline Committee",
    page_number: int = 3,
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
        extraction_method=ExtractionMethod.SENTENCE_SPLIT,
    )


def _make_validated_evidence(
    text: str,
    *,
    chunk_id: str = "chunk-101",
    document_name: str = "Discipline_Rules.pdf",
    section: str = "Discipline Committee",
    page_number: int = 3,
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


# 1. Valid requirement model
def test_valid_requirement_model():
    req = EvidenceRequirement(
        requirement_id="req-alcohol-ban",
        description="Requirement prohibiting possession of alcohol on campus",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        factual_anchors=("alcohol", "prohibited", "campus"),
        expected_predicate="prohibited",
        is_verified=False,
    )
    assert req.requirement_id == "req-alcohol-ban"
    assert req.id == "req-alcohol-ban"
    assert req.description == "Requirement prohibiting possession of alcohol on campus"
    assert req.intent_type == QuestionIntentType.PROHIBITION_PERMISSIBILITY
    assert req.factual_anchors == ("alcohol", "prohibited", "campus")
    assert req.expected_predicate == "prohibited"
    assert req.is_verified is False
    assert req.category == "prohibition_permissibility"

    as_dict = req.to_dict()
    assert as_dict["requirement_id"] == "req-alcohol-ban"
    assert as_dict["intent_type"] == "prohibition_permissibility"
    assert as_dict["is_verified"] is False
    assert as_dict["factual_anchors"] == ["alcohol", "prohibited", "campus"]


# 2. Invalid requirement ID
@pytest.mark.parametrize("invalid_id", ["", "   ", "\t\n", None, 123, True])
def test_invalid_requirement_id(invalid_id):
    with pytest.raises((ValueError, TypeError)):
        EvidenceRequirement(
            requirement_id=invalid_id,
            description="Valid description",
            intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        )


# 3. Duplicate requirement IDs
def test_duplicate_requirement_ids():
    req1 = EvidenceRequirement(
        requirement_id="dup-req-1",
        description="First rule requirement",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
    )
    req2 = EvidenceRequirement(
        requirement_id="dup-req-1",
        description="Second rule requirement with same ID",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
    )
    with pytest.raises(ValueError, match="Duplicate requirement ID"):
        QuestionValidationPlan(
            question="Who handles student discipline?",
            intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
            requirements=(req1, req2),
        )


# 4. Empty plan
def test_empty_plan():
    plan = QuestionValidationPlan(
        question="What is the general procedure?",
        intent_type=QuestionIntentType.POLICY_APPLICABILITY,
        requirements=(),
    )
    assert len(plan.requirements) == 0

    evidence = (
        _make_validated_evidence("General procedures apply to all students."),
    )
    evaluation = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=evidence,
        issues=(),
        plan=plan,
    )

    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert evaluation.unverified_requirements == ()
    assert evaluation.verified_requirements == ()
    assert "no evidence requirements" in evaluation.reason.lower()


# 5. Single requirement
def test_single_requirement():
    req = EvidenceRequirement(
        requirement_id="req-authority",
        description="Authority authorized to issue penalties",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
        factual_anchors=("Discipline Committee", "authority"),
        expected_predicate="authorizes_penalty",
    )
    plan = QuestionValidationPlan(
        question="Which authority issues penalties?",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
        requirements=(req,),
    )
    evidence = (
        _make_validated_evidence("The Discipline Committee may impose penalties."),
    )
    evaluation = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=evidence,
        issues=(),
        plan=plan,
    )

    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert len(evaluation.unverified_requirements) == 1
    assert evaluation.unverified_requirements[0].requirement_id == "req-authority"
    assert evaluation.unverified_requirements[0].is_verified is False
    assert evaluation.verified_requirements == ()


# 6. Multiple requirements
def test_multiple_requirements():
    req1 = EvidenceRequirement(
        requirement_id="req-deadline-filing",
        description="Filing deadline for appeal",
        intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
        factual_anchors=("appeal", "days"),
        expected_predicate="filing_deadline",
    )
    req2 = EvidenceRequirement(
        requirement_id="req-appellate-authority",
        description="Authority to which appeal is addressed",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
        factual_anchors=("Vice Chancellor", "appeal"),
        expected_predicate="receives_appeal",
    )
    plan = QuestionValidationPlan(
        question="What is the deadline and authority for appeals?",
        intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
        requirements=(req1, req2),
    )
    evidence = (
        _make_validated_evidence("An appeal may be filed within 15 days."),
        _make_validated_evidence("Appeals shall be submitted to the Vice Chancellor."),
    )
    evaluation = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=evidence,
        issues=(),
        plan=plan,
    )

    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert len(evaluation.unverified_requirements) == 2
    # Verify deterministic ordering matches plan requirements
    assert evaluation.unverified_requirements[0].requirement_id == "req-deadline-filing"
    assert evaluation.unverified_requirements[1].requirement_id == "req-appellate-authority"
    assert all(not r.is_verified for r in evaluation.unverified_requirements)
    assert evaluation.verified_requirements == ()


# 7. Empty evidence
def test_empty_evidence():
    req = EvidenceRequirement(
        requirement_id="req-ragging-ban",
        description="Explicit ban on ragging",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
    )
    plan = QuestionValidationPlan(
        question="Is ragging banned?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(req,),
    )
    evaluation = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=(),
        issues=(),
        plan=plan,
    )

    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert len(evaluation.unverified_requirements) == 1
    assert any(b.code == ValidationIssueCode.EMPTY_EVIDENCE for b in evaluation.blockers)
    assert any(i.code == ValidationIssueCode.EMPTY_EVIDENCE for i in evaluation.issues)


# 8. Unknown question intent
def test_unknown_question_intent():
    req = EvidenceRequirement(
        requirement_id="req-unknown",
        description="Requirement for unclassified question",
        intent_type=QuestionIntentType.UNSUPPORTED_OR_UNKNOWN,
    )
    plan = QuestionValidationPlan(
        question="What is the meaning of campus life?",
        intent_type=QuestionIntentType.UNSUPPORTED_OR_UNKNOWN,
        requirements=(req,),
    )
    evidence = (_make_validated_evidence("Campus life involves academic and extracurricular activities."),)
    evaluation = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=evidence,
        issues=(),
        plan=plan,
    )

    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert "unsupported or unknown" in evaluation.reason.lower()
    assert len(evaluation.unverified_requirements) == 1
    assert evaluation.verified_requirements == ()


# 9. Unsupported question intent
def test_unsupported_question_intent():
    # Calling evaluate_evidence_sufficiency with plan=None represents unclassified/unsupported intent
    evidence = (_make_validated_evidence("Some policy text"),)
    evaluation = evaluate_evidence_sufficiency(
        question="How do I get a scholarship?",
        validated_evidence=evidence,
        issues=(),
        plan=None,
    )

    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert evaluation.plan is None
    assert evaluation.unverified_requirements == ()
    assert evaluation.verified_requirements == ()
    assert "unknown or unsupported" in evaluation.reason.lower()


# 10. Structurally valid evidence remaining unverified
def test_structurally_valid_evidence_remaining_unverified():
    req = EvidenceRequirement(
        requirement_id="req-smoking-prohibition",
        description="Prohibition of smoking on university premises",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        factual_anchors=("smoking", "prohibited"),
        expected_predicate="prohibited",
        is_verified=False,
    )
    plan = QuestionValidationPlan(
        question="Is smoking allowed on campus?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(req,),
    )
    evidence = (
        _make_validated_evidence(
            "Smoking is strictly prohibited on all university premises.",
            is_complete=True,
            is_context_dependent=False,
        ),
    )
    issues = (
        ValidationIssue(
            code=ValidationIssueCode.NO_CONTEXT_ISSUE,
            message="No obvious structural context dependency was detected",
            severity=ValidationIssueSeverity.NONE,
        ),
        ValidationIssue(
            code=ValidationIssueCode.SUFFICIENCY_NOT_EVALUATED,
            message="Provenance and structure are valid; answer sufficiency was not evaluated",
            severity=ValidationIssueSeverity.NONE,
        ),
    )
    evaluation = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=evidence,
        issues=issues,
        plan=plan,
    )

    # Structurally valid evidence must NEVER automatically verify requirements in M6.3A
    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert len(evaluation.verified_requirements) == 0
    assert len(evaluation.unverified_requirements) == 1
    assert evaluation.unverified_requirements[0].is_verified is False
    # NON_BLOCKING_CODES should not appear in blockers
    assert len(evaluation.blockers) == 0
    # but remain in all issues
    assert len(evaluation.issues) == 2


# 11. Context-risk blocker preservation
def test_context_risk_blocker_preservation():
    req = EvidenceRequirement(
        requirement_id="req-penalties",
        description="List of applicable penalties",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
    )
    plan = QuestionValidationPlan(
        question="What penalties may be imposed?",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
        requirements=(req,),
    )
    evidence = (
        _make_validated_evidence(
            "and may impose a fine or suspension.",
            is_complete=False,
            is_context_dependent=True,
        ),
    )
    issues = (
        ValidationIssue(
            code=ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
            message="The quotation may continue or depend on earlier parent context",
            chunk_id="chunk-101",
            severity=ValidationIssueSeverity.LIKELY,
        ),
        ValidationIssue(
            code=ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY,
            message="Possible cross-reference or pronoun dependency",
            chunk_id="chunk-101",
            severity=ValidationIssueSeverity.LIKELY,
        ),
        ValidationIssue(
            code=ValidationIssueCode.MISSING_PARENT_CONTEXT,
            message="Parent text appears to continue across quotation boundary",
            chunk_id="chunk-101",
            severity=ValidationIssueSeverity.UNRESOLVED,
        ),
    )
    evaluation = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=evidence,
        issues=issues,
        plan=plan,
    )

    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert len(evaluation.blockers) >= 3
    blocker_codes = {b.code for b in evaluation.blockers}
    assert ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION in blocker_codes
    assert ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY in blocker_codes
    assert ValidationIssueCode.MISSING_PARENT_CONTEXT in blocker_codes
    assert any(b.chunk_id == "chunk-101" for b in evaluation.blockers)


# 12. Deterministic output
def test_deterministic_output():
    req1 = EvidenceRequirement(
        requirement_id="req-1",
        description="First requirement",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
    )
    req2 = EvidenceRequirement(
        requirement_id="req-2",
        description="Second requirement",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
    )
    plan = QuestionValidationPlan(
        question="Is it prohibited?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(req1, req2),
    )
    evidence = (
        _make_validated_evidence("Possession is prohibited on campus."),
    )

    evaluations = [
        evaluate_evidence_sufficiency(
            question=plan.question,
            validated_evidence=evidence,
            issues=(),
            plan=plan,
        )
        for _ in range(5)
    ]

    for ev in evaluations[1:]:
        assert ev.status == evaluations[0].status
        assert ev.is_sufficient == evaluations[0].is_sufficient
        assert ev.unverified_requirements == evaluations[0].unverified_requirements
        assert ev.verified_requirements == evaluations[0].verified_requirements
        assert ev.blockers == evaluations[0].blockers
        assert ev.issues == evaluations[0].issues
        assert ev.reason == evaluations[0].reason
        assert ev.to_dict() == evaluations[0].to_dict()


# 13. Immutable models
def test_immutable_models():
    req = EvidenceRequirement(
        requirement_id="req-immut",
        description="Immutable requirement",
        intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
        factual_anchors=("days",),
    )
    with pytest.raises(FrozenInstanceError):
        req.requirement_id = "modified-id"  # type: ignore

    with pytest.raises(FrozenInstanceError):
        req.is_verified = True  # type: ignore

    plan = QuestionValidationPlan(
        question="Immutable plan question?",
        intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
        requirements=(req,),
    )
    with pytest.raises(FrozenInstanceError):
        plan.question = "modified question"  # type: ignore

    eval_result = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=(),
        issues=(),
        plan=plan,
    )
    with pytest.raises(FrozenInstanceError):
        eval_result.status = AnswerStatus.ANSWERED  # type: ignore

    with pytest.raises(FrozenInstanceError):
        eval_result.is_sufficient = True  # type: ignore


# 14. No quotation rewriting
def test_no_quotation_rewriting():
    raw_text = "  Section 4.1: Possession of narcotics is strictly prohibited.  \n"
    citation = EvidenceCitation(
        document_name="Rules.pdf",
        section="Prohibited Conduct",
        pdf_page_number=4,
        chunk_id="chunk-42",
        source_span=SourceSpan(10, 10 + len(raw_text)),
    )
    quoted = QuotedEvidence(exact_quotation=raw_text, citation=citation)
    validated = ValidatedEvidence(
        quotation=quoted,
        is_complete=True,
        is_context_dependent=False,
    )
    plan = QuestionValidationPlan(
        question="Are narcotics prohibited?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-narcotics",
                description="Narcotics prohibition",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
            ),
        ),
    )
    evaluation = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=(validated,),
        issues=(),
        plan=plan,
    )

    # Output quotation and citation must be identical object / byte content without alteration
    out_evidence = evaluation.validated_evidence[0]
    assert out_evidence.quotation.exact_quotation == raw_text
    assert out_evidence.quotation.citation.document_name == "Rules.pdf"
    assert out_evidence.quotation.citation.section == "Prohibited Conduct"
    assert out_evidence.quotation.citation.pdf_page_number == 4
    assert out_evidence.quotation.citation.chunk_id == "chunk-42"
    assert out_evidence.quotation.citation.source_span == SourceSpan(10, 10 + len(raw_text))


# 15. No automatic answered status
def test_no_automatic_answered_status():
    req = EvidenceRequirement(
        requirement_id="req-full-match",
        description="Complete match for prohibition",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        factual_anchors=("ragging", "strictly", "prohibited"),
        expected_predicate="prohibited",
    )
    plan = QuestionValidationPlan(
        question="Is ragging strictly prohibited?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(req,),
    )
    evidence = (
        _make_validated_evidence(
            "Ragging in any form is strictly prohibited on the University campus.",
            is_complete=True,
            is_context_dependent=False,
        ),
    )
    evaluation = evaluate_evidence_sufficiency(
        question=plan.question,
        validated_evidence=evidence,
        issues=(),
        plan=plan,
    )

    # Must never return answered in M6.3A
    assert evaluation.status != AnswerStatus.ANSWERED
    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert len(evaluation.verified_requirements) == 0


# 16. Compatibility with existing M6.1 and M6.2 models
def test_compatibility_with_m61_and_m62_models():
    unit = _make_unit("Ragging in any form is strictly prohibited on campus.")
    selected = score_source_units("ragging prohibited", [unit])[0]
    selection = EvidenceSelection(
        selected_candidates=(selected,),
        excluded_candidates=(),
        diagnostics=SelectionDiagnostics(
            candidate_count=1,
            selected_count=1,
            excluded_count=0,
            deduplicated_count=0,
            max_evidence=3,
        ),
    )
    draft = assemble_evidence("Is ragging prohibited?", selection)
    context = ValidationContext(
        question="Is ragging prohibited?",
        retrieved_chunks=(_retrieved(unit),),
        selection=selection,
        draft=draft,
    )

    # Run M6.1 validation
    val_result = validate_evidence(context)
    assert isinstance(val_result, ValidationResult)
    assert len(val_result.validated_evidence) == 1

    # Plan
    plan = QuestionValidationPlan(
        question=context.question,
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-ragging",
                description="Ragging prohibition rule",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("ragging", "prohibited"),
            ),
        ),
    )

    # Pass validation_result directly or unpacked
    eval_direct = evaluate_evidence_sufficiency(
        question=val_result.question,
        validated_evidence=val_result.validated_evidence,
        issues=val_result.issues,
        plan=plan,
    )
    eval_via_result = evaluate_evidence_sufficiency(
        question="",
        validation_result=val_result,
        plan=plan,
    )

    assert eval_direct.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert eval_direct.is_sufficient is False
    assert len(eval_direct.validated_evidence) == 1
    assert eval_direct.validated_evidence[0].quotation.exact_quotation == unit.text
    assert eval_direct == eval_via_result
    assert eval_direct.pending_requirements == eval_direct.unverified_requirements
    assert eval_direct.structural_blockers == eval_direct.blockers
