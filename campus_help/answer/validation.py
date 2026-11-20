"""Deterministic provenance and structural validation for M6.1."""

from __future__ import annotations

from collections.abc import Sequence
import re

from ..hybrid.engine import HybridSearchResult
from .models import (
    AnswerStatus,
    EvidenceSelection,
    ExtractiveDraft,
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


class ProvenanceValidationError(ValueError):
    """Raised when evidence cannot be traced exactly to retrieved source."""


TAIL_STARTERS = frozenset(
    {
        "and",
        "for",
        "or",
        "that",
        "the",
        "to",
        "which",
        "within",
    }
)

CONDITIONAL_TERMS = frozenset(
    {
        "unless",
        "except",
        "provided",
        "subject",
        "notwithstanding",
        "generally",
        "exception",
        "conditional",
    }
)

REFERENCE_TERMS = frozenset(
    {
        "above",
        "herein",
        "it",
        "same",
        "such",
        "that",
        "thereof",
        "thereunder",
    }
)

# Regex that matches a well-formed numbered-item prefix: "9. ", "12) ", "(b) " etc.
_NUMBERED_ITEM_PREFIX_RE = re.compile(r"^\d+[.)]\s")

# Issue codes that definitively establish structural incompleteness.
# LIKELY or NONE severity warnings must NOT collapse is_complete on their own.
_FATAL_ISSUE_CODES = frozenset(
    {
        ValidationIssueCode.INCOMPLETE_SOURCE_UNIT,
        ValidationIssueCode.CONTINUATION_USED_AS_EVIDENCE,
        ValidationIssueCode.TABLE_FRAGMENT_USED_AS_EVIDENCE,
        ValidationIssueCode.HEADING_USED_AS_EVIDENCE,
        ValidationIssueCode.ISOLATED_SENTENCE_TAIL,
        ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT,
    }
)


def _parent_context(unit: SourceUnit, radius: int = 240) -> tuple[str, str]:
    before = unit.full_chunk_text[max(0, unit.span.start - radius):unit.span.start]
    after = unit.full_chunk_text[unit.span.end:min(len(unit.full_chunk_text), unit.span.end + radius)]
    return before, after


def _has_nearby_reference(unit: SourceUnit) -> bool:
    before, after = _parent_context(unit)
    nearby = f"{before} {unit.text} {after}".lower()
    words = set(re.findall(r"[a-z]+", nearby))
    return bool(words.intersection(REFERENCE_TERMS))


def _has_nearby_condition(unit: SourceUnit) -> bool:
    before, after = _parent_context(unit)
    nearby = f"{before} {unit.text} {after}".lower()
    words = set(re.findall(r"[a-z]+", nearby))
    return bool(words.intersection(CONDITIONAL_TERMS))


def _has_incomplete_neighbor(unit: SourceUnit) -> bool:
    """Return True if the selected quotation appears to cut across a sentence boundary.

    M6.3F fix: the original ``after.lstrip().startswith(("\\n", ...))`` check was
    always False for the ``"\\n"`` sentinel because ``lstrip()`` removes every
    leading whitespace character including newlines before the ``startswith`` test.
    That meant *any* non-empty ``after`` context triggered the warning
    unconditionally.  The corrected logic inspects the raw ``after`` string for
    genuine paragraph breaks and distinguishes clean structural boundaries from
    genuine mid-sentence splits.
    """
    before, after = _parent_context(unit)
    text_rstripped = unit.text.rstrip()

    # --- Before boundary ---
    # A new numbered item always starts at a clean boundary regardless of what
    # immediately precedes it in the chunk.
    if before:
        unit_starts_numbered = bool(_NUMBERED_ITEM_PREFIX_RE.match(text_rstripped))
        if not unit_starts_numbered and not before.rstrip().endswith(
            ("\n\n", ".", "!", "?", ")", ":", ";")
        ):
            return True

    # --- After boundary ---
    if after:
        unit_ends_clean = text_rstripped.endswith((".", "!", "?", ")"))
        if not unit_ends_clean:
            # Unit is cut off mid-sentence: definite incomplete boundary.
            return True

        # Unit ends with terminal punctuation; determine whether the boundary
        # that follows is structurally clean.
        after_stripped = after.lstrip()
        if after_stripped and after_stripped[0].islower():
            # After continues with a lowercase letter → same sentence was split.
            return True

        # A paragraph break in the raw ``after`` (before stripping) is a clean
        # structural separator regardless of what follows.
        after_has_paragraph_break = "\n\n" in after[:8]

        # A new numbered item in ``after`` is also a clean structural boundary.
        after_starts_new_item = bool(_NUMBERED_ITEM_PREFIX_RE.match(after_stripped))

        # An uppercase start indicates a new sentence.
        after_starts_upper = bool(after_stripped and after_stripped[0].isupper())

        if after_has_paragraph_break or after_starts_new_item or after_starts_upper:
            return False

        # Fallback: unclear boundary — flag as potentially incomplete.
        return True

    return False


def _validate_duplicate_retrieved_chunks(
    retrieved_chunks: Sequence[HybridSearchResult],
) -> dict[str, HybridSearchResult]:
    by_id: dict[str, HybridSearchResult] = {}
    for chunk in retrieved_chunks:
        existing = by_id.get(chunk.chunk_id)
        if existing is None:
            by_id[chunk.chunk_id] = chunk
            continue
        existing_signature = (
            existing.document_name,
            existing.category,
            existing.section,
            existing.page_number,
            existing.text,
        )
        current_signature = (
            chunk.document_name,
            chunk.category,
            chunk.section,
            chunk.page_number,
            chunk.text,
        )
        if current_signature != existing_signature:
            raise ProvenanceValidationError(
                f"Duplicate chunk ID {chunk.chunk_id!r} has conflicting retrieved "
                "document metadata or text"
            )
    return by_id


def _validate_source_unit(
    unit: SourceUnit,
    retrieved_by_id: dict[str, HybridSearchResult],
) -> None:
    if unit.span.start < 0 or unit.span.end < unit.span.start:
        raise ProvenanceValidationError(
            f"Invalid source span for chunk {unit.chunk_id!r}"
        )
    if unit.span.end > len(unit.full_chunk_text):
        raise ProvenanceValidationError(
            f"Source span is outside parent text for chunk {unit.chunk_id!r}"
        )
    try:
        extracted = unit.full_chunk_text[
            unit.span.start:unit.span.end
        ]
    except (IndexError, TypeError) as exc:
        raise ProvenanceValidationError(
            f"Cannot read source span for chunk {unit.chunk_id!r}"
        ) from exc
    if extracted != unit.text:
        raise ProvenanceValidationError(
            f"Quotation does not match selected source span for chunk "
            f"{unit.chunk_id!r}"
        )

    retrieved = retrieved_by_id.get(unit.chunk_id)
    if retrieved is None:
        raise ProvenanceValidationError(
            f"Selected chunk ID {unit.chunk_id!r} is missing from retrieved chunks"
        )
    if (
        unit.document_name != retrieved.document_name
        or unit.category != retrieved.category
        or unit.section != retrieved.section
        or unit.page_number != retrieved.page_number
        or unit.full_chunk_text != retrieved.text
    ):
        raise ProvenanceValidationError(
            f"Selected source unit metadata or parent text conflicts with "
            f"retrieved chunk {unit.chunk_id!r}"
        )


def _context_dependent(unit: SourceUnit) -> tuple[bool, str | None]:
    text = unit.text.strip()
    if not text:
        return True, "Empty quotation"

    starts_lowercase = bool(text) and text[0].islower()
    first_word = text.split(maxsplit=1)[0].rstrip(".,!?;:").lower()
    starts_tail_word = first_word in TAIL_STARTERS

    # M6.3F fix: a complete NUMBERED_ITEM unit (e.g., "9. Indulging in gambling.")
    # starts with a digit but is NOT a continuation tail — it is the head of its
    # own self-contained rule.  Only suppress the flag when the unit is classified
    # as NUMBERED_ITEM *and* the text matches the structured numbered-item prefix.
    is_structured_numbered_item = unit.unit_type is UnitType.NUMBERED_ITEM and bool(
        _NUMBERED_ITEM_PREFIX_RE.match(text)
    )
    starts_numeric_tail = (
        bool(text) and text[0].isdigit() and not is_structured_numbered_item
    )

    preceding_context = ""
    if unit.span.start > 0:
        preceding_context = unit.full_chunk_text[
            max(0, unit.span.start - 160):unit.span.start
        ]

    missing_before = bool(
        unit.span.start > 0
        and preceding_context.strip()
        and not preceding_context.rstrip().endswith(("\n\n", ".", "!", "?"))
    )

    if (
        starts_lowercase
        or (unit.span.start > 0 and starts_tail_word)
        or (unit.span.start > 0 and starts_numeric_tail)
    ):
        return True, "The quotation may continue or depend on earlier parent context"
    if missing_before:
        return True, "The parent chunk may continue directly before this span"
    return False, None


def _context_sufficiency_issues(
    unit: SourceUnit,
) -> tuple[ValidationIssue, ...]:
    """Inspect only nearby text in the exact parent chunk."""
    issues: list[ValidationIssue] = []
    before, after = _parent_context(unit)
    nearby_available = bool(before.strip() or after.strip())
    context_dependent, context_message = _context_dependent(unit)
    reference_dependency = _has_nearby_reference(unit)
    has_condition = _has_nearby_condition(unit)
    incomplete_neighbor = _has_incomplete_neighbor(unit)

    if reference_dependency:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY,
                message="The quotation or nearby parent text contains a possible cross-reference or pronoun dependency",
                chunk_id=unit.chunk_id,
                source_span=unit.span,
                severity=ValidationIssueSeverity.LIKELY,
            )
        )

    if has_condition:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY,
                message="A possible condition or exception appears in the quotation or nearby parent text",
                chunk_id=unit.chunk_id,
                source_span=unit.span,
                severity=ValidationIssueSeverity.LIKELY,
            )
        )

    if incomplete_neighbor:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.MISSING_PARENT_CONTEXT,
                message="Nearby parent text appears to continue across the quotation boundary",
                chunk_id=unit.chunk_id,
                source_span=unit.span,
                severity=ValidationIssueSeverity.UNRESOLVED,
            )
        )

    if context_dependent:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
                message=context_message or "The quotation may depend on surrounding parent text",
                chunk_id=unit.chunk_id,
                source_span=unit.span,
                severity=ValidationIssueSeverity.LIKELY,
            )
        )

    if context_dependent or reference_dependency or has_condition or incomplete_neighbor:
        if nearby_available:
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.CONTEXT_AVAILABLE_NEARBY,
                    message="Potentially relevant context was found in the same retrieved parent chunk",
                    chunk_id=unit.chunk_id,
                    source_span=unit.span,
                    severity=ValidationIssueSeverity.NONE,
                )
            )
        else:
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.CONTEXT_MISSING_OUTSIDE_CHUNK,
                    message="Required context is not available in the exact parent chunk",
                    chunk_id=unit.chunk_id,
                    source_span=unit.span,
                    severity=ValidationIssueSeverity.UNRESOLVED,
                )
            )

    return tuple(issues)


def _structural_issues(
    unit: SourceUnit,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    span = unit.span

    if not unit.is_complete:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.INCOMPLETE_SOURCE_UNIT,
                message="The source unit is incomplete or may not terminate independently",
                chunk_id=unit.chunk_id,
                source_span=span,
                severity=ValidationIssueSeverity.DEFINITE,
            )
        )
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT,
                message="Known source structure does not provide a complete standalone rule",
                chunk_id=unit.chunk_id,
                source_span=span,
                severity=ValidationIssueSeverity.DEFINITE,
            )
        )
    if unit.unit_type is UnitType.HEADING:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.HEADING_USED_AS_EVIDENCE,
                message="A heading is not evidence of a policy fact",
                chunk_id=unit.chunk_id,
                source_span=span,
                severity=ValidationIssueSeverity.DEFINITE,
            )
        )
    if unit.unit_type is UnitType.TABLE_ROW:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.TABLE_FRAGMENT_USED_AS_EVIDENCE,
                message="A table fragment may require adjacent row or column context",
                chunk_id=unit.chunk_id,
                source_span=span,
                severity=ValidationIssueSeverity.DEFINITE,
            )
        )
    if unit.unit_type is UnitType.CONTINUATION:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.CONTINUATION_USED_AS_EVIDENCE,
                message="A continuation unit is not supported as a standalone quotation",
                chunk_id=unit.chunk_id,
                source_span=span,
                severity=ValidationIssueSeverity.DEFINITE,
            )
        )

    context_dependent, context_message = _context_dependent(unit)
    if context_dependent and context_message:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION,
                message=context_message,
                chunk_id=unit.chunk_id,
                source_span=span,
                severity=ValidationIssueSeverity.LIKELY,
            )
        )
    if unit.span.start > 0:
        preceding_context = unit.full_chunk_text[
            max(0, unit.span.start - 160):unit.span.start
        ]
        if (
            preceding_context.strip()
            and not preceding_context.rstrip().endswith(("\n\n", ".", "!", "?", ")", ":"))
        ):
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.MISSING_PARENT_CONTEXT,
                    message="The preceding parent text may continue directly into this span",
                    chunk_id=unit.chunk_id,
                    source_span=span,
                    severity=ValidationIssueSeverity.UNRESOLVED,
                )
            )
    if unit.unit_type is UnitType.CONTINUATION and unit.span.start > 0:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.ISOLATED_SENTENCE_TAIL,
                message="The quotation may be an isolated continuation of earlier text",
                chunk_id=unit.chunk_id,
                source_span=span,
                severity=ValidationIssueSeverity.LIKELY,
            )
        )

    issues.extend(_context_sufficiency_issues(unit))

    return tuple(issues)


def validate_evidence(context: ValidationContext) -> ValidationResult:
    """Validate provenance and obvious structure without deciding sufficiency."""
    retrieved_by_id = _validate_duplicate_retrieved_chunks(
        context.retrieved_chunks
    )

    selected = tuple(context.selection.selected_candidates)
    quotations = tuple(context.draft.quotations)

    if not selected or not quotations:
        if selected or quotations:
            raise ProvenanceValidationError(
                "Selection and draft quotation lists are inconsistent"
            )
        return ValidationResult(
            question=context.question,
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            validated_evidence=(),
            issues=(
                ValidationIssue(
                    code=ValidationIssueCode.EMPTY_EVIDENCE,
                    message="No candidate evidence was selected",
                ),
            ),
        )

    if len(selected) != len(quotations):
        raise ProvenanceValidationError(
            "Selection and draft quotation counts differ"
        )

    issues: list[ValidationIssue] = []
    validated: list[ValidatedEvidence] = []

    for scored, quoted in zip(selected, quotations):
        unit = scored.source_unit
        citation = quoted.citation

        retrieved = retrieved_by_id.get(unit.chunk_id)
        if retrieved is None:
            raise ProvenanceValidationError(
                f"Selected chunk ID {unit.chunk_id!r} is missing from retrieved chunks"
            )
        if citation.chunk_id != unit.chunk_id:
            raise ProvenanceValidationError(
                "Draft quotation chunk ID does not match the selected source unit"
            )
        if (
            citation.document_name != unit.document_name
            or citation.document_name != retrieved.document_name
            or citation.section != unit.section
            or citation.section != retrieved.section
            or citation.pdf_page_number != unit.page_number
            or citation.pdf_page_number != retrieved.page_number
            or citation.source_span != unit.span
        ):
            raise ProvenanceValidationError(
                f"Draft citation metadata conflicts for chunk {unit.chunk_id!r}"
            )
        if quoted.exact_quotation != unit.text:
            raise ProvenanceValidationError(
                f"Draft quotation differs from selected source unit "
                f"{unit.chunk_id!r}"
            )

        _validate_source_unit(unit, retrieved_by_id)

        unit_issues = _structural_issues(unit)
        issues.extend(unit_issues)
        context_dependent, _ = _context_dependent(unit)

        # M6.3F fix: only fatal structural issues should collapse is_complete.
        # LIKELY or informational warnings (e.g. LIKELY_CONTEXT_DEPENDENCY,
        # MISSING_PARENT_CONTEXT with UNRESOLVED severity, CONTEXT_AVAILABLE_NEARBY)
        # describe context risks but do not establish that the unit itself is
        # structurally truncated.  Collapsing is_complete for them caused every
        # complete numbered rule to be treated as incomplete.
        has_fatal_issue = not unit.is_complete or any(
            issue.code in _FATAL_ISSUE_CODES
            or issue.severity is ValidationIssueSeverity.DEFINITE
            for issue in unit_issues
        )
        validated.append(
            ValidatedEvidence(
                quotation=quoted,
                is_complete=not has_fatal_issue,
                is_context_dependent=context_dependent,
            )
        )

    deduplicated_issues: list[ValidationIssue] = []
    seen_issue_keys: set[tuple[object, ...]] = set()
    for issue in issues:
        key = (
            issue.code,
            issue.chunk_id,
            issue.severity,
            issue.source_span.start if issue.source_span is not None else None,
            issue.source_span.end if issue.source_span is not None else None,
        )
        if key in seen_issue_keys:
            continue
        seen_issue_keys.add(key)
        deduplicated_issues.append(issue)
    issues = deduplicated_issues

    if not any(
        issue.code is ValidationIssueCode.INCOMPLETE_SOURCE_UNIT
        or issue.code is ValidationIssueCode.HEADING_USED_AS_EVIDENCE
        or issue.code is ValidationIssueCode.TABLE_FRAGMENT_USED_AS_EVIDENCE
        or issue.code is ValidationIssueCode.CONTINUATION_USED_AS_EVIDENCE
        or issue.code is ValidationIssueCode.ISOLATED_SENTENCE_TAIL
        or issue.code is ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION
        or issue.code is ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY
        or issue.code is ValidationIssueCode.CONTEXT_MISSING_OUTSIDE_CHUNK
        or issue.code is ValidationIssueCode.MISSING_PARENT_CONTEXT
        or issue.code is ValidationIssueCode.DEFINITE_INCOMPLETE_CONTEXT
        for issue in issues
    ):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.NO_CONTEXT_ISSUE,
                message="No obvious structural context dependency was detected",
                severity=ValidationIssueSeverity.NONE,
            )
        )
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.SUFFICIENCY_NOT_EVALUATED,
                message="Provenance and structure are valid; answer sufficiency was not evaluated",
                severity=ValidationIssueSeverity.NONE,
            )
        )

    has_structural_issue = any(
        issue.code not in (
            ValidationIssueCode.SUFFICIENCY_NOT_EVALUATED,
            ValidationIssueCode.NO_CONTEXT_ISSUE,
        )
        for issue in issues
    )
    status = (
        AnswerStatus.INSUFFICIENT_EVIDENCE
        if has_structural_issue
        else AnswerStatus.INSUFFICIENT_EVIDENCE
    )

    return ValidationResult(
        question=context.question,
        status=status,
        validated_evidence=tuple(validated),
        issues=tuple(issues),
    )
