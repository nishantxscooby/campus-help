from dataclasses import FrozenInstanceError
import pytest

from campus_help.answer.evidence_matching import match_evidence_requirements
from campus_help.answer.models import (
    AnswerStatus,
    CandidateEvidenceMatch,
    EvidenceCitation,
    EvidenceMatchReport,
    EvidenceRequirement,
    QuestionIntentType,
    QuestionValidationPlan,
    QuotedEvidence,
    RequirementMatchDiagnostics,
    SourceSpan,
    SufficiencyEvaluation,
    ValidatedEvidence,
    ValidationIssue,
    ValidationIssueCode,
    ValidationIssueSeverity,
)
from campus_help.answer.question_planning import create_question_plan
from campus_help.answer.sufficiency import evaluate_evidence_sufficiency


def _make_evidence(
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


# 1. Exact anchor match
def test_exact_anchor_match():
    plan = QuestionValidationPlan(
        question="Is gambling prohibited in the hostel?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-gambling",
                description="Gambling prohibition rule",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("gambling", "hostel"),
            ),
        ),
    )
    ev = _make_evidence("Gambling is strictly prohibited in the hostel premises.")
    report = match_evidence_requirements(plan, (ev,))

    assert len(report.evidence_matches) == 1
    match = report.evidence_matches[0]
    # "hostel" matches exactly
    assert "hostel" in match.exact_anchor_matches
    # "gambling" matches (case-normalized: "Gambling" in text vs "gambling" in anchor)
    assert "gambling" in match.matched_anchors
    assert len(match.missing_anchors) == 0
    assert match.has_potential_support is True
    assert match.is_verified is False


# 2. Normalized lexical match
def test_normalized_lexical_match():
    plan = QuestionValidationPlan(
        question="Do the rules apply to part-time students?",
        intent_type=QuestionIntentType.POLICY_APPLICABILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-part-time",
                description="Rule for part-time students",
                intent_type=QuestionIntentType.POLICY_APPLICABILITY,
                factual_anchors=("part-time", "Students"),
            ),
        ),
    )
    # Text has "PART-TIME" and lowercase "students"
    ev = _make_evidence("The rules govern all PART-TIME students admitted to the university.")
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert "part-time" in match.normalized_anchor_matches
    assert "Students" in match.normalized_anchor_matches
    assert len(match.missing_anchors) == 0
    assert match.has_potential_support is True


# 3. Missing anchor
def test_missing_anchor():
    plan = QuestionValidationPlan(
        question="Is smoking permitted in hostel rooms?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-smoking-hostel",
                description="Smoking in hostel room",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("smoking", "hostel", "balcony"),
            ),
        ),
    )
    ev = _make_evidence("Smoking is prohibited on campus.")
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert "smoking" in match.matched_anchors
    assert "hostel" in match.missing_anchors
    assert "balcony" in match.missing_anchors


# 4. Multiple requirements
def test_multiple_requirements():
    plan = QuestionValidationPlan(
        question="Who has authority to impose penalties and what penalties apply?",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-auth",
                description="Authority entity",
                intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
                factual_anchors=("Discipline Committee", "authority"),
            ),
            EvidenceRequirement(
                requirement_id="req-penalty",
                description="Penalties mandate",
                intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
                factual_anchors=("penalties", "fine", "suspension"),
            ),
        ),
    )
    ev = _make_evidence("The Discipline Committee may impose penalties including a fine.")
    report = match_evidence_requirements(plan, (ev,))

    assert len(report.requirement_diagnostics) == 2
    # Requirement ordering preserved
    assert report.requirement_diagnostics[0].requirement.requirement_id == "req-auth"
    assert report.requirement_diagnostics[1].requirement.requirement_id == "req-penalty"


# 5. Multiple quotations
def test_multiple_quotations():
    plan = QuestionValidationPlan(
        question="Is alcohol prohibited on campus?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-alcohol",
                description="Alcohol prohibition",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("alcohol", "prohibited"),
            ),
        ),
    )
    ev1 = _make_evidence("Alcohol possession is strictly prohibited.", chunk_id="chunk-1")
    ev2 = _make_evidence("Students found intoxicated will face disciplinary action.", chunk_id="chunk-2")
    report = match_evidence_requirements(plan, (ev1, ev2))

    assert len(report.evidence_matches) == 2
    # Evidence ordering preserved
    assert report.evidence_matches[0].citation.chunk_id == "chunk-1"
    assert report.evidence_matches[1].citation.chunk_id == "chunk-2"
    assert report.evidence_matches[0].has_potential_support is True


# 6. Empty evidence
def test_empty_evidence():
    plan = QuestionValidationPlan(
        question="Is gambling prohibited?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-gambling",
                description="Gambling prohibition",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("gambling",),
            ),
        ),
    )
    report = match_evidence_requirements(plan, ())

    assert len(report.evidence_matches) == 0
    assert len(report.requirement_diagnostics) == 1
    assert report.requirement_diagnostics[0].has_potential_support is False
    assert report.potential_support_count == 0
    assert report.unsupported_count == 1
    assert "No evidence provided" in report.summary


# 7. Empty plan
def test_empty_plan():
    plan = QuestionValidationPlan(
        question="General procedure?",
        intent_type=QuestionIntentType.POLICY_APPLICABILITY,
        requirements=(),
    )
    ev = _make_evidence("Some procedure text.")
    report = match_evidence_requirements(plan, (ev,))

    assert len(report.requirement_diagnostics) == 0
    assert len(report.evidence_matches) == 0
    assert report.total_requirements == 0
    assert report.potential_support_count == 0


# 8. Unknown intent
def test_unknown_intent():
    plan = QuestionValidationPlan(
        question="What is the weather like?",
        intent_type=QuestionIntentType.UNSUPPORTED_OR_UNKNOWN,
        requirements=(),
    )
    ev = _make_evidence("It is sunny.")
    report = match_evidence_requirements(plan, (ev,))

    assert report.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert report.is_verified is False
    assert report.total_requirements == 0


# 9. Number and unit handling
def test_number_and_unit_handling():
    plan = QuestionValidationPlan(
        question="How many days are allowed to appeal a penalty?",
        intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-appeal-deadline",
                description="Appeal deadline duration",
                intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
                factual_anchors=("appeal", "days"),
                expected_predicate="explicit_duration_and_unit",
            ),
        ),
    )
    ev = _make_evidence("An appeal must be submitted within 15 working days of the order.")
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert "15" in match.matched_numbers
    assert "working days" in match.matched_units or "days" in match.matched_units
    # Numbers and units tracked in separate tuple fields
    assert match.matched_numbers == ("15",)


# 10. Negation indicators
def test_negation_indicators():
    plan = QuestionValidationPlan(
        question="Is cooking allowed in hostel rooms?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-cooking",
                description="Cooking allowance",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("cooking", "hostel"),
            ),
        ),
    )
    ev = _make_evidence("Cooking is not permitted under any circumstances in hostel rooms.")
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert "not" in match.negation_indicators
    assert any("Negation indicator(s) present" in r for r in match.uncertainty_reasons)


# 11. Conditional indicators
def test_conditional_indicators():
    plan = QuestionValidationPlan(
        question="Can students hold a sit-in?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-sitin",
                description="Sit-in permission",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("sit-in",),
            ),
        ),
    )
    ev = _make_evidence("Students may hold a sit-in provided that prior intimation is given, unless prohibited.")
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert "provided that" in match.conditional_indicators or "provided" in match.conditional_indicators
    assert "unless" in match.conditional_indicators
    assert any("Conditional indicator(s) present" in r for r in match.uncertainty_reasons)


# 12. Modal verbs
def test_modal_verbs():
    plan = QuestionValidationPlan(
        question="Who may impose a fine?",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-fine",
                description="Authority to fine",
                intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
                factual_anchors=("fine",),
            ),
        ),
    )
    ev = _make_evidence("The committee shall examine witnesses and must report recommendations.")
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert "shall" in match.modal_verbs
    assert "must" in match.modal_verbs


# 13. High lexical overlap without entailment
def test_high_lexical_overlap_without_entailment():
    plan = QuestionValidationPlan(
        question="Is gambling prohibited in the hostel?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-gambling-ban",
                description="Gambling prohibition",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("gambling", "hostel", "prohibited"),
            ),
        ),
    )
    # Shares terms "gambling", "hostel", but says discussions are held, not that it is prohibited
    ev = _make_evidence("Discussions regarding gambling prevention were scheduled for each hostel.")
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert "gambling" in match.matched_anchors
    assert "hostel" in match.matched_anchors
    assert "prohibited" in match.missing_anchors
    # Must NOT claim verified entailment
    assert match.is_verified is False
    assert report.is_verified is False


# 14. Contradictory wording with similar tokens
def test_contradictory_wording_with_similar_tokens():
    plan = QuestionValidationPlan(
        question="Is gambling prohibited in the hostel?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-gambling",
                description="Gambling prohibited",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("gambling", "prohibited"),
            ),
        ),
    )
    # Contradictory negation
    ev = _make_evidence("Recreational gambling is not prohibited during annual festival days.")
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert "not" in match.negation_indicators
    # Never claim verified
    assert match.is_verified is False


# 15. Unrelated passage sharing topic terms
def test_unrelated_passage_sharing_topic_terms():
    plan = QuestionValidationPlan(
        question="What is the tuition fee deadline for this semester?",
        intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-tuition-deadline",
                description="Tuition fee deadline",
                intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
                factual_anchors=("tuition", "fee", "deadline"),
            ),
        ),
    )
    # Shares topic word "semester" / "university"
    ev = _make_evidence("A student registered for this semester must observe discipline rules.")
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert "tuition" in match.missing_anchors
    assert "fee" in match.missing_anchors
    assert "deadline" in match.missing_anchors
    assert match.has_potential_support is False


# 16. Context-risk preservation
def test_context_risk_preservation():
    plan = QuestionValidationPlan(
        question="Is alcohol prohibited?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-alcohol",
                description="Alcohol prohibition",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("alcohol", "prohibited"),
            ),
        ),
    )
    ev = _make_evidence(
        "and possession of alcohol is strictly prohibited.",
        is_complete=False,
        is_context_dependent=True,
    )
    issue = ValidationIssue(
        code=ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
        message="Quotation may depend on surrounding context",
        chunk_id=ev.quotation.citation.chunk_id,
        severity=ValidationIssueSeverity.LIKELY,
    )
    report = match_evidence_requirements(plan, (ev,), issues=(issue,))

    match = report.evidence_matches[0]
    assert len(match.context_issues) >= 1
    assert any(i.code == ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION for i in match.context_issues)
    assert len(report.unresolved_context_risks) >= 1
    assert any("Unresolved context issue" in r for r in match.uncertainty_reasons)


# 17. Deterministic ordering
def test_deterministic_ordering():
    plan = QuestionValidationPlan(
        question="Appeal procedure and deadline?",
        intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-z",
                description="Requirement Z",
                intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
                factual_anchors=("appeal",),
            ),
            EvidenceRequirement(
                requirement_id="req-a",
                description="Requirement A",
                intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
                factual_anchors=("days",),
            ),
        ),
    )
    ev1 = _make_evidence("Submit appeal.", chunk_id="chunk-1")
    ev2 = _make_evidence("Within 15 days.", chunk_id="chunk-2")

    reports = [match_evidence_requirements(plan, (ev1, ev2)) for _ in range(5)]
    for r in reports[1:]:
        assert r.to_dict() == reports[0].to_dict()
        assert [rd.requirement.requirement_id for rd in r.requirement_diagnostics] == ["req-z", "req-a"]


# 18. Exact citation preservation
def test_exact_citation_preservation():
    plan = QuestionValidationPlan(
        question="Is gambling prohibited?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-g",
                description="Gambling",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("gambling",),
            ),
        ),
    )
    citation = EvidenceCitation(
        document_name="Discipline_Rules.pdf",
        section="Hostel Rules",
        pdf_page_number=12,
        chunk_id="chunk-exact-99",
        source_span=SourceSpan(45, 95),
    )
    ev = ValidatedEvidence(
        quotation=QuotedEvidence("Gambling is prohibited on university premises.", citation),
        is_complete=True,
        is_context_dependent=False,
    )
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    assert match.citation.document_name == "Discipline_Rules.pdf"
    assert match.citation.section == "Hostel Rules"
    assert match.citation.pdf_page_number == 12
    assert match.citation.chunk_id == "chunk-exact-99"
    assert match.citation.source_span == SourceSpan(45, 95)


# 19. No quotation rewriting
def test_no_quotation_rewriting():
    raw_text = "  Possession of alcohol is prohibited. \n "
    plan = QuestionValidationPlan(
        question="Is alcohol prohibited?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-alc",
                description="Alcohol",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("alcohol",),
            ),
        ),
    )
    ev = _make_evidence(raw_text)
    report = match_evidence_requirements(plan, (ev,))

    match = report.evidence_matches[0]
    # Exact character sequence preserved without stripping or trimming
    assert match.quotation == raw_text


# 20. No verified requirements
def test_no_verified_requirements():
    plan = QuestionValidationPlan(
        question="Is gambling prohibited in the hostel?",
        intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-gambling",
                description="Gambling prohibition",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=("gambling", "prohibited", "hostel"),
            ),
        ),
    )
    # Perfect match with all anchors
    ev = _make_evidence("Gambling is strictly prohibited in the hostel.")
    report = match_evidence_requirements(plan, (ev,))

    assert report.is_verified is False
    assert all(not rd.is_verified for rd in report.requirement_diagnostics)
    assert all(not m.is_verified for m in report.evidence_matches)


# 21. No answered status
def test_no_answered_status():
    plan = QuestionValidationPlan(
        question="Who has authority over discipline?",
        intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
        requirements=(
            EvidenceRequirement(
                requirement_id="req-auth",
                description="Discipline authority",
                intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
                factual_anchors=("Vice Chancellor", "authority"),
            ),
        ),
    )
    ev = _make_evidence("The Vice Chancellor has sole authority over discipline.")
    report = match_evidence_requirements(plan, (ev,))

    assert report.status != AnswerStatus.ANSWERED
    assert report.status == AnswerStatus.INSUFFICIENT_EVIDENCE


# 22. Compatibility with M6.3A and M6.3B
def test_compatibility_with_m63a_and_m63b():
    question = "Is gambling prohibited in the hostel?"
    plan = create_question_plan(question)
    ev = _make_evidence("Gambling or betting in any form is prohibited on hostel premises.")

    # M6.3C matching
    match_report = match_evidence_requirements(plan, (ev,))
    assert isinstance(match_report, EvidenceMatchReport)
    assert match_report.total_requirements == len(plan.requirements)
    assert match_report.is_verified is False

    # M6.3A sufficiency evaluation
    suff_eval = evaluate_evidence_sufficiency(question, (ev,), plan=plan)
    assert isinstance(suff_eval, SufficiencyEvaluation)
    assert suff_eval.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert suff_eval.is_sufficient is False


# 23. Real Discipline PDF examples
def test_real_discipline_pdf_examples():
    # Example 1: Section 2 Policy Applicability (verified on page 2 of Discipline Rules)
    q1 = "Do the discipline rules apply if a student commits misconduct outside the university campus?"
    plan1 = create_question_plan(q1)
    ev1 = _make_evidence(
        "These rules shall apply to all students of the University, whether inside or outside the University campus.",
        document_name="STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf",
        section="Application",
        page_number=2,
    )
    report1 = match_evidence_requirements(plan1, (ev1,))
    assert report1.potential_support_count >= 1
    assert report1.is_verified is False

    # Example 2: Section on Gambling (verified on page 7 & 22)
    q2 = "Is gambling or betting prohibited on university premises?"
    plan2 = create_question_plan(q2)
    ev2 = _make_evidence(
        "Gambling or betting in any form on the University campus or using University infrastructure is prohibited.",
        document_name="STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf",
        section="Category II Misconduct",
        page_number=7,
    )
    report2 = match_evidence_requirements(plan2, (ev2,))
    assert report2.potential_support_count >= 1
    assert report2.is_verified is False

    # Example 3: Appeals (verified on page 5)
    q3 = "What is the deadline to appeal a penalty?"
    plan3 = create_question_plan(q3)
    ev3 = _make_evidence(
        "An appeal may be filed within 5 working days of the service of the penalty order.",
        document_name="STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf",
        section="Appeals",
        page_number=5,
    )
    report3 = match_evidence_requirements(plan3, (ev3,))
    assert report3.potential_support_count >= 1
    deadline_match = report3.evidence_matches[0]
    assert "5" in deadline_match.matched_numbers
    assert "working days" in deadline_match.matched_units
    assert deadline_match.is_verified is False
