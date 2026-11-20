"""Deterministic evidence scoring and selection for M5.2."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from ..retrieval.tokenizer import tokenize
from .models import (
    EvidenceSelection,
    ScoredSourceUnit,
    SelectionDiagnostics,
    SourceUnit,
    UnitType,
)

STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "at",
        "be",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "when",
        "where",
        "which",
        "who",
        "with",
    }
)

POLICY_TERMS = frozenset(
    {
        "appeal",
        "category",
        "committee",
        "complaint",
        "conduct",
        "deadline",
        "disciplinary",
        "discipline",
        "enquiry",
        "evidence",
        "expulsion",
        "fine",
        "misconduct",
        "penalty",
        "punishment",
        "rule",
        "rules",
        "student",
        "students",
        "suspension",
        "university",
        "vice",
        "witness",
        "witnesses",
    }
)

NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[.,]\d+)*(?!\w)")
SELECTION_THRESHOLD = 0.15


def _meaningful_terms(text: str) -> tuple[str, ...]:
    terms = []
    seen = set()
    for term in tokenize(text):
        if term in STOP_WORDS or len(term) < 2:
            continue
        if term not in seen:
            seen.add(term)
            terms.append(term)
    return tuple(terms)


def _numbers(text: str) -> tuple[str, ...]:
    numbers = []
    seen = set()
    for match in NUMBER_RE.findall(text):
        normalized = match.rstrip(".").replace(",", "")
        if normalized not in seen:
            seen.add(normalized)
            numbers.append(normalized)
    return tuple(numbers)


def _number_contexts(text: str) -> dict[str, tuple[str, ...]]:
    """Return normalized terms following a numeric value in source text."""
    contexts: dict[str, list[str]] = {}
    for match in re.finditer(r"(?<!\w)(\d+(?:[.,]\d+)*)(?!\w)", text):
        number = match.group(1).rstrip(".").replace(",", "")
        following = text[match.end():match.end() + 80]
        terms = []
        for term in tokenize(following):
            if term in STOP_WORDS:
                continue
            if term in {"and", "or"}:
                continue
            normalized = term[:-1] if len(term) > 4 and term.endswith("s") else term
            if normalized not in terms:
                terms.append(normalized)
            if len(terms) == 3:
                break
        contexts.setdefault(number, [])
        for term in terms:
            if term not in contexts[number]:
                contexts[number].append(term)
    return {number: tuple(terms) for number, terms in contexts.items()}


def _contexts_compatible(
    query_context: tuple[str, ...],
    unit_context: tuple[str, ...],
) -> bool:
    if not query_context or not unit_context:
        return True
    return bool(set(query_context).intersection(unit_context))


def _stable_unit_key(unit: SourceUnit) -> tuple[object, ...]:
    return (
        unit.document_name,
        unit.page_number,
        unit.section,
        unit.chunk_id,
        unit.span.start,
        unit.span.end,
        unit.text,
    )


def score_source_units(
    question: str,
    units: Sequence[SourceUnit],
) -> tuple[ScoredSourceUnit, ...]:
    """Score source units with a deterministic lexical relevance formula."""
    if not question.strip() or not units:
        return tuple(
            ScoredSourceUnit(
                source_unit=unit,
                relevance_score=0.0,
                query_term_coverage=0.0,
                matched_terms=(),
                matched_numbers=(),
                mismatched_numbers=(),
            )
            for unit in units
        )

    query_terms = _meaningful_terms(question)
    query_numbers = _numbers(question)
    query_set = set(query_terms)
    scored: list[ScoredSourceUnit] = []

    for unit in units:
        unit_terms = tuple(tokenize(unit.text))
        unit_meaningful = set(_meaningful_terms(unit.text))
        matched_terms = tuple(
            term for term in query_terms if term in unit_meaningful
        )
        coverage = (
            len(matched_terms) / len(query_terms)
            if query_terms
            else 0.0
        )
        overlap = (
            sum(min(Counter(unit_terms)[term], 1) for term in matched_terms)
            / max(len(set(unit_terms)), 1)
        )

        unit_number_contexts = _number_contexts(unit.text)
        query_number_contexts = _number_contexts(question)
        matched_numbers = tuple(
            number
            for number in query_numbers
            if number in unit_number_contexts
            and _contexts_compatible(
                query_number_contexts.get(number, ()),
                unit_number_contexts[number],
            )
        )
        mismatched_numbers = tuple(
            number
            for number in query_numbers
            if number not in unit_number_contexts
            or not _contexts_compatible(
                query_number_contexts.get(number, ()),
                unit_number_contexts.get(number, ()),
            )
        )

        if query_numbers:
            number_score = (
                len(matched_numbers) / len(query_numbers)
                if len(matched_numbers) == len(query_numbers)
                else -0.25
            )
        else:
            number_score = 0.0

        policy_matches = len(query_set.intersection(POLICY_TERMS).intersection(unit_meaningful))
        policy_score = min(policy_matches * 0.04, 0.12)

        score = (
            0.50 * coverage
            + 0.25 * min(overlap * 4.0, 1.0)
            + 0.20 * number_score
            + policy_score
        )

        if unit.unit_type is UnitType.HEADING:
            score -= 0.25
        if not unit.is_complete:
            score -= 0.35
        if unit.unit_type is UnitType.NUMBERED_ITEM and unit.is_complete:
            score += 0.03

        scored.append(
            ScoredSourceUnit(
                source_unit=unit,
                relevance_score=score,
                query_term_coverage=coverage,
                matched_terms=matched_terms,
                matched_numbers=matched_numbers,
                mismatched_numbers=mismatched_numbers,
            )
        )

    scored.sort(
        key=lambda scored_unit: (
            -scored_unit.relevance_score,
            -scored_unit.query_term_coverage,
            _stable_unit_key(scored_unit.source_unit),
        )
    )
    return tuple(scored)


def _deduplication_key(unit: SourceUnit) -> tuple[str, str]:
    normalized = " ".join(unit.text.split())
    return unit.chunk_id, normalized


def select_evidence(
    question: str,
    scored_units: Sequence[ScoredSourceUnit],
    *,
    max_evidence: int = 3,
) -> EvidenceSelection:
    """Select deterministic candidate evidence without making final answerability claims."""
    if max_evidence < 1:
        raise ValueError("max_evidence must be at least 1")

    ordered = tuple(
        sorted(
            scored_units,
            key=lambda scored_unit: (
                -scored_unit.relevance_score,
                -scored_unit.query_term_coverage,
                _stable_unit_key(scored_unit.source_unit),
            ),
        )
    )

    selected: list[ScoredSourceUnit] = []
    excluded: list[ScoredSourceUnit] = []
    seen: set[tuple[str, str]] = set()
    deduplicated_count = 0

    for scored in ordered:
        unit = scored.source_unit
        key = _deduplication_key(unit)

        if unit.unit_type is UnitType.HEADING:
            excluded.append(scored)
        elif not unit.is_complete:
            excluded.append(scored)
        elif key in seen:
            deduplicated_count += 1
            excluded.append(scored)
        elif scored.relevance_score < SELECTION_THRESHOLD:
            excluded.append(scored)
        elif len(selected) < max_evidence:
            seen.add(key)
            selected.append(scored)
        else:
            excluded.append(scored)

    diagnostics = SelectionDiagnostics(
        candidate_count=len(scored_units),
        selected_count=len(selected),
        excluded_count=len(excluded),
        deduplicated_count=deduplicated_count,
        max_evidence=max_evidence,
    )
    return EvidenceSelection(
        selected_candidates=tuple(selected),
        excluded_candidates=tuple(excluded),
        diagnostics=diagnostics,
    )
