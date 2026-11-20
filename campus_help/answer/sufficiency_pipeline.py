"""Deterministic, read-only sufficiency evaluation pipeline for M6.3D."""

from __future__ import annotations

from dataclasses import replace

from .evidence_matching import match_evidence_requirements
from .models import (
    AnswerStatus,
    AssessmentReadiness,
    EvidenceMatchReport,
    QuestionEvidenceAssessment,
    QuestionIntentType,
    QuestionValidationPlan,
    SufficiencyEvaluation,
    ValidatedEvidence,
    ValidationContext,
    ValidationIssueCode,
    ValidationIssueSeverity,
    ValidationResult,
)
from .question_planning import create_question_plan
from .sufficiency import evaluate_evidence_sufficiency
from .validation import ProvenanceValidationError, validate_evidence

CONTEXT_RISK_CODES = frozenset(
    {
        ValidationIssueCode.INCOMPLETE_SOURCE_UNIT,
        ValidationIssueCode.HEADING_USED_AS_EVIDENCE,
        ValidationIssueCode.TABLE_FRAGMENT_USED_AS_EVIDENCE,
        ValidationIssueCode.CONTINUATION_USED_AS_EVIDENCE,
        ValidationIssueCode.ISOLATED_SENTENCE_TAIL,
        ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
        ValidationIssueCode.MISSING_PARENT_CONTEXT,
        ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT,
        ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY,
        ValidationIssueCode.CONTEXT_MISSING_OUTSIDE_CHUNK,
    }
)


def evaluate_question_evidence(
    question: str,
    validation_result: ValidationResult | None = None,
    *,
    plan: QuestionValidationPlan | None = None,
    context: ValidationContext | None = None,
    require_context: bool = False,
) -> QuestionEvidenceAssessment:
    """Connect question-planning, provenance, evidence matching, and sufficiency.

    Read-only integration:
    - Never emits answered status.
    - Never marks requirements verified.
    - Preserves exact quotations and citations.
    - Classifies readiness conservatively for diagnostics.
    """
    if isinstance(question, bool) or not isinstance(question, str):
        raise TypeError("question must be a string")

    # 1. Resolve and validate QuestionValidationPlan
    if plan is not None:
        if plan.question != question:
            raise ValueError(
                f"Question plan mismatch: plan question {plan.question!r} does not match {question!r}"
            )
        # Safety invariant: Never accept caller-supplied is_verified=True as trusted
        sanitized_reqs = tuple(
            replace(r, is_verified=False) if r.is_verified else r
            for r in plan.requirements
        )
        active_plan = QuestionValidationPlan(
            question=plan.question,
            intent_type=plan.intent_type,
            requirements=sanitized_reqs,
        )
    else:
        active_plan = create_question_plan(question)

    # 2. Resolve Provenance and Validation Result Trust Boundary
    if context is None and validation_result is None:
        raise ValueError(
            "Either validation_result (ValidationResult) or context (ValidationContext) must be provided"
        )

    if context is not None:
        if context.question != question:
            raise ValueError(
                f"ValidationContext question {context.question!r} does not match question {question!r}"
            )
        trusted_result = validate_evidence(context)
        if validation_result is not None:
            if validation_result.question != question:
                raise ValueError(
                    f"ValidationResult question {validation_result.question!r} does not match question {question!r}"
                )
            if len(validation_result.validated_evidence) != len(trusted_result.validated_evidence):
                raise ProvenanceValidationError(
                    "Supplied validation_result evidence count differs from M6.1 ValidationContext validation"
                )
        active_result = trusted_result
        trust_note = "Full provenance verified against retrieved chunks via M6.1 ValidationContext."
    else:
        assert validation_result is not None
        if require_context:
            raise ValueError(
                "Direct ValidationContext is required by policy to verify full source chunk provenance."
            )
        if validation_result.question != question:
            raise ValueError(
                f"ValidationResult question {validation_result.question!r} does not match question {question!r}"
            )
        active_result = validation_result
        trust_note = "Standalone ValidationResult consumed; provenance trusted from upstream M6.1 validation step."

    # 3. Execute M6.3C Candidate Evidence Matching
    match_report = match_evidence_requirements(
        active_plan,
        active_result.validated_evidence,
        active_result.issues,
    )

    # 4. Execute M6.3A Sufficiency Evaluation
    sufficiency_eval = evaluate_evidence_sufficiency(
        question,
        active_result.validated_evidence,
        active_result.issues,
        plan=active_plan,
    )

    # 5. Diagnostic Readiness Classification
    has_context_blocker = any(
        issue.code in CONTEXT_RISK_CODES
        for issue in sufficiency_eval.blockers
    ) or any(
        not ev.is_complete or ev.is_context_dependent
        for ev in active_result.validated_evidence
    ) or any(
        issue.code in CONTEXT_RISK_CODES
        for issue in match_report.unresolved_context_risks
    )

    if (
        active_plan.intent_type is QuestionIntentType.UNSUPPORTED_OR_UNKNOWN
        or not active_plan.requirements
    ):
        readiness = AssessmentReadiness.UNSUPPORTED_INTENT
    elif not active_result.validated_evidence:
        readiness = AssessmentReadiness.NO_EVIDENCE
    elif has_context_blocker:
        readiness = AssessmentReadiness.CONTEXT_BLOCKED
    elif (
        match_report.potential_support_count == match_report.total_requirements
        and match_report.total_requirements > 0
    ):
        readiness = AssessmentReadiness.FULL_CANDIDATE_COVERAGE_UNVERIFIED
    else:
        readiness = AssessmentReadiness.PARTIAL_CANDIDATE_COVERAGE

    # 6. Diagnostic Summary
    summary = (
        f"Intent: {active_plan.intent_type.value}; "
        f"Readiness: {readiness.value}; "
        f"Candidate coverage: {match_report.potential_support_count}/{match_report.total_requirements} requirements; "
        f"Context blockers: {len(sufficiency_eval.blockers)}; "
        "Factual entailment: unverified (M6.3D fail-closed)."
    )

    return QuestionEvidenceAssessment(
        question=question,
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        is_sufficient=False,
        is_verified=False,
        readiness=readiness,
        plan=active_plan,
        validation_result=active_result,
        match_report=match_report,
        sufficiency_evaluation=sufficiency_eval,
        diagnostics_summary=summary,
        trust_boundary_note=trust_note,
    )


__all__ = [
    "evaluate_question_evidence",
    "CONTEXT_RISK_CODES",
]
