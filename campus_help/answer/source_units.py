"""Deterministic extraction of traceable units from retrieved chunks."""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import replace

from ..hybrid.engine import HybridSearchResult
from .models import ExtractionMethod, SourceSpan, SourceUnit, UnitType

_NUMBERED_ITEM_RE = re.compile(
    r"(?m)(?<!\S)(\d+(?:\.\d+)*[.)])(?:[ \t]+)"
)
_LINE_BREAK_RE = re.compile(r"\r?\n(?:[ \t]*\r?\n)*")
_MODAL = r"(?:must|shall|will|may)"
_OPEN_END_RE = re.compile(rf"\b(?:{_MODAL}(?: be| have)?|the|their|any|by|of|to)$")
_PROSE_VERB_RE = re.compile(rf"\b(?:{_MODAL}|is|are|has|have)\b")
_BARE_MARKER_RE = re.compile(r"(?:[a-z]|[ivxlcdm]+|\d+)[.)]", re.I)
_DURATION_RE = re.compile(r"^\d+[ \t]+(?:working[ \t]+)?(?:days?|hours?|weeks?|months?)\b")
_POLICY_NOUN_PHRASE = (
    r"(?:(?:[0-9]+|a|an|the) )?(?:(?:written|signed|working) )?"
    r"(?:appeals?|applications?|requests?|forms?|signatures?|students?|"
    r"committees?|registrars?|hours?|days?|weeks?)"
)
_POLICY_PREDICATE = (
    rf"(?:(?:is|are|{_MODAL} be) (?:required|filed|submitted|permitted|prohibited)"
    rf"|{_MODAL} (?:attend|meet|elapse))"
)
_STANDALONE_POLICY_RE = re.compile(
    rf"{_POLICY_NOUN_PHRASE} {_POLICY_PREDICATE}"
    rf"(?: (?:for|with|to|by) {_POLICY_NOUN_PHRASE}"
    rf"| (?:before|after) {_POLICY_NOUN_PHRASE} {_POLICY_PREDICATE})?\.",
    re.ASCII | re.IGNORECASE,
)


def _is_explicit_row(text: str) -> bool:
    return text.startswith(("•", "-")) or "|" in text


def _is_table_fragment(text: str, section: str) -> bool:
    candidate = text.strip()
    if _is_explicit_row(candidate):
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


def _continues_prose(head: str, following: str, section: str) -> bool:
    """Recognize an open grammatical link, never a paragraph break by default."""
    marker = _NUMBERED_ITEM_RE.match(head)
    body = head[marker.end():] if marker else head
    if not body or not body[0].isupper() or not following:
        return False
    if not marker and not _PROSE_VERB_RE.search(body):
        return False
    if any(
        _is_table_fragment(part, section) or "\t" in part
        for part in (body, following)
    ):
        return False
    if re.search(r"[.!?:;]", body) or _NUMBERED_ITEM_RE.search(following):
        return False
    if re.search(r"[.!?].", following):
        return False
    if re.search(r"\bwithin$", body) and _DURATION_RE.match(following):
        return True
    return bool(
        _OPEN_END_RE.search(body)
        and not _BARE_MARKER_RE.fullmatch(following)
        and re.match(r"[a-z][\w’'/-]*(?:,?\s+\w|[.!?]$)", following)
    )


def _chunk_units(chunk: HybridSearchResult) -> Iterator[SourceUnit]:
    text = chunk.text
    start = line_start = 0
    separators = iter(_LINE_BREAK_RE.finditer(text))
    current = next(separators, None)
    while current is not None:
        following = next(separators, None)
        next_end = following.start() if following else len(text)
        line = text[line_start:current.start()].strip()
        next_line = text[current.end():next_end].strip()
        breaks = current.group().count("\n")
        if breaks == 1:
            split = (
                _is_explicit_row(line) or _is_explicit_row(next_line)
                or _is_heading(line) or _is_heading(next_line)
                or _NUMBERED_ITEM_RE.match(next_line) is not None
            )
        else:
            split = breaks > 2 or not _continues_prose(
                text[start:current.start()].strip(), next_line, chunk.section,
            )
        if split:
            yield from _extract_block(chunk, start, current.start())
            start = current.end()
        line_start = current.end()
        current = following
    yield from _extract_block(chunk, start, len(text))


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
        if unit_text[0].islower() or unit_text[0].isdigit():
            tail = (
                _STANDALONE_POLICY_RE.fullmatch(unit_text) is None
                or (start, end) != _trimmed_span(text, 0, len(text))
            )
        else:
            tail = (
                _BARE_MARKER_RE.fullmatch(unit_text) is not None
                or not any(character.isalpha() for character in unit_text)
            )
        units.append(
            _make_unit(
                chunk,
                unit_text,
                SourceSpan(start, end),
                UnitType.CONTINUATION if tail else UnitType.SENTENCE,
                not tail and _ends_with_terminal_punctuation(unit_text),
                ExtractionMethod.CONTINUATION_DETECTION
                if tail else ExtractionMethod.SENTENCE_SPLIT,
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

    explicit_row = _is_explicit_row(block)
    if not explicit_row and _is_heading(block):
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

    if not explicit_row:
        numbered = _split_numbered_items_in_range(chunk, start, end)
        if numbered:
            return numbered

    if explicit_row or _is_table_fragment(block, chunk.section):
        return (
            _make_unit(
                chunk, block, SourceSpan(start, end), UnitType.TABLE_ROW,
                False, ExtractionMethod.TABLE_ROW_DETECTION,
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
    finalized: list[SourceUnit] = []
    for chunk in chunks:
        previous = None
        for unit in _chunk_units(chunk):
            if (
                previous is not None
                and not previous.is_complete
                and (
                    previous.unit_type is UnitType.NUMBERED_ITEM
                    or previous.text.endswith("/")
                    or re.search(r"\bincluding$", previous.text)
                )
                and unit.unit_type not in (
                    UnitType.NUMBERED_ITEM,
                    UnitType.HEADING,
                    UnitType.TABLE_ROW,
                )
            ):
                unit = replace(
                    unit,
                    unit_type=UnitType.CONTINUATION,
                    is_complete=False,
                    extraction_method=ExtractionMethod.CONTINUATION_DETECTION,
                )
            finalized.append(unit)
            previous = unit

    return tuple(finalized)
