"""Deterministic extraction of traceable units from retrieved chunks."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace

from ..hybrid.engine import HybridSearchResult
from .models import ExtractionMethod, SourceSpan, SourceUnit, UnitType

_NUMBERED_ITEM_RE = re.compile(
    r"(?m)(?<!\S)(\d+(?:\.\d+)*[.)])(?:[ \t]+)"
)


def _is_table_fragment(text: str, section: str) -> bool:
    candidate = text.strip()
    if candidate.startswith(("•", "-", "|")):
        return True
    if re.match(r"^(?:Sr\.?\s*No\.?|Penalties?|Acts of Indiscipline)\b", candidate, re.I):
        return True
    return bool(re.search(r"(?:penalt|statutory)", section, re.I))


def _is_heading(text: str) -> bool:
    candidate = text.strip()
    if not candidate or len(candidate.split()) > 12:
        return False
    if candidate.endswith((".", ",", ";", ":")):
        return False
    if candidate.isupper():
        return True
    if re.match(r"^\d+(?:\.\d+)*[\s.)-]+", candidate):
        cased = "".join(character for character in candidate if character.isalpha())
        return bool(cased and cased.isupper())
    return False


def _trimmed_span(
    text: str,
    start: int,
    end: int,
) -> tuple[int, int]:
    """Return offsets around non-whitespace text without changing that text."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _ends_with_terminal_punctuation(text: str) -> bool:
    return text.rstrip().endswith((".", "!", "?", ")"))


def _make_unit(
    chunk: HybridSearchResult,
    text: str,
    span: SourceSpan,
    unit_type: UnitType,
    is_complete: bool,
    extraction_method: ExtractionMethod,
) -> SourceUnit:
    return SourceUnit(
        chunk_id=chunk.chunk_id,
        document_name=chunk.document_name,
        category=chunk.category,
        section=chunk.section,
        page_number=chunk.page_number,
        full_chunk_text=chunk.text,
        text=text,
        span=span,
        unit_type=unit_type,
        is_complete=is_complete,
        extraction_method=extraction_method,
    )


def _split_sentences(
    chunk: HybridSearchResult,
    block_start: int,
    block_end: int,
) -> tuple[SourceUnit, ...]:
    text = chunk.text
    block = text[block_start:block_end]
    sentence_bounds: list[tuple[int, int]] = []
    sentence_start = 0

    for match in re.finditer(r"[.!?](?:[\"'”’)\]]*)", block):
        sentence_end = match.end()
        raw_start = block_start + sentence_start
        raw_end = block_start + sentence_end
        raw_start, raw_end = _trimmed_span(text, raw_start, raw_end)
        if raw_start < raw_end:
            sentence_bounds.append((raw_start, raw_end))
        sentence_start = sentence_end

    if sentence_start < len(block):
        raw_start = block_start + sentence_start
        raw_end = block_end
        raw_start, raw_end = _trimmed_span(text, raw_start, raw_end)
        if raw_start < raw_end:
            sentence_bounds.append((raw_start, raw_end))

    units: list[SourceUnit] = []
    for start, end in sentence_bounds:
        unit_text = text[start:end]
        terminal = _ends_with_terminal_punctuation(unit_text)
        units.append(
            _make_unit(
                chunk,
                unit_text,
                SourceSpan(start, end),
                UnitType.SENTENCE,
                terminal,
                ExtractionMethod.SENTENCE_SPLIT,
            )
        )
    return tuple(units)


def _extract_block(
    chunk: HybridSearchResult,
    block_start: int,
    block_end: int,
) -> tuple[SourceUnit, ...]:
    text = chunk.text
    start, end = _trimmed_span(text, block_start, block_end)
    if start >= end:
        return ()

    block = text[start:end]

    if _is_heading(block):
        return (
            _make_unit(
                chunk,
                block,
                SourceSpan(start, end),
                UnitType.HEADING,
                True,
                ExtractionMethod.HEADING_DETECTION,
            ),
        )

    numbered = tuple(
        unit
        for unit in _split_numbered_items_in_range(chunk, start, end)
    )
    if numbered:
        return numbered

    if _is_table_fragment(block, chunk.section):
        return (
            _make_unit(
                chunk,
                block,
                SourceSpan(start, end),
                UnitType.TABLE_ROW,
                False,
                ExtractionMethod.TABLE_ROW_DETECTION,
            ),
        )

    if not re.search(r"[.!?]", block):
        return (
            _make_unit(
                chunk,
                block,
                SourceSpan(start, end),
                UnitType.CONTINUATION,
                False,
                ExtractionMethod.CONTINUATION_DETECTION,
            ),
        )

    sentences = _split_sentences(chunk, start, end)
    if sentences:
        return sentences

    first = block.lstrip()
    first_character = first[:1]
    appears_continuation = (
        bool(first_character and first_character.islower())
        or not block.rstrip().endswith((".", "!", "?"))
    )
    if appears_continuation:
        unit_type = UnitType.CONTINUATION
        method = ExtractionMethod.CONTINUATION_DETECTION
        is_complete = False
    else:
        unit_type = UnitType.PARAGRAPH
        method = ExtractionMethod.PARAGRAPH_SPLIT
        is_complete = True

    return (
        _make_unit(
            chunk,
            block,
            SourceSpan(start, end),
            unit_type,
            is_complete,
            method,
        ),
    )


def _split_numbered_items_in_range(
    chunk: HybridSearchResult,
    range_start: int,
    range_end: int,
) -> tuple[SourceUnit, ...]:
    text = chunk.text
    matches = [
        match
        for match in _NUMBERED_ITEM_RE.finditer(text, range_start, range_end)
    ]
    if not matches:
        return ()

    units: list[SourceUnit] = []
    for index, match in enumerate(matches):
        item_start = match.start()
        item_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else range_end
        )
        item_start, item_end = _trimmed_span(text, item_start, item_end)
        if item_start >= item_end:
            continue
        unit_text = text[item_start:item_end]
        is_complete = _ends_with_terminal_punctuation(unit_text)
        units.append(
            _make_unit(
                chunk,
                unit_text,
                SourceSpan(item_start, item_end),
                UnitType.NUMBERED_ITEM,
                is_complete,
                ExtractionMethod.NUMBERED_ITEM_SPLIT,
            )
        )
    return tuple(units)


def extract_source_units(
    chunks: Sequence[HybridSearchResult],
) -> tuple[SourceUnit, ...]:
    """Extract exact, deterministic source units from one-chunk-at-a-time spans."""
    units: list[SourceUnit] = []

    for chunk in chunks:
        if not chunk.text.strip():
            continue

        paragraph_matches = list(
            re.finditer(r"\n\s*\n+", chunk.text)
        )
        if not paragraph_matches:
            units.extend(_extract_block(chunk, 0, len(chunk.text)))
            continue

        block_start = 0
        for separator in paragraph_matches:
            if block_start < separator.start():
                units.extend(_extract_block(chunk, block_start, separator.start()))
            block_start = separator.end()
        if block_start < len(chunk.text):
            units.extend(_extract_block(chunk, block_start, len(chunk.text)))

    finalized: list[SourceUnit] = []
    for unit in units:
        if finalized:
            previous = finalized[-1]
            continues_incomplete_numbered_item = (
                previous.chunk_id == unit.chunk_id
                and previous.unit_type is UnitType.NUMBERED_ITEM
                and not previous.is_complete
                and unit.unit_type not in (
                    UnitType.NUMBERED_ITEM,
                    UnitType.HEADING,
                )
            )
            if continues_incomplete_numbered_item:
                unit = replace(
                    unit,
                    unit_type=UnitType.CONTINUATION,
                    is_complete=False,
                    extraction_method=ExtractionMethod.CONTINUATION_DETECTION,
                )
        finalized.append(unit)

    return tuple(finalized)
