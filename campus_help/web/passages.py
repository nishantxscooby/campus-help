"""Reviewed question-to-passage bindings and independently authenticated reading excerpts."""

from datetime import date
from hashlib import sha256
from typing import Literal
import re

import fitz
from pydantic import Field

from ..answer.source_units import extract_source_units
from ..answer.verification import _check_pages
from .reviews import Digest, Record, Text


def normalized(question):
    return " ".join(question.casefold().strip().removesuffix("?").split())


class PassageSpan(Record):
    page: int = Field(ge=1)
    chunk_id: str | None
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quotation: Text
    parent_sha256: Digest


class Passage(Record):
    fact_id: Text
    questions: list[Text]
    relation: Literal["deadline", "review_authority", "penalty_category", "listed_conduct", "committee_eligibility", "source_statement"]
    claim: Text
    context: Text
    exceptions: Text
    witnesses: list[PassageSpan] = Field(min_length=1)
    # Binds all intervening PDF text, including list/category changes, to this review.
    passage_sha256: Digest
    review_complete: bool = False
    conflicts: list[Text] = Field(default_factory=list)
    status: Literal["PENDING_REVIEW", "REJECTED", "APPROVED"]
    reviewer: Text | None
    decision_date: date | None


class PassageRelease(Record):
    format: Literal["reviewed-passages-v1"]
    document: Text
    pdf_sha256: Digest
    corpus_sha256: Digest
    review_revision: Text
    entries: list[Passage]


def digest(text):
    return sha256(text.encode()).hexdigest()


def compact(text):
    return " ".join(text.split())


def authenticate(card, pdf_bytes, chunks):
    """Locate each parent uniquely, check its slice, then check order and reviewed PDF interval."""
    if len({w.page for w in card.witnesses}) != 1:
        raise ValueError("Cross-page relationship requires separate review support")
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        source_page = doc[card.witnesses[0].page - 1]
        if card.relation == "source_statement" and any(
                run["type"] == 3 for run in source_page.get_texttrace()):
            raise ValueError("Invisible text requires a separately reviewed transcription")
        raw = source_page.get_text()
    page = compact(raw)
    positions = []
    for w in card.witnesses:
        if w.chunk_id is None:
            parent = raw
        else:
            chunk = chunks[w.chunk_id]
            if chunk.page_number != w.page:
                raise ValueError("Wrong witness page")
            _check_pages(pdf_bytes, (chunk,))
            parent = chunk.text
        if (w.end > len(parent) or parent[w.start:w.end] != w.quotation
                or digest(parent) != w.parent_sha256):
            raise ValueError("Stale source span")
        phrase = compact(w.quotation)
        if page.count(phrase) != 1:
            raise ValueError("Ambiguous source location")
        start = page.index(phrase)
        if positions and start < positions[-1][1]:
            raise ValueError("Out-of-order witnesses")
        positions.append((start, start + len(phrase)))
    interval = page[positions[0][0]:positions[-1][1]]
    if digest(interval) != card.passage_sha256:
        raise ValueError("Unreviewed span relationship")
    if card.relation == "source_statement":
        witness = card.witnesses[0]
        if (not witness.chunk_id or chunks[witness.chunk_id].text.strip() != witness.quotation
                or not any(unit.is_complete and unit.text == witness.quotation for unit in
                           extract_source_units((chunks[witness.chunk_id],)))):
            raise ValueError("Reviewed standalone statement must include its full parent")
    clause = compact(card.witnesses[-1].quotation)
    if card.relation in {"deadline", "review_authority"}:
        if len(positions) != 2 or not re.fullmatch(r"(?:\d+\. )?Appeal:", compact(card.witnesses[0].quotation)):
            raise ValueError("Missing appeal heading")
        if re.search(r"\b\d+\. [A-Z][a-z]+:", interval[len(card.witnesses[0].quotation):]):
            raise ValueError("Intervening section")
        if card.relation == "deadline" and not (
                "appeal" in clause.lower() and re.search(r"within \d+ (?:working |calendar )?days? (?:of|after) ", clause)
                and clause.endswith(".")):
            raise ValueError("Incomplete appeal deadline")
        if card.relation == "review_authority" and not re.search(r"review the (major|minor) penalties", clause):
            raise ValueError("Missing penalty review authority")
    if card.relation == "committee_eligibility" and not (
            len(positions) == 1 and "not debar such member from sitting as a member" in clause):
        raise ValueError("Missing committee eligibility clause")
    if card.relation == "source_statement" and (
            len(card.witnesses) != 1 or card.claim != card.witnesses[0].quotation
            or not clause.endswith((".", "?", "!"))):
        raise ValueError("Reviewed statement must reproduce its complete quoted statement")
    if card.relation == "listed_conduct":
        if (len(positions) != 3 or "MISCONDUCT" not in card.witnesses[0].quotation
                or not compact(card.witnesses[1].quotation).startswith("CATEGORY")
                or "CATEGORY" in page[positions[1][1]:positions[2][0]]
                or not re.match(r"\d+\. ", card.witnesses[-1].quotation)):
            raise ValueError("Missing governing misconduct category")
    if card.relation == "penalty_category":
        if (len(positions) != 3 or "may impose" not in compact(card.witnesses[0].quotation)
                or not card.witnesses[1].quotation.startswith("CATEGORY")
                or "CATEGORY" in page[positions[1][1]:positions[2][0]]
                or not re.match(r"\d+\. ", card.witnesses[-1].quotation)):
            raise ValueError("Missing governing penalty provision")


def validate_catalog(release, config):
    if (release.document, release.pdf_sha256, release.corpus_sha256) != (
            config.document.document_name, config.document.pdf_sha256, config.corpus_revision):
        raise ValueError("Passage release source mismatch")
    ids = set()
    questions = set()
    for card in release.entries:
        keys = {normalized(q) for q in card.questions}
        if card.fact_id in ids or questions.intersection(keys):
            raise ValueError("Conflicting review entries")
        if card.status == "APPROVED" and not (card.reviewer and card.decision_date and keys and card.review_complete and not card.conflicts
                                               and not card.exceptions.startswith("Pending")):
            raise ValueError("Incomplete review record")
        ids.add(card.fact_id)
        questions.update(keys)


def locate(question, release):
    q = normalized(question)
    exact = [c for c in release.entries if q in map(normalized, c.questions)]
    if exact:
        return exact, "exact"
    templates = [c for c in release.entries if c.relation == "source_statement" and any(
        p.count("{value}") == 1 and re.fullmatch(re.escape(p).replace(r"\{value\}",r"\d{1,4}(?:\.\d{1,3})?"),question,re.I)
        for p in c.questions)]
    if len(templates) == 1:
        return templates, "numeric"
    if re.search(r"\bscholarships?\b", q):
        return [], "unsupported_document"
    if "appeal" in q and "who reviews" in q and "deadline" in q:
        return [], "clarify_appeal"
    if "restigate" in q or "rustigate" in q:
        ids, reason = ["rustication"], "possible_typo"
    elif "debar" in q and "rusticat" in q:
        ids, reason = ["rustication", "debar"], "comparison"
    elif "debar" in q:
        ids, reason = ["debar"], "student_debarment"
    elif "rusticat" in q:
        ids, reason = ["rustication"], "penalty_mapping"
    elif "hostel" in q and ("rule" in q or "punish" in q):
        return [], "clarify_hostel"
    elif "appeal" in q and ("deadline" in q or "days" in q or "date" in q):
        ids, reason = ["appeal"], "related_only"
    elif "penalt" in q and "review" in q:
        ids, reason = ["major" if "minor" not in q else "minor"], "related_only"
    elif "punishment" in q or "what happens if" in q:
        return [], "clarify_penalty"
    else:
        return [], ""
    return [c for c in release.entries if c.fact_id in ids], reason
