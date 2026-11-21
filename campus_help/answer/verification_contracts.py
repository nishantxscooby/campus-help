"""Immutable contracts for source authentication. No outcome confers factual support."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re

from .models import EvidenceCitation, QuestionIntentType, ValidationIssue


def _text(*values: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Expected nonempty text")


def _digest(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        raise ValueError("Expected a lowercase SHA-256 digest")


def _tuple(value: tuple, item_type: type) -> None:
    if not isinstance(value, tuple) or not all(isinstance(item, item_type) for item in value):
        raise TypeError(f"Expected an immutable tuple of {item_type.__name__}")


class PolicyRelation(str, Enum):
    AUTHORITY_FOR = "authority_for"
    PERMISSIBILITY_OF = "permissibility_of"
    DEADLINE_FOR = "deadline_for"
    APPLIES_TO = "applies_to"


@dataclass(frozen=True)
class ClaimRequest:
    question: str
    intent: QuestionIntentType
    requested_relation: PolicyRelation | None
    explicit_constraints: tuple[str, ...]
    output_slots: tuple[str, ...]
    required_obligations: tuple[str, ...]
    unresolved_qualifiers: tuple[str, ...]
    revision: str = "m6.4a-1"

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not isinstance(self.intent, QuestionIntentType):
            raise TypeError("Expected original question text and recognized intent")
        if self.requested_relation is not None and not isinstance(self.requested_relation, PolicyRelation):
            raise TypeError("Expected a policy relation")
        _text(self.revision)
        for values in (self.explicit_constraints, self.output_slots,
                       self.required_obligations, self.unresolved_qualifiers):
            _tuple(values, str)


@dataclass(frozen=True)
class DocumentVersion:
    document_name: str
    pdf_sha256: str

    def __post_init__(self) -> None:
        _text(self.document_name)
        _digest(self.pdf_sha256)


@dataclass(frozen=True)
class ApprovedCorpus:
    """Application-owned pins for one PDF/JSON pair. The JSON digest is its revision."""

    document: DocumentVersion
    pdf_path: Path
    corpus_path: Path
    corpus_revision: str
    review_revision: str

    def __post_init__(self) -> None:
        _digest(self.corpus_revision)
        _text(self.review_revision)


@dataclass(frozen=True)
class SourceWitness:
    """Exact citation in a source/review snapshot. Inclusion alone conveys no approval."""

    document: DocumentVersion
    corpus_revision: str
    review_revision: str
    parent_sha256: str
    citation: EvidenceCitation
    exact_quotation: str

    def __post_init__(self) -> None:
        _digest(self.parent_sha256)
        _digest(self.corpus_revision)
        _text(self.review_revision, self.exact_quotation, self.citation.chunk_id)
        span = self.citation.source_span
        if self.document.document_name != self.citation.document_name:
            raise ValueError("Witness document differs from citation")
        if (type(self.citation.pdf_page_number) is not int or self.citation.pdf_page_number < 1
                or span.end - span.start != len(self.exact_quotation)):
            raise ValueError("Invalid witness page or parent-relative quotation span")


@dataclass(frozen=True)
class ReviewedPolicyFact:
    """Offline approval record. None denotes unknown; an empty tuple denotes known empty."""

    fact_id: str
    revision: str
    review_revision: str
    relation: PolicyRelation
    witnesses: tuple[SourceWitness, ...]
    actor: str | None = None
    action: str | None = None
    object: str | None = None
    modality: str | None = None
    polarity: str | None = None
    scope: str | None = None
    conditions: tuple[str, ...] | None = None
    exceptions: tuple[str, ...] | None = None
    quantity: str | None = None
    unit: str | None = None
    triggering_event: str | None = None

    def __post_init__(self) -> None:
        _text(self.fact_id, self.revision, self.review_revision)
        if not isinstance(self.relation, PolicyRelation) or not self.witnesses:
            raise ValueError("A reviewed fact requires a typed relation and witnesses")
        _tuple(self.witnesses, SourceWitness)
        for value in (self.actor, self.action, self.object, self.modality, self.polarity,
                      self.scope, self.quantity, self.unit, self.triggering_event):
            if value is not None:
                _text(value)
        for values in (self.conditions, self.exceptions):
            if values is not None:
                _tuple(values, str)


@dataclass(frozen=True)
class ReviewScope:
    documents: tuple[DocumentVersion, ...]
    policy_family: PolicyRelation
    corpus_revision: str
    review_revision: str
    definitions: tuple[str, ...]
    governing_provisions: tuple[str, ...]
    known_exceptions: tuple[str, ...]
    known_conflicts: tuple[str, ...]
    complete: bool

    def __post_init__(self) -> None:
        _tuple(self.documents, DocumentVersion)
        _text(self.review_revision)
        _digest(self.corpus_revision)
        if not self.documents or not isinstance(self.policy_family, PolicyRelation):
            raise ValueError("Review scope requires document versions and a policy family")
        if not isinstance(self.complete, bool):
            raise TypeError("Expected boolean review completeness")
        for values in (self.definitions, self.governing_provisions,
                       self.known_exceptions, self.known_conflicts):
            _tuple(values, str)


@dataclass(frozen=True)
class FactRegistry:
    scope: ReviewScope
    facts: tuple[ReviewedPolicyFact, ...]

    def __post_init__(self) -> None:
        _tuple(self.facts, ReviewedPolicyFact)
        if len({fact.fact_id for fact in self.facts}) != len(self.facts):
            raise ValueError("Duplicate active fact ID")
        if any(fact.relation != self.scope.policy_family for fact in self.facts):
            raise ValueError("Fact outside the reviewed policy family")


class ProvenanceOutcome(str, Enum):
    CANONICAL_MATCH = "canonical_match"
    NO_EVIDENCE = "no_evidence"
    MISSING_SOURCE = "missing_source"
    STALE_SOURCE = "stale_source"
    MISMATCH = "provenance_mismatch"


class VerificationOutcome(str, Enum):
    NOT_ESTABLISHED = "not_established"
    PROVENANCE_BLOCKED = "provenance_blocked"
    UNSUPPORTED_REQUEST = "unsupported_request"
    MISSING_APPROVED_FACT = "missing_approved_fact"


@dataclass(frozen=True)
class ObligationDiagnostic:
    obligation: str
    unresolved_reason: str

    def __post_init__(self) -> None:
        _text(self.obligation, self.unresolved_reason)


@dataclass(frozen=True)
class FactReference:
    fact_id: str
    revision: str


@dataclass(frozen=True)
class VerificationReport:
    request: ClaimRequest
    document: DocumentVersion | None
    corpus_revision: str | None
    review_revision: str | None
    provenance: ProvenanceOutcome
    outcome: VerificationOutcome
    detail: str
    obligations: tuple[ObligationDiagnostic, ...]
    context_findings: tuple[ValidationIssue, ...]
    conflict_findings: tuple[str, ...]
    witnesses: tuple[SourceWitness, ...]
    referenced_facts: tuple[FactReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, VerificationOutcome):
            raise ValueError("Unknown verification outcome")
        if not isinstance(self.provenance, ProvenanceOutcome):
            raise ValueError("Unknown provenance outcome")
        _tuple(self.obligations, ObligationDiagnostic)
        _tuple(self.context_findings, ValidationIssue)
        _tuple(self.conflict_findings, str)
        _tuple(self.witnesses, SourceWitness)
        _tuple(self.referenced_facts, FactReference)
        if tuple(item.obligation for item in self.obligations) != self.request.required_obligations:
            raise ValueError("Every requested proof obligation requires a diagnostic")

    @property
    def is_verified(self) -> bool:
        return False
