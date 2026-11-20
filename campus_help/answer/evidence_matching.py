"""Deterministic candidate evidence matching and verification diagnostics for M6.3C."""

from __future__ import annotations

import re
from collections.abc import Sequence

from ..retrieval.tokenizer import tokenize
from .models import (
    AnswerStatus,
    CandidateEvidenceMatch,
    EvidenceMatchReport,
    EvidenceRequirement,
    QuestionValidationPlan,
    RequirementMatchDiagnostics,
    ValidatedEvidence,
    ValidationIssue,
    ValidationIssueCode,
    ValidationIssueSeverity,
    ValidationResult,
)

NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[.,]\d+)*(?!\w)")

UNIT_TERMS: tuple[str, ...] = (
    "working days",
    "working day",
    "days",
    "day",
    "hours",
    "hour",
    "weeks",
    "week",
    "months",
    "month",
    "years",
    "year",
)

NEGATION_TERMS: tuple[str, ...] = (
    "not",
    "no",
    "never",
    "neither",
    "nor",
    "without",
    "non",
)

CONDITIONAL_TERMS: tuple[str, ...] = (
    "unless",
    "except",
    "provided that",
    "provided",
    "subject to",
    "only if",
    "conditional on",
    "contingent upon",
    "if",
)

MODAL_VERBS: tuple[str, ...] = (
    "may",
    "must",
    "shall",
    "can",
    "could",
    "should",
    "ought",
    "would",
    "might",
)

PREDICATE_KEYWORDS: frozenset[str] = frozenset(
    {
        "prohibited",
        "prohibit",
        "prohibits",
        "prohibition",
        "banned",
        "ban",
        "bans",
        "disallowed",
        "forbidden",
        "allowed",
        "allow",
        "allows",
        "permitted",
        "permit",
        "permits",
        "permission",
        "violation",
        "violations",
        "misconduct",
        "offence",
        "offences",
        "punished",
        "punishment",
        "punishments",
        "penalty",
        "penalties",
        "authority",
        "authorities",
        "powers",
        "power",
        "authorized",
        "empowered",
        "vested",
        "jurisdiction",
        "competent",
        "committee",
        "officer",
        "apply",
        "applies",
        "applicable",
        "applicability",
        "cover",
        "covers",
        "governed",
        "extent",
        "within",
        "deadline",
        "deadlines",
        "timeframe",
        "period",
        "limit",
    }
)


def _match_anchors_against_quotation(
    anchors: Sequence[str],
    quotation: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Classify anchors into exact matches, normalized matches, and missing anchors."""
    exact_matches: list[str] = []
    normalized_matches: list[str] = []
    missing: list[str] = []

    quotation_tokens = set(tokenize(quotation))

    for anchor in anchors:
        if not anchor.strip():
            continue

        # Exact match check: exact case and word boundaries
        exact_pattern = re.compile(rf"(?<!\w){re.escape(anchor)}(?!\w)")
        if exact_pattern.search(quotation):
            exact_matches.append(anchor)
            continue

        # Normalized match check: case-insensitive word boundary or token containment
        case_insensitive_pattern = re.compile(
            rf"(?<!\w){re.escape(anchor)}(?!\w)", re.IGNORECASE
        )
        if case_insensitive_pattern.search(quotation):
            normalized_matches.append(anchor)
            continue

        anchor_tokens = tuple(tokenize(anchor))
        if anchor_tokens and all(tok in quotation_tokens for tok in anchor_tokens):
            normalized_matches.append(anchor)
            continue

        missing.append(anchor)

    return tuple(exact_matches), tuple(normalized_matches), tuple(missing)


def _extract_numbers_and_units(
    quotation: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Extract numbers and time-unit phrases separately from quotation."""
    numbers: list[str] = []
    seen_nums: set[str] = set()
    for match in NUMBER_RE.findall(quotation):
        clean_num = match.replace(",", "").rstrip(".")
        if clean_num not in seen_nums:
            seen_nums.add(clean_num)
            numbers.append(clean_num)

    units: list[str] = []
    for unit in UNIT_TERMS:
        if re.search(rf"(?<!\w){re.escape(unit)}(?!\w)", quotation, re.IGNORECASE):
            if unit not in units:
                units.append(unit)

    return tuple(numbers), tuple(units)


def _extract_diagnostics_terms(
    quotation: str,
    terms: Sequence[str],
) -> tuple[str, ...]:
    """Find presence of specific diagnostic words or phrases in quotation."""
    found: list[str] = []
    for term in terms:
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", quotation, re.IGNORECASE):
            if term not in found:
                found.append(term)
    return tuple(found)


def _extract_predicate_indicators(
    quotation: str,
    expected_predicate: str,
) -> tuple[str, ...]:
    """Identify predicate tokens matching expected predicate or common policy predicates."""
    quotation_tokens = set(tokenize(quotation))
    expected_tokens = set(tokenize(expected_predicate))

    indicators = quotation_tokens.intersection(PREDICATE_KEYWORDS.union(expected_tokens))
    return tuple(sorted(indicators))


def _find_evidence_issues(
    evidence: ValidatedEvidence,
    all_issues: Sequence[ValidationIssue],
) -> tuple[ValidationIssue, ...]:
    """Select validation issues relevant to this specific evidence item."""
    citation = evidence.quotation.citation
    relevant: list[ValidationIssue] = []

    for issue in all_issues:
        if issue.chunk_id == citation.chunk_id:
            relevant.append(issue)
        elif issue.code in (
            ValidationIssueCode.EMPTY_EVIDENCE,
            ValidationIssueCode.SUFFICIENCY_NOT_EVALUATED,
        ):
            relevant.append(issue)

    # If evidence flagged incomplete or context-dependent without an explicit issue, add diagnostic issue
    if not evidence.is_complete and not any(
        i.code is ValidationIssueCode.INCOMPLETE_SOURCE_UNIT for i in relevant
    ):
        relevant.append(
            ValidationIssue(
                code=ValidationIssueCode.INCOMPLETE_SOURCE_UNIT,
                message="Quoted evidence is incomplete or contextually truncated",
                chunk_id=citation.chunk_id,
                source_span=citation.source_span,
                severity=ValidationIssueSeverity.DEFINITE,
            )
        )
    if evidence.is_context_dependent and not any(
        i.code is ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION for i in relevant
    ):
        relevant.append(
            ValidationIssue(
                code=ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
                message="Quoted evidence may depend on surrounding context",
                chunk_id=citation.chunk_id,
                source_span=citation.source_span,
                severity=ValidationIssueSeverity.LIKELY,
            )
        )

    return tuple(relevant)


def match_evidence_requirements(
    plan: QuestionValidationPlan,
    validated_evidence: tuple[ValidatedEvidence, ...] | Sequence[ValidatedEvidence] = (),
    issues: tuple[ValidationIssue, ...] | Sequence[ValidationIssue] = (),
    *,
    validation_result: ValidationResult | None = None,
) -> EvidenceMatchReport:
    """Match evidence requirements to candidate policy quotations conservatively.

    Preserves exact citations, source spans, requirement ordering, and quotation text.
    Flags negation, conditional, modal, and structural context hazards.
    Never verifies requirements (is_verified=False) and never returns answered.
    """
    if validation_result is not None:
        if not validated_evidence:
            validated_evidence = validation_result.validated_evidence
        if not issues:
            issues = validation_result.issues

    evidence_tuple = tuple(validated_evidence)
    issues_tuple = tuple(issues)

    all_evidence_matches: list[CandidateEvidenceMatch] = []
    requirement_diagnostics_list: list[RequirementMatchDiagnostics] = []

    total_requirements = len(plan.requirements)
    potential_support_count = 0

    # Collect unresolved context risks across supplied evidence
    unresolved_context_risks: list[ValidationIssue] = []
    for issue in issues_tuple:
        if issue.severity not in (ValidationIssueSeverity.NONE,):
            unresolved_context_risks.append(issue)

    # Iterate through requirements in deterministic plan order
    for req in plan.requirements:
        req_candidate_matches: list[CandidateEvidenceMatch] = []

        for evidence in evidence_tuple:
            quotation = evidence.quotation.exact_quotation
            citation = evidence.quotation.citation

            exact_anchors, norm_anchors, missing_anchors = _match_anchors_against_quotation(
                req.factual_anchors, quotation
            )
            matched_numbers, matched_units = _extract_numbers_and_units(quotation)
            negations = _extract_diagnostics_terms(quotation, NEGATION_TERMS)
            conditionals = _extract_diagnostics_terms(quotation, CONDITIONAL_TERMS)
            modals = _extract_diagnostics_terms(quotation, MODAL_VERBS)
            predicates = _extract_predicate_indicators(quotation, req.expected_predicate)
            ev_issues = _find_evidence_issues(evidence, issues_tuple)

            # Determine potential support (lexical candidate indicator only)
            has_anchor_overlap = bool(exact_anchors or norm_anchors)
            has_predicate_overlap = bool(predicates)

            if req.factual_anchors:
                has_potential_support = has_anchor_overlap
            else:
                has_potential_support = has_predicate_overlap

            uncertainty_reasons: list[str] = []
            if missing_anchors:
                uncertainty_reasons.append(
                    f"Missing anchor(s): {', '.join(missing_anchors)}"
                )
            if negations:
                uncertainty_reasons.append(
                    f"Negation indicator(s) present: {', '.join(negations)} (risk of inverted meaning)"
                )
            if conditionals:
                uncertainty_reasons.append(
                    f"Conditional indicator(s) present: {', '.join(conditionals)} (exception or condition clause)"
                )
            if modals:
                uncertainty_reasons.append(
                    f"Modal verb(s) present: {', '.join(modals)}"
                )
            if ev_issues:
                issue_codes = ", ".join(i.code.value for i in ev_issues)
                uncertainty_reasons.append(f"Unresolved context issue(s): {issue_codes}")
            if not has_potential_support:
                uncertainty_reasons.append("No factual anchor overlap found")

            uncertainty_reasons.append(
                "Potential lexical support only; factual entailment is unverified."
            )

            match = CandidateEvidenceMatch(
                requirement_id=req.requirement_id,
                quotation=quotation,
                citation=citation,
                exact_anchor_matches=exact_anchors,
                normalized_anchor_matches=norm_anchors,
                missing_anchors=missing_anchors,
                predicate_indicators=predicates,
                matched_numbers=matched_numbers,
                matched_units=matched_units,
                negation_indicators=negations,
                conditional_indicators=conditionals,
                modal_verbs=modals,
                context_issues=ev_issues,
                has_potential_support=has_potential_support,
                is_verified=False,
                uncertainty_reasons=tuple(uncertainty_reasons),
            )

            req_candidate_matches.append(match)
            all_evidence_matches.append(match)

        # Requirement-level summary
        req_has_support = any(m.has_potential_support for m in req_candidate_matches)
        if req_has_support:
            potential_support_count += 1

        # Missing anchors for this requirement across all candidate quotations
        if req_candidate_matches:
            all_matched = set()
            for m in req_candidate_matches:
                all_matched.update(m.matched_anchors)
            req_missing = tuple(a for a in req.factual_anchors if a not in all_matched)
        else:
            req_missing = req.factual_anchors

        if not evidence_tuple:
            diag_summary = f"No candidate evidence provided for requirement '{req.requirement_id}'"
        elif req_has_support:
            diag_summary = (
                f"Requirement '{req.requirement_id}' has potential lexical candidate(s); "
                "factual verification is unverified."
            )
        else:
            diag_summary = (
                f"Requirement '{req.requirement_id}' lacks candidate evidence support."
            )

        diag = RequirementMatchDiagnostics(
            requirement=req,
            candidate_matches=tuple(req_candidate_matches),
            has_potential_support=req_has_support,
            is_verified=False,
            missing_anchors=req_missing,
            diagnostics_summary=diag_summary,
        )
        requirement_diagnostics_list.append(diag)

    unsupported_count = total_requirements - potential_support_count

    if not plan.requirements:
        summary = "Empty or unsupported question validation plan; no requirements matched."
    elif not evidence_tuple:
        summary = (
            f"No evidence provided; all {total_requirements} requirement(s) unsupported."
        )
    else:
        summary = (
            f"{potential_support_count}/{total_requirements} requirement(s) have potential candidate "
            "support; verification engine not implemented (M6.3C diagnostic foundation)."
        )

    return EvidenceMatchReport(
        plan=plan,
        requirement_diagnostics=tuple(requirement_diagnostics_list),
        evidence_matches=tuple(all_evidence_matches),
        unresolved_context_risks=tuple(unresolved_context_risks),
        total_requirements=total_requirements,
        potential_support_count=potential_support_count,
        unsupported_count=unsupported_count,
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        is_verified=False,
        summary=summary,
    )


__all__ = [
    "match_evidence_requirements",
]
