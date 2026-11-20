"""Immutable data models for exact, traceable source units."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..hybrid.engine import HybridSearchResult


class UnitType(str, Enum):
    """The structure identified by the extraction logic."""

    SENTENCE = "sentence"
    NUMBERED_ITEM = "numbered_item"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    CONTINUATION = "continuation"
    TABLE_ROW = "table_row"


class ExtractionMethod(str, Enum):
    """The deterministic rule used to create a source unit."""

    SENTENCE_SPLIT = "sentence_split"
    NUMBERED_ITEM_SPLIT = "numbered_item_split"
    PARAGRAPH_SPLIT = "paragraph_split"
    HEADING_DETECTION = "heading_detection"
    CONTINUATION_DETECTION = "continuation_detection"
    TABLE_ROW_DETECTION = "table_row_detection"


@dataclass(frozen=True)
class SourceSpan:
    """Half-open character offsets `[start, end)` in a source chunk."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if isinstance(self.start, bool) or isinstance(self.end, bool):
            raise TypeError("SourceSpan offsets must be integers")
        if not isinstance(self.start, int) or not isinstance(self.end, int):
            raise TypeError("SourceSpan offsets must be integers")
        if self.start < 0 or self.end < self.start:
            raise ValueError("SourceSpan offsets must satisfy 0 <= start <= end")


@dataclass(frozen=True)
class SourceUnit:
    """An exact quotation and its provenance within one original chunk."""

    chunk_id: str
    document_name: str
    category: str
    section: str
    page_number: int
    full_chunk_text: str
    text: str
    span: SourceSpan
    unit_type: UnitType
    is_complete: bool
    extraction_method: ExtractionMethod

    def __post_init__(self) -> None:
        if self.span.end > len(self.full_chunk_text):
            raise ValueError("SourceSpan end is outside full_chunk_text")
        if self.full_chunk_text[self.span.start:self.span.end] != self.text:
            raise ValueError("SourceUnit text must exactly match its source span")


@dataclass(frozen=True)
class ScoredSourceUnit:
    """A source unit with deterministic, explainable relevance diagnostics."""

    source_unit: SourceUnit
    relevance_score: float
    query_term_coverage: float
    matched_terms: tuple[str, ...]
    matched_numbers: tuple[str, ...]
    mismatched_numbers: tuple[str, ...]


@dataclass(frozen=True)
class SelectionDiagnostics:
    """Deterministic evidence-selection counts and limits."""

    candidate_count: int
    selected_count: int
    excluded_count: int
    deduplicated_count: int
    max_evidence: int


@dataclass(frozen=True)
class EvidenceSelection:
    """Candidate evidence selected without making a final answerability claim."""

    selected_candidates: tuple[ScoredSourceUnit, ...]
    excluded_candidates: tuple[ScoredSourceUnit, ...]
    diagnostics: SelectionDiagnostics


class AnswerStatus(str, Enum):
    """Validation outcomes available to the answer pipeline."""

    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    AMBIGUOUS = "ambiguous"
    CONFLICTING_EVIDENCE = "conflicting_evidence"


class ValidationIssueCode(str, Enum):
    """Machine-readable structural and context issue codes."""

    EMPTY_EVIDENCE = "EMPTY_EVIDENCE"
    INCOMPLETE_SOURCE_UNIT = "INCOMPLETE_SOURCE_UNIT"
    HEADING_USED_AS_EVIDENCE = "HEADING_USED_AS_EVIDENCE"
    TABLE_FRAGMENT_USED_AS_EVIDENCE = "TABLE_FRAGMENT_USED_AS_EVIDENCE"
    CONTINUATION_USED_AS_EVIDENCE = "CONTINUATION_USED_AS_EVIDENCE"
    ISOLATED_SENTENCE_TAIL = "ISOLATED_SENTENCE_TAIL"
    CONTEXT_DEPENDENT_QUOTATION = "CONTEXT_DEPENDENT_QUOTATION"
    MISSING_PARENT_CONTEXT = "MISSING_PARENT_CONTEXT"
    SUFFICIENCY_NOT_EVALUATED = "SUFFICIENCY_NOT_EVALUATED"
    DEFINITE_INCOMPLETE_CONTEXT = "DEFINITE_INCOMPLETE_CONTEXT"
    LIKELY_CONTEXT_DEPENDENCY = "LIKELY_CONTEXT_DEPENDENCY"
    CONTEXT_MISSING_OUTSIDE_CHUNK = "CONTEXT_MISSING_OUTSIDE_CHUNK"
    CONTEXT_AVAILABLE_NEARBY = "CONTEXT_AVAILABLE_NEARBY"
    NO_CONTEXT_ISSUE = "NO_CONTEXT_ISSUE"


class ValidationIssueSeverity(str, Enum):
    """Conservative severity for context-sufficiency diagnostics."""

    DEFINITE = "definite"
    LIKELY = "likely"
    UNRESOLVED = "unresolved"
    NONE = "none"


@dataclass(frozen=True)
class ValidationContext:
    """Exact retrieved chunks and M5 evidence used for M6.1 validation."""

    question: str
    retrieved_chunks: tuple["HybridSearchResult", ...]
    selection: "EvidenceSelection"
    draft: "ExtractiveDraft"


@dataclass(frozen=True)
class EvidenceCitation:
    """Machine-readable provenance for one exact source quotation."""

    document_name: str
    section: str
    pdf_page_number: int
    chunk_id: str
    source_span: SourceSpan


@dataclass(frozen=True)
class QuotedEvidence:
    """An exact quotation paired with its citation."""

    exact_quotation: str
    citation: EvidenceCitation

    def to_dict(self) -> dict[str, object]:
        return {
            "exact_quotation": self.exact_quotation,
            "citation": {
                "document_name": self.citation.document_name,
                "section": self.citation.section,
                "pdf_page_number": self.citation.pdf_page_number,
                "chunk_id": self.citation.chunk_id,
                "source_span": {
                    "start": self.citation.source_span.start,
                    "end": self.citation.source_span.end,
                },
            },
        }


@dataclass(frozen=True)
class ExtractiveDraft:
    """A collection of source quotations, without a final answerability status."""

    question: str
    quotations: tuple[QuotedEvidence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "quotations": [
                quotation.to_dict()
                for quotation in self.quotations
            ],
        }


@dataclass(frozen=True)
class ValidationIssue:
    """A deterministic structural or context issue found during validation."""

    code: ValidationIssueCode
    message: str
    chunk_id: str | None = None
    source_span: SourceSpan | None = None
    severity: ValidationIssueSeverity = ValidationIssueSeverity.UNRESOLVED


@dataclass(frozen=True)
class ValidatedEvidence:
    """Structural validation metadata for one exact quoted source unit."""

    quotation: "QuotedEvidence"
    is_complete: bool
    is_context_dependent: bool


@dataclass(frozen=True)
class ValidationResult:
    """M6.1 validation output. Answer status does not claim sufficiency."""

    question: str
    status: AnswerStatus
    validated_evidence: tuple[ValidatedEvidence, ...]
    issues: tuple[ValidationIssue, ...]


class QuestionIntentType(str, Enum):
    """Broad question intent categories for policy questions."""

    PROHIBITION_PERMISSIBILITY = "prohibition_permissibility"
    DISCIPLINARY_AUTHORITY = "disciplinary_authority"
    POLICY_APPLICABILITY = "policy_applicability"
    PROCEDURAL_DEADLINE = "procedural_deadline"
    UNSUPPORTED_OR_UNKNOWN = "unsupported_or_unknown"


@dataclass(frozen=True, init=False)
class EvidenceRequirement:
    """A single factual condition required to answer a question."""

    requirement_id: str
    description: str
    intent_type: QuestionIntentType
    factual_anchors: tuple[str, ...]
    expected_predicate: str
    is_verified: bool
    category: str

    def __init__(
        self,
        requirement_id: str | None = None,
        description: str = "",
        intent_type: QuestionIntentType | str = QuestionIntentType.UNSUPPORTED_OR_UNKNOWN,
        factual_anchors: tuple[str, ...] | Sequence[str] = (),
        expected_predicate: str = "",
        is_verified: bool = False,
        category: str = "",
        *,
        id: str | None = None,
    ) -> None:
        actual_id = requirement_id if requirement_id is not None else id
        if actual_id is None:
            raise TypeError("requirement_id (or id) is required")
        if isinstance(actual_id, bool) or not isinstance(actual_id, str):
            raise TypeError("requirement_id must be a string")
        if not actual_id.strip():
            raise ValueError("requirement_id must be a non-empty string")

        if isinstance(description, bool) or not isinstance(description, str):
            raise TypeError("description must be a string")
        if not description.strip():
            raise ValueError("description must be a non-empty string")

        if isinstance(intent_type, str) and not isinstance(intent_type, QuestionIntentType):
            try:
                resolved_intent = QuestionIntentType(intent_type)
            except ValueError:
                try:
                    resolved_intent = QuestionIntentType[intent_type]
                except KeyError:
                    raise TypeError(f"intent_type {intent_type!r} is not a valid QuestionIntentType")
        elif isinstance(intent_type, QuestionIntentType):
            resolved_intent = intent_type
        else:
            raise TypeError(f"intent_type must be a QuestionIntentType, got {type(intent_type)}")

        if isinstance(is_verified, int) and not isinstance(is_verified, bool):
            raise TypeError("is_verified must be a boolean")
        if not isinstance(is_verified, bool):
            raise TypeError("is_verified must be a boolean")

        if isinstance(expected_predicate, bool) or not isinstance(expected_predicate, str):
            raise TypeError("expected_predicate must be a string")

        if isinstance(factual_anchors, (list, tuple)):
            for anchor in factual_anchors:
                if isinstance(anchor, bool) or not isinstance(anchor, str):
                    raise TypeError("Each factual anchor must be a string")
            resolved_anchors = tuple(factual_anchors)
        else:
            raise TypeError("factual_anchors must be a tuple or list of strings")

        resolved_category = category if category else resolved_intent.value
        if not isinstance(resolved_category, str):
            raise TypeError("category must be a string")

        object.__setattr__(self, "requirement_id", actual_id)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "intent_type", resolved_intent)
        object.__setattr__(self, "factual_anchors", resolved_anchors)
        object.__setattr__(self, "expected_predicate", expected_predicate)
        object.__setattr__(self, "is_verified", is_verified)
        object.__setattr__(self, "category", resolved_category)

    @property
    def id(self) -> str:
        return self.requirement_id

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "description": self.description,
            "intent_type": self.intent_type.value,
            "category": self.category,
            "factual_anchors": list(self.factual_anchors),
            "expected_predicate": self.expected_predicate,
            "is_verified": self.is_verified,
        }


@dataclass(frozen=True)
class QuestionValidationPlan:
    """Deterministic validation plan specifying evidence requirements for a question."""

    question: str
    intent_type: QuestionIntentType
    requirements: tuple[EvidenceRequirement, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.question, bool) or not isinstance(self.question, str):
            raise TypeError("question must be a string")

        if isinstance(self.intent_type, str) and not isinstance(self.intent_type, QuestionIntentType):
            try:
                object.__setattr__(self, "intent_type", QuestionIntentType(self.intent_type))
            except ValueError:
                try:
                    object.__setattr__(self, "intent_type", QuestionIntentType[self.intent_type])
                except KeyError:
                    raise TypeError(f"intent_type {self.intent_type!r} is not a valid QuestionIntentType")
        elif not isinstance(self.intent_type, QuestionIntentType):
            raise TypeError(f"intent_type must be a QuestionIntentType, got {type(self.intent_type)}")

        if not isinstance(self.requirements, (list, tuple)):
            raise TypeError("requirements must be a tuple or list of EvidenceRequirement instances")

        seen_ids: set[str] = set()
        converted_requirements: list[EvidenceRequirement] = []
        for req in self.requirements:
            if not isinstance(req, EvidenceRequirement):
                raise TypeError("All requirements must be EvidenceRequirement instances")
            if req.requirement_id in seen_ids:
                raise ValueError(f"Duplicate requirement ID: {req.requirement_id!r}")
            seen_ids.add(req.requirement_id)
            converted_requirements.append(req)

        object.__setattr__(self, "requirements", tuple(converted_requirements))

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "intent_type": self.intent_type.value,
            "requirements": [r.to_dict() for r in self.requirements],
        }


@dataclass(frozen=True)
class SufficiencyEvaluation:
    """Fail-closed evaluation of evidence sufficiency for answering a question."""

    question: str
    status: AnswerStatus
    is_sufficient: bool
    plan: QuestionValidationPlan | None
    unverified_requirements: tuple[EvidenceRequirement, ...]
    verified_requirements: tuple[EvidenceRequirement, ...]
    blockers: tuple[ValidationIssue, ...]
    issues: tuple[ValidationIssue, ...]
    validated_evidence: tuple[ValidatedEvidence, ...]
    reason: str

    def __post_init__(self) -> None:
        if isinstance(self.unverified_requirements, (list, tuple)):
            object.__setattr__(
                self, "unverified_requirements", tuple(self.unverified_requirements)
            )
        else:
            raise TypeError("unverified_requirements must be a sequence")

        if isinstance(self.verified_requirements, (list, tuple)):
            object.__setattr__(
                self, "verified_requirements", tuple(self.verified_requirements)
            )
        else:
            raise TypeError("verified_requirements must be a sequence")

        if isinstance(self.blockers, (list, tuple)):
            object.__setattr__(self, "blockers", tuple(self.blockers))
        else:
            raise TypeError("blockers must be a sequence")

        if isinstance(self.issues, (list, tuple)):
            object.__setattr__(self, "issues", tuple(self.issues))
        else:
            raise TypeError("issues must be a sequence")

        if isinstance(self.validated_evidence, (list, tuple)):
            object.__setattr__(
                self, "validated_evidence", tuple(self.validated_evidence)
            )
        else:
            raise TypeError("validated_evidence must be a sequence")

    @property
    def pending_requirements(self) -> tuple[EvidenceRequirement, ...]:
        return self.unverified_requirements

    @property
    def structural_blockers(self) -> tuple[ValidationIssue, ...]:
        return self.blockers

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "status": self.status.value,
            "is_sufficient": self.is_sufficient,
            "plan": self.plan.to_dict() if self.plan is not None else None,
            "unverified_requirements": [
                r.to_dict() for r in self.unverified_requirements
            ],
            "verified_requirements": [
                r.to_dict() for r in self.verified_requirements
            ],
            "blockers": [
                {
                    "code": b.code.value if hasattr(b.code, "value") else str(b.code),
                    "message": b.message,
                    "severity": b.severity.value if hasattr(b.severity, "value") else str(b.severity),
                    "chunk_id": b.chunk_id,
                }
                for b in self.blockers
            ],
            "issues": [
                {
                    "code": i.code.value if hasattr(i.code, "value") else str(i.code),
                    "message": i.message,
                    "severity": i.severity.value if hasattr(i.severity, "value") else str(i.severity),
                    "chunk_id": i.chunk_id,
                }
                for i in self.issues
            ],
            "validated_evidence": [
                ve.quotation.to_dict() for ve in self.validated_evidence
            ],
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CandidateEvidenceMatch:
    """Deterministic lexical match diagnostics between a requirement and a quoted source."""

    requirement_id: str
    quotation: str
    citation: EvidenceCitation
    exact_anchor_matches: tuple[str, ...]
    normalized_anchor_matches: tuple[str, ...]
    missing_anchors: tuple[str, ...]
    predicate_indicators: tuple[str, ...]
    matched_numbers: tuple[str, ...] = ()
    matched_units: tuple[str, ...] = ()
    negation_indicators: tuple[str, ...] = ()
    conditional_indicators: tuple[str, ...] = ()
    modal_verbs: tuple[str, ...] = ()
    context_issues: tuple[ValidationIssue, ...] = ()
    has_potential_support: bool = False
    is_verified: bool = False
    uncertainty_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.is_verified:
            raise ValueError("CandidateEvidenceMatch cannot be marked is_verified=True in M6.3C")
        for field in (
            "exact_anchor_matches",
            "normalized_anchor_matches",
            "missing_anchors",
            "predicate_indicators",
            "matched_numbers",
            "matched_units",
            "negation_indicators",
            "conditional_indicators",
            "modal_verbs",
            "context_issues",
            "uncertainty_reasons",
        ):
            val = getattr(self, field)
            if isinstance(val, (list, tuple)):
                object.__setattr__(self, field, tuple(val))
            else:
                raise TypeError(f"{field} must be a sequence")

    @property
    def matched_anchors(self) -> tuple[str, ...]:
        """Union of exact and normalized matched anchors preserving order."""
        seen = set()
        result = []
        for a in self.exact_anchor_matches + self.normalized_anchor_matches:
            if a not in seen:
                seen.add(a)
                result.append(a)
        return tuple(result)

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "quotation": self.quotation,
            "citation": {
                "document_name": self.citation.document_name,
                "section": self.citation.section,
                "pdf_page_number": self.citation.pdf_page_number,
                "chunk_id": self.citation.chunk_id,
                "source_span": {
                    "start": self.citation.source_span.start,
                    "end": self.citation.source_span.end,
                },
            },
            "exact_anchor_matches": list(self.exact_anchor_matches),
            "normalized_anchor_matches": list(self.normalized_anchor_matches),
            "matched_anchors": list(self.matched_anchors),
            "missing_anchors": list(self.missing_anchors),
            "predicate_indicators": list(self.predicate_indicators),
            "matched_numbers": list(self.matched_numbers),
            "matched_units": list(self.matched_units),
            "negation_indicators": list(self.negation_indicators),
            "conditional_indicators": list(self.conditional_indicators),
            "modal_verbs": list(self.modal_verbs),
            "context_issues": [
                {
                    "code": issue.code.value if hasattr(issue.code, "value") else str(issue.code),
                    "message": issue.message,
                    "severity": issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                    "chunk_id": issue.chunk_id,
                }
                for issue in self.context_issues
            ],
            "has_potential_support": self.has_potential_support,
            "is_verified": self.is_verified,
            "uncertainty_reasons": list(self.uncertainty_reasons),
        }


@dataclass(frozen=True)
class RequirementMatchDiagnostics:
    """Diagnostic matching results for a single evidence requirement."""

    requirement: EvidenceRequirement
    candidate_matches: tuple[CandidateEvidenceMatch, ...]
    has_potential_support: bool = False
    is_verified: bool = False
    missing_anchors: tuple[str, ...] = ()
    diagnostics_summary: str = ""

    def __post_init__(self) -> None:
        if self.is_verified:
            raise ValueError("RequirementMatchDiagnostics cannot be marked is_verified=True in M6.3C")
        if isinstance(self.candidate_matches, (list, tuple)):
            object.__setattr__(self, "candidate_matches", tuple(self.candidate_matches))
        else:
            raise TypeError("candidate_matches must be a sequence")
        if isinstance(self.missing_anchors, (list, tuple)):
            object.__setattr__(self, "missing_anchors", tuple(self.missing_anchors))
        else:
            raise TypeError("missing_anchors must be a sequence")

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement": self.requirement.to_dict(),
            "candidate_matches": [m.to_dict() for m in self.candidate_matches],
            "has_potential_support": self.has_potential_support,
            "is_verified": self.is_verified,
            "missing_anchors": list(self.missing_anchors),
            "diagnostics_summary": self.diagnostics_summary,
        }


@dataclass(frozen=True)
class EvidenceMatchReport:
    """Comprehensive, inspectable report of evidence matching against a question plan."""

    plan: QuestionValidationPlan
    requirement_diagnostics: tuple[RequirementMatchDiagnostics, ...]
    evidence_matches: tuple[CandidateEvidenceMatch, ...]
    unresolved_context_risks: tuple[ValidationIssue, ...]
    total_requirements: int
    potential_support_count: int
    unsupported_count: int
    status: AnswerStatus = AnswerStatus.INSUFFICIENT_EVIDENCE
    is_verified: bool = False
    summary: str = ""

    def __post_init__(self) -> None:
        if self.is_verified:
            raise ValueError("EvidenceMatchReport cannot be marked is_verified=True in M6.3C")
        if self.status is AnswerStatus.ANSWERED:
            raise ValueError("EvidenceMatchReport cannot have status AnswerStatus.ANSWERED in M6.3C")
        if isinstance(self.requirement_diagnostics, (list, tuple)):
            object.__setattr__(
                self, "requirement_diagnostics", tuple(self.requirement_diagnostics)
            )
        else:
            raise TypeError("requirement_diagnostics must be a sequence")
        if isinstance(self.evidence_matches, (list, tuple)):
            object.__setattr__(self, "evidence_matches", tuple(self.evidence_matches))
        else:
            raise TypeError("evidence_matches must be a sequence")
        if isinstance(self.unresolved_context_risks, (list, tuple)):
            object.__setattr__(
                self, "unresolved_context_risks", tuple(self.unresolved_context_risks)
            )
        else:
            raise TypeError("unresolved_context_risks must be a sequence")

    def to_dict(self) -> dict[str, object]:
        return {
            "plan": self.plan.to_dict(),
            "requirement_diagnostics": [
                rd.to_dict() for rd in self.requirement_diagnostics
            ],
            "evidence_matches": [m.to_dict() for m in self.evidence_matches],
            "unresolved_context_risks": [
                {
                    "code": issue.code.value if hasattr(issue.code, "value") else str(issue.code),
                    "message": issue.message,
                    "severity": issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                    "chunk_id": issue.chunk_id,
                }
                for issue in self.unresolved_context_risks
            ],
            "total_requirements": self.total_requirements,
            "potential_support_count": self.potential_support_count,
            "unsupported_count": self.unsupported_count,
            "status": self.status.value,
            "is_verified": self.is_verified,
            "summary": self.summary,
        }


class AssessmentReadiness(str, Enum):
    """Conservative diagnostic readiness category for question evidence."""

    UNSUPPORTED_INTENT = "unsupported_intent"
    NO_EVIDENCE = "no_evidence"
    CONTEXT_BLOCKED = "context_blocked"
    PARTIAL_CANDIDATE_COVERAGE = "partial_candidate_coverage"
    FULL_CANDIDATE_COVERAGE_UNVERIFIED = "full_candidate_coverage_unverified"


@dataclass(frozen=True)
class QuestionEvidenceAssessment:
    """Comprehensive, read-only diagnostic assessment of question evidence sufficiency."""

    question: str
    status: AnswerStatus
    is_sufficient: bool
    is_verified: bool
    readiness: AssessmentReadiness
    plan: QuestionValidationPlan
    validation_result: ValidationResult
    match_report: EvidenceMatchReport
    sufficiency_evaluation: SufficiencyEvaluation
    diagnostics_summary: str
    trust_boundary_note: str

    def __post_init__(self) -> None:
        if self.is_verified:
            raise ValueError("QuestionEvidenceAssessment cannot be marked is_verified=True in M6.3D")
        if self.status is AnswerStatus.ANSWERED:
            raise ValueError("QuestionEvidenceAssessment cannot have status AnswerStatus.ANSWERED in M6.3D")
        if self.is_sufficient:
            raise ValueError("QuestionEvidenceAssessment cannot have is_sufficient=True in M6.3D")

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "status": self.status.value,
            "is_sufficient": self.is_sufficient,
            "is_verified": self.is_verified,
            "readiness": self.readiness.value,
            "plan": self.plan.to_dict(),
            "validation_result": {
                "question": self.validation_result.question,
                "status": self.validation_result.status.value,
                "validated_evidence": [
                    ve.quotation.to_dict()
                    for ve in self.validation_result.validated_evidence
                ],
                "issues": [
                    {
                        "code": i.code.value if hasattr(i.code, "value") else str(i.code),
                        "message": i.message,
                        "severity": i.severity.value if hasattr(i.severity, "value") else str(i.severity),
                        "chunk_id": i.chunk_id,
                    }
                    for i in self.validation_result.issues
                ],
            },
            "match_report": self.match_report.to_dict(),
            "sufficiency_evaluation": self.sufficiency_evaluation.to_dict(),
            "diagnostics_summary": self.diagnostics_summary,
            "trust_boundary_note": self.trust_boundary_note,
        }
