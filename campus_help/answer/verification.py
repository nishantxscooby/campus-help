"""Context-only M6.4A API. Supply pins and registry from trusted application configuration.

Pins identify approved file bytes, not institutional authority or completeness of a
policy review. There is no default registry. Never derive configuration from a request.
"""

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import re

import fitz

from ..hybrid.engine import HybridSearchResult
from .models import EvidenceCitation, QuestionIntentType, SourceUnit, ValidationContext
from .question_planning import create_question_plan
from .source_units import extract_source_units
from .validation import ProvenanceValidationError, validate_evidence
from .verification_contracts import (
    ApprovedCorpus, ClaimRequest, FactReference, FactRegistry, ObligationDiagnostic, PolicyRelation,
    ProvenanceOutcome, SourceWitness, VerificationOutcome, VerificationReport,
)


_REQUEST_TYPES = {
    QuestionIntentType.DISCIPLINARY_AUTHORITY: (PolicyRelation.AUTHORITY_FOR, ("actor",)),
    QuestionIntentType.PROCEDURAL_DEADLINE: (PolicyRelation.DEADLINE_FOR, ("duration", "unit", "trigger")),
    QuestionIntentType.PROHIBITION_PERMISSIBILITY: (PolicyRelation.PERMISSIBILITY_OF, ("modality",)),
    QuestionIntentType.POLICY_APPLICABILITY: (PolicyRelation.APPLIES_TO, ("applicability",)),
}


def _request(question: str) -> ClaimRequest:
    plan = create_question_plan(question)
    relation, slots = _REQUEST_TYPES.get(plan.intent_type, (None, ()))
    return ClaimRequest(
        question=question, intent=plan.intent_type, requested_relation=relation,
        explicit_constraints=tuple(re.findall(
            r"\b[0-9]+[ \t]+(?:(?:working|calendar)[ \t]+days?|days?|hours?|weeks?|months?)\b",
            question, re.IGNORECASE,
        )), output_slots=slots,
        required_obligations=("bind_full_question",) + tuple(
            requirement.expected_predicate for requirement in plan.requirements
        ),
        unresolved_qualifiers=(question,),
    )


class _SourceError(ValueError):
    def __init__(self, outcome: ProvenanceOutcome, message: str):
        super().__init__(message)
        self.outcome = outcome


def _pinned_bytes(path: Path, digest: str) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise _SourceError(ProvenanceOutcome.MISSING_SOURCE, "Canonical file unavailable") from exc
    if sha256(data).hexdigest() != digest:
        raise _SourceError(ProvenanceOutcome.STALE_SOURCE, "Canonical file digest mismatch")
    return data


def _canonical_chunks(config: ApprovedCorpus) -> dict[str, HybridSearchResult]:
    data = _pinned_bytes(config.corpus_path, config.corpus_revision)
    try:
        envelope = json.loads(data)
        if envelope["document_name"] != config.document.document_name:
            raise ValueError("Document identity mismatch")
        if not isinstance(envelope["chunks"], list):
            raise ValueError("Invalid chunk list")
        chunks = {}
        for row in envelope["chunks"]:
            chunk = HybridSearchResult(**row, bm25_rank=None, semantic_rank=None, rrf_score=0.0)
            if (chunk.chunk_id in chunks or chunk.document_name != envelope["document_name"]
                    or chunk.category != envelope["category"] or type(chunk.page_number) is not int
                    or chunk.page_number < 1 or not all(isinstance(value, str) and value.strip()
                        for value in (chunk.chunk_id, chunk.text, chunk.category, chunk.section))):
                raise ValueError("Invalid or duplicate canonical chunk")
            chunks[chunk.chunk_id] = chunk
        return chunks
    except (KeyError, TypeError, ValueError) as exc:
        raise _SourceError(ProvenanceOutcome.MISMATCH, "Invalid pinned corpus envelope") from exc


def _source_witness(unit: SourceUnit, config: ApprovedCorpus) -> SourceWitness:
    return SourceWitness(
        config.document, config.corpus_revision, config.review_revision,
        sha256(unit.full_chunk_text.encode("utf-8")).hexdigest(),
        EvidenceCitation(unit.document_name, unit.section, unit.page_number, unit.chunk_id, unit.span),
        unit.text,
    )


def _check_review_versions(config: ApprovedCorpus, registry: FactRegistry) -> None:
    scope = registry.scope
    if (scope.documents != (config.document,) or scope.corpus_revision != config.corpus_revision
            or scope.review_revision != config.review_revision):
        raise _SourceError(ProvenanceOutcome.STALE_SOURCE, "Review scope differs from active pins")
    for fact in registry.facts:
        if fact.review_revision != config.review_revision:
            raise _SourceError(ProvenanceOutcome.STALE_SOURCE, "Stale reviewed fact")
        for witness in fact.witnesses:
            if (witness.document != config.document or witness.corpus_revision != config.corpus_revision
                    or witness.review_revision != config.review_revision):
                raise _SourceError(ProvenanceOutcome.STALE_SOURCE, "Stale witness")


def _check_pages(pdf_bytes: bytes, parents: tuple[HybridSearchResult, ...]) -> None:
    """Locate each whole parent uniquely on its pinned PDF page, ignoring layout whitespace only."""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            pages = {}
            for parent in parents:
                page = parent.page_number
                if page not in pages:
                    pages[page] = " " + " ".join(document.load_page(page - 1).get_text().split()) + " "
                pattern = " " + " ".join(parent.text.split()) + " "
                first = pages[page].find(pattern)
                if first < 0 or pages[page].find(pattern, first + 1) >= 0:
                    raise ValueError("Ambiguous or missing PDF parent")
    except (RuntimeError, ValueError, IndexError) as exc:
        raise _SourceError(ProvenanceOutcome.MISMATCH, "Cannot locate canonical parent on PDF page") from exc


def _authenticate(
    context: ValidationContext, config: ApprovedCorpus, registry: FactRegistry | None,
) -> tuple[SourceWitness, ...]:
    pdf_bytes = _pinned_bytes(config.pdf_path, config.document.pdf_sha256)
    chunks = _canonical_chunks(config)
    for supplied in context.retrieved_chunks:
        identity = replace(supplied, bm25_rank=None, semantic_rank=None, rrf_score=0.0)
        if type(supplied.page_number) is not int or identity != chunks.get(supplied.chunk_id):
            raise _SourceError(ProvenanceOutcome.MISMATCH, "Retrieved parent differs from canonical chunk")

    reviewed = set()
    if registry is not None:
        _check_review_versions(config, registry)
        reviewed = {witness for fact in registry.facts for witness in fact.witnesses}

    selected = tuple(candidate.source_unit for candidate in context.selection.selected_candidates)
    parent_ids = {unit.chunk_id for unit in selected} | {item.citation.chunk_id for item in reviewed}
    if parent_ids.difference(chunks):
        raise _SourceError(ProvenanceOutcome.MISMATCH, "Unknown witness parent")
    parents = tuple(chunks[chunk_id] for chunk_id in sorted(parent_ids))
    _check_pages(pdf_bytes, parents)
    units = {(unit.chunk_id, unit.span): unit for unit in extract_source_units(parents)}
    for witness in reviewed:
        canonical = units.get((witness.citation.chunk_id, witness.citation.source_span))
        if canonical is None or _source_witness(canonical, config) != witness:
            raise _SourceError(ProvenanceOutcome.MISMATCH, "Approval differs from canonical witness")

    selected_witnesses = []
    for unit in selected:
        canonical = units.get((unit.chunk_id, unit.span))
        if (canonical is None or canonical != unit or type(unit.page_number) is not int
                or canonical.is_complete is not unit.is_complete
                or canonical.unit_type is not unit.unit_type
                or canonical.extraction_method is not unit.extraction_method):
            raise _SourceError(ProvenanceOutcome.MISMATCH, "Selected unit differs from canonical extraction")
        selected_witnesses.append(_source_witness(canonical, config))
    return tuple(selected_witnesses)


def verify_question_evidence(
    context: ValidationContext, *, approved_corpus: ApprovedCorpus | None,
    fact_registry: FactRegistry | None,
) -> VerificationReport:
    """Authenticate exact evidence only. Configuration belongs to the application, never the caller payload."""
    if not isinstance(context, ValidationContext):
        raise TypeError("Original ValidationContext required")
    if approved_corpus is not None and not isinstance(approved_corpus, ApprovedCorpus):
        raise TypeError("Expected application ApprovedCorpus configuration")
    if fact_registry is not None and not isinstance(fact_registry, FactRegistry):
        raise TypeError("Expected application FactRegistry configuration")
    request = _request(context.question)
    findings = ()
    witnesses = ()
    conflicts = ()
    references = ()
    try:
        validation = validate_evidence(context)
        if context.question != context.draft.question:
            raise ProvenanceValidationError("Draft question differs from original question")
        if any(type(item.citation.pdf_page_number) is not int for item in context.draft.quotations):
            raise ProvenanceValidationError("Invalid citation page")
        if approved_corpus is None:
            raise _SourceError(ProvenanceOutcome.MISSING_SOURCE, "No independently pinned source")
        witnesses = _authenticate(context, approved_corpus, fact_registry)
        findings = validation.issues
        provenance = ProvenanceOutcome.CANONICAL_MATCH if witnesses else ProvenanceOutcome.NO_EVIDENCE
        if fact_registry is not None:
            conflicts = fact_registry.scope.known_conflicts
            references = tuple(
                FactReference(fact.fact_id, fact.revision) for fact in fact_registry.facts
                if fact.relation == request.requested_relation and set(fact.witnesses).issubset(witnesses)
            )
        if request.requested_relation is None:
            outcome = VerificationOutcome.UNSUPPORTED_REQUEST
            detail = "No recognized relation"
        elif not references:
            outcome = VerificationOutcome.MISSING_APPROVED_FACT
            detail = "No configured fact for this family with all exact witnesses selected"
        else:
            outcome = VerificationOutcome.NOT_ESTABLISHED
            detail = "Source identity checked; question binding and factual obligations unresolved"
    except (ProvenanceValidationError, _SourceError) as exc:
        provenance = exc.outcome if isinstance(exc, _SourceError) else ProvenanceOutcome.MISMATCH
        outcome = VerificationOutcome.PROVENANCE_BLOCKED
        detail = str(exc)

    return VerificationReport(
        request=request, document=approved_corpus.document if approved_corpus else None,
        corpus_revision=approved_corpus.corpus_revision if approved_corpus else None,
        review_revision=approved_corpus.review_revision if approved_corpus else None,
        provenance=provenance, outcome=outcome, detail=detail,
        obligations=tuple(ObligationDiagnostic(name, detail) for name in request.required_obligations),
        context_findings=findings, conflict_findings=conflicts, witnesses=witnesses,
        referenced_facts=references,
    )
