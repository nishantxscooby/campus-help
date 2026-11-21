"""Local policy search and a deliberately narrow, application-owned answer gate."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from ..answer.assembly import assemble_evidence
from ..answer.evidence import score_source_units, select_evidence
from ..answer.models import ValidationContext, ValidationIssueSeverity
from ..answer.source_units import extract_source_units
from ..answer.verification import verify_question_evidence
from ..answer.verification_contracts import (
    ApprovedCorpus, DocumentVersion, FactRegistry, PolicyRelation, ProvenanceOutcome,
    SourceWitness, VerificationOutcome,
)
from ..hybrid.engine import HybridSearchResult
from ..retrieval.engine import BM25Retriever
from ..retrieval.loader import load_chunks


PDF_NAME = "STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf"


def bundled_corpus(data_dir: Path) -> ApprovedCorpus:
    return ApprovedCorpus(
        DocumentVersion(PDF_NAME, "1325facb0517e640ebf634e8d30ffe3d2fcd1122a676e7cfba49db9a8fa3bb2d"),
        data_dir / "input" / PDF_NAME, data_dir / "output" / "discipline-rules.json",
        "5108a91f99e3d49c0f4d5b7d5a8ad5761f58b5fb9ee92357013c01d892c6b5e1", "unreviewed",
    )


class SourceUnavailable(Exception):
    pass


def pinned_bytes(path: Path, expected: str) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SourceUnavailable from exc
    if sha256(data).hexdigest() != expected:
        raise SourceUnavailable
    return data


@dataclass(frozen=True)
class Decision:
    reason: str
    witness: SourceWitness | None = None


class PolicyDesk:
    def __init__(self, corpus: ApprovedCorpus, registry: FactRegistry | None = None, *, semantic_index: str | None = None):
        self.corpus = corpus
        self.registry = registry
        pinned_bytes(corpus.corpus_path, corpus.corpus_revision)
        self.index = BM25Retriever(load_chunks(corpus.corpus_path))

        self.hybrid = None
        if semantic_index:
            from ..hybrid.engine import HybridRetriever
            from ..semantic.engine import SemanticRetriever
            from ..semantic.model import MODEL_NAME, load_model

            model = load_model(MODEL_NAME, local_files_only=True)
            self.hybrid = HybridRetriever(self.index, SemanticRetriever.from_index(model, semantic_index))

    def ask(self, question: str) -> Decision:
        if self.hybrid:
            parents = tuple(self.hybrid.search(question))
        else:
            parents = tuple(
                HybridSearchResult.from_candidate(result, rank, None, 0.0)
                for rank, result in enumerate(self.index.search(question, top_k=5), 1)
            )
        selected = select_evidence(question, score_source_units(question, extract_source_units(parents)))
        context = ValidationContext(question, parents, selected, assemble_evidence(question, selected))
        report = verify_question_evidence(context, approved_corpus=self.corpus, fact_registry=self.registry)
        if report.provenance in (ProvenanceOutcome.MISSING_SOURCE, ProvenanceOutcome.STALE_SOURCE):
            raise SourceUnavailable
        if report.provenance is ProvenanceOutcome.MISMATCH:
            return Decision("source_context")
        if report.request.requested_relation is None:
            return Decision("unsupported_or_ambiguous")
        if not report.witnesses:
            return Decision("no_evidence")
        if any(issue.severity is not ValidationIssueSeverity.NONE for issue in report.context_findings):
            return Decision("source_context")
        registry = self.registry
        if registry is None or report.outcome is VerificationOutcome.MISSING_APPROVED_FACT:
            return Decision("awaiting_review")
        scope = registry.scope
        if (not scope.complete or scope.known_exceptions or report.conflict_findings
                or scope.definitions or scope.governing_provisions):
            return Decision("incomplete_proof")
        matching = [fact for fact in registry.facts if question ==
                    f"Who is authorized to {fact.action} {fact.object} under {fact.scope}?"]
        if len(matching) != 1:
            return Decision("incomplete_proof")
        fact, = matching
        if (report.provenance is not ProvenanceOutcome.CANONICAL_MATCH
                or report.outcome is not VerificationOutcome.NOT_ESTABLISHED
                or report.request.requested_relation is not PolicyRelation.AUTHORITY_FOR
                or fact.relation is not PolicyRelation.AUTHORITY_FOR or len(report.referenced_facts) != 1
                or not all((fact.actor, fact.action, fact.object, fact.scope))
                or fact.modality != "may" or fact.polarity != "affirmative"
                or fact.conditions != () or fact.exceptions != ()
                or any(value is not None for value in (fact.quantity, fact.unit, fact.triggering_event))
                or len(fact.witnesses) != 1):
            return Decision("incomplete_proof")
        witness, = fact.witnesses
        expected_question = f"Who is authorized to {fact.action} {fact.object} under {fact.scope}?"
        expected_statement = f"{fact.actor} may {fact.action} {fact.object} under {fact.scope}."
        if (question != expected_question or witness.exact_quotation != expected_statement
                or witness not in report.witnesses):
            return Decision("incomplete_proof")
        for candidate in selected.selected_candidates:
            unit = candidate.source_unit
            if (unit.chunk_id == witness.citation.chunk_id and unit.span == witness.citation.source_span
                    and unit.is_complete and unit.full_chunk_text.strip() == witness.exact_quotation):
                return Decision("reviewed_authority", witness)
        return Decision("incomplete_proof")
