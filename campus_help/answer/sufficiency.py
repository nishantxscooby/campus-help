"""Deterministic evidence sufficiency interface for M6.3A foundation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from .models import (
    AnswerStatus,
    EvidenceRequirement,
    QuestionIntentType,
    QuestionValidationPlan,
    SufficiencyEvaluation,
    ValidatedEvidence,
    ValidationIssue,
    ValidationIssueCode,
    ValidationIssueSeverity,
    ValidationResult,
)

NON_BLOCKING_CODES = frozenset(
    {
        ValidationIssueCode.NO_CONTEXT_ISSUE,
        ValidationIssueCode.SUFFICIENCY_NOT_EVALUATED,
        ValidationIssueCode.CONTEXT_AVAILABLE_NEARBY,
    }
)


def evaluate_evidence_sufficiency(
    question: str,
    validated_evidence: tuple[ValidatedEvidence, ...] | Sequence[ValidatedEvidence] = (),
    issues: tuple[ValidationIssue, ...] | Sequence[ValidationIssue] = (),
    plan: QuestionValidationPlan | None = None,
    *,
    validation_result: ValidationResult | None = None,
) -> SufficiencyEvaluation:
    """Fail-closed evidence sufficiency evaluation foundation for M6.3A.

    Never claims sufficiency, never returns AnswerStatus.ANSWERED,
    never verifies requirements without an approved verification mechanism,
    and preserves original evidence quotations and citations unmodified.
    """
    if validation_result is not None:
        if not question:
            question = validation_result.question
        if not validated_evidence:
            validated_evidence = validation_result.validated_evidence
        if not issues:
            issues = validation_result.issues

    evidence_tuple = tuple(validated_evidence)
    accumulated_issues: list[ValidationIssue] = list(issues)

    if not evidence_tuple:
        if not any(
            issue.code is ValidationIssueCode.EMPTY_EVIDENCE
            for issue in accumulated_issues
        ):
            accumulated_issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.EMPTY_EVIDENCE,
                    message="No candidate evidence was provided for sufficiency evaluation",
                    severity=ValidationIssueSeverity.DEFINITE,
                )
            )

    for item in evidence_tuple:
        if not item.is_complete:
            if not any(
                issue.code is ValidationIssueCode.INCOMPLETE_SOURCE_UNIT
                and issue.chunk_id == item.quotation.citation.chunk_id
                for issue in accumulated_issues
            ):
                accumulated_issues.append(
                    ValidationIssue(
                        code=ValidationIssueCode.INCOMPLETE_SOURCE_UNIT,
                        message="Quoted evidence is incomplete or contextually truncated",
                        chunk_id=item.quotation.citation.chunk_id,
                        source_span=item.quotation.citation.source_span,
                        severity=ValidationIssueSeverity.DEFINITE,
                    )
                )
        if item.is_context_dependent:
            if not any(
                issue.code is ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION
                and issue.chunk_id == item.quotation.citation.chunk_id
                for issue in accumulated_issues
            ):
                accumulated_issues.append(
                    ValidationIssue(
                        code=ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
                        message="Quoted evidence may depend on surrounding context",
                        chunk_id=item.quotation.citation.chunk_id,
                        source_span=item.quotation.citation.source_span,
                        severity=ValidationIssueSeverity.LIKELY,
                    )
                )

    seen_issue_keys: set[tuple[object, ...]] = set()
    deduped_issues: list[ValidationIssue] = []
    for issue in accumulated_issues:
        key = (
            issue.code,
            issue.chunk_id,
            issue.severity,
            issue.source_span.start if issue.source_span is not None else None,
            issue.source_span.end if issue.source_span is not None else None,
        )
        if key not in seen_issue_keys:
            seen_issue_keys.add(key)
            deduped_issues.append(issue)
    issues_tuple = tuple(deduped_issues)

    blockers = tuple(
        issue
        for issue in issues_tuple
        if issue.code not in NON_BLOCKING_CODES
        and issue.severity is not ValidationIssueSeverity.NONE
    )

    # Fail-closed requirement handling for M6.3A:
    # No requirement can be marked verified without an approved verification engine.
    if plan is None:
        unverified_reqs: tuple[EvidenceRequirement, ...] = ()
        verified_reqs: tuple[EvidenceRequirement, ...] = ()
        reason = (
            "No validation plan provided; question intent is unknown or unsupported."
        )
    elif plan.intent_type is QuestionIntentType.UNSUPPORTED_OR_UNKNOWN:
        unverified_reqs = tuple(
            replace(r, is_verified=False) if r.is_verified else r
            for r in plan.requirements
        )
        verified_reqs = ()
        reason = (
            "Question intent is unsupported or unknown; evidence sufficiency cannot be evaluated."
        )
    elif not plan.requirements:
        unverified_reqs = ()
        verified_reqs = ()
        reason = (
            "Validation plan defines no evidence requirements; evidence sufficiency cannot be evaluated."
        )
    else:
        unverified_reqs = tuple(
            replace(r, is_verified=False) if r.is_verified else r
            for r in plan.requirements
        )
        verified_reqs = ()
        if blockers:
            reason = (
                f"Evidence sufficiency blocked by {len(blockers)} issue(s); "
                f"{len(unverified_reqs)} requirement(s) remain unverified."
            )
        elif not evidence_tuple:
            reason = (
                f"No evidence provided; {len(unverified_reqs)} requirement(s) remain unverified."
            )
        else:
            reason = (
                f"Evidence verification engine not implemented (M6.3A foundation); "
                f"{len(unverified_reqs)} requirement(s) remain unverified."
            )

    return SufficiencyEvaluation(
        question=question,
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        is_sufficient=False,
        plan=plan,
        unverified_requirements=unverified_reqs,
        verified_requirements=verified_reqs,
        blockers=blockers,
        issues=issues_tuple,
        validated_evidence=evidence_tuple,
        reason=reason,
    )


__all__ = [
    "NON_BLOCKING_CODES",
    "EvidenceRequirement",
    "QuestionIntentType",
    "QuestionValidationPlan",
    "SufficiencyEvaluation",
    "evaluate_evidence_sufficiency",
]
