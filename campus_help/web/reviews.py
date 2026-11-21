"""Load an operator-pinned review release. Never accept review data over HTTP."""

from dataclasses import replace
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ..answer.models import EvidenceCitation, SourceSpan
from ..answer.verification_contracts import (
    ApprovedCorpus, FactRegistry, PolicyRelation, ReviewedPolicyFact, ReviewScope, SourceWitness,
)

Text = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Entry(Record):
    fact_id: Text
    status: Literal["APPROVED", "PENDING_REVIEW", "REJECTED"]
    reviewer: Text | None
    decision_date: date | None
    actor: Text
    action: Text
    object: Text
    scope: Text
    quotation: Text
    section: Text
    page: int = Field(ge=1)
    chunk_id: Text
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    parent_sha256: Digest


class Release(Record):
    document: Text
    pdf_sha256: Digest
    corpus_sha256: Digest
    review_revision: Text
    relation: Literal["authority_for"]
    modality: Literal["may"]
    polarity: Literal["affirmative"]
    scope_complete: Literal[True]
    conditions: list[Text]
    exceptions: list[Text]
    conflicts: list[Text]
    definitions: list[Text]
    governing_provisions: list[Text]
    entries: list[Entry]


def load_release(path: Path, digest: str, corpus: ApprovedCorpus) -> tuple[ApprovedCorpus, FactRegistry]:
    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Review release digest mismatch")
    release = Release.model_validate_json(data)
    if (release.document != corpus.document.document_name or release.pdf_sha256 != corpus.document.pdf_sha256
            or release.corpus_sha256 != corpus.corpus_revision):
        raise ValueError("Review release source mismatch")
    ids = [entry.fact_id for entry in release.entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate decision for fact ID")
    revision = release.review_revision
    scope = ReviewScope((corpus.document,), PolicyRelation.AUTHORITY_FOR, corpus.corpus_revision, revision,
                        tuple(release.definitions), tuple(release.governing_provisions), tuple(release.exceptions),
                        tuple(release.conflicts), release.scope_complete)
    facts = []
    for entry in release.entries:
        if entry.status == "PENDING_REVIEW":
            continue
        if not entry.reviewer or not entry.decision_date:
            raise ValueError("Missing reviewer decision details")
        if entry.status == "REJECTED":
            continue
        citation = EvidenceCitation(release.document, entry.section, entry.page, entry.chunk_id,
                                    SourceSpan(entry.start, entry.end))
        witness = SourceWitness(corpus.document, corpus.corpus_revision, revision, entry.parent_sha256,
                                citation, entry.quotation)
        facts.append(ReviewedPolicyFact(entry.fact_id, revision, revision, scope.policy_family, (witness,),
                                       entry.actor, entry.action, entry.object, release.modality, release.polarity,
                                       entry.scope, tuple(release.conditions), tuple(release.exceptions)))
    return replace(corpus, review_revision=revision), FactRegistry(scope, tuple(facts))
