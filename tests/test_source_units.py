import pytest

from campus_help.answer.models import (
    ExtractionMethod,
    SourceSpan,
    SourceUnit,
    UnitType,
)
from campus_help.answer.source_units import extract_source_units
from campus_help.hybrid.engine import HybridSearchResult


def _chunk(
    chunk_id: str,
    text: str,
    *,
    document_name: str = "rules.pdf",
    category: str = "discipline",
    section: str = "Policy",
    page_number: int = 3,
) -> HybridSearchResult:
    return HybridSearchResult(
        chunk_id=chunk_id,
        document_name=document_name,
        category=category,
        section=section,
        page_number=page_number,
        text=text,
        bm25_rank=1,
        semantic_rank=2,
        rrf_score=0.03,
    )


def test_sentence_extraction_preserves_exact_spans():
    chunk = _chunk("s1", "Students must attend. Late arrivals are noted.")
    units = extract_source_units([chunk])

    assert [unit.text for unit in units] == [
        "Students must attend.",
        "Late arrivals are noted.",
    ]
    assert [unit.span for unit in units] == [
        SourceSpan(0, 21),
        SourceSpan(22, 46),
    ]
    assert all(unit.full_chunk_text[unit.span.start:unit.span.end] == unit.text for unit in units)
    assert all(unit.unit_type is UnitType.SENTENCE for unit in units)


def test_numbered_items_are_split_without_rewriting():
    chunk = _chunk("n1", "1. First rule.\n\n2. Second rule.\n\n3. Third rule.")
    units = extract_source_units([chunk])

    assert [unit.text for unit in units] == [
        "1. First rule.",
        "2. Second rule.",
        "3. Third rule.",
    ]
    assert all(unit.unit_type is UnitType.NUMBERED_ITEM for unit in units)
    assert all(unit.is_complete for unit in units)


def test_numbered_item_without_terminal_punctuation_is_incomplete():
    chunk = _chunk(
        "n-incomplete",
        "1. Cancellation of admission or withdrawal of degree for a specified",
    )
    unit = extract_source_units([chunk])[0]

    assert unit.text == (
        "1. Cancellation of admission or withdrawal of degree for a specified"
    )
    assert unit.unit_type is UnitType.NUMBERED_ITEM
    assert not unit.is_complete


def test_complete_numbered_item_with_terminal_punctuation_is_complete():
    chunk = _chunk("n-complete", "3. Expulsion.")
    unit = extract_source_units([chunk])[0]

    assert unit.text == "3. Expulsion."
    assert unit.unit_type is UnitType.NUMBERED_ITEM
    assert unit.is_complete


def test_numbered_item_ending_with_closing_parenthesis_is_complete():
    chunk = _chunk(
        "n-parenthesis",
        "29. Cooking food in hostel rooms (Use of hot plates, electric cooker etc.)",
    )
    unit = extract_source_units([chunk])[0]

    assert unit.text.endswith("etc.)")
    assert unit.unit_type is UnitType.NUMBERED_ITEM
    assert unit.is_complete


def test_sentence_after_incomplete_numbered_item_is_marked_continuation():
    chunk = _chunk(
        "n-continuation",
        "1. Cancellation for a specified\n\nperiod.",
    )
    units = extract_source_units([chunk])

    assert units[0].unit_type is UnitType.NUMBERED_ITEM
    assert not units[0].is_complete
    assert units[1].text == "period."
    assert units[1].unit_type is UnitType.CONTINUATION
    assert not units[1].is_complete


def test_real_category_i_part_without_punctuation_is_incomplete():
    import json
    from pathlib import Path

    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    raw = next(
        chunk
        for chunk in payload["chunks"]
        if chunk["chunk_id"] == "0320a43289fbdbe8"
    )
    chunk = HybridSearchResult(
        chunk_id=raw["chunk_id"],
        document_name=raw["document_name"],
        category=raw["category"],
        section=raw["section"],
        page_number=raw["page_number"],
        text=raw["text"],
        bm25_rank=None,
        semantic_rank=None,
        rrf_score=0.0,
    )
    units = extract_source_units([chunk])

    problematic = next(
        unit
        for unit in units
        if unit.text.startswith("1. Cancellation")
    )
    assert problematic.text == (
        "1. Cancellation of admission or withdrawal of degree or denial "
        "of registration for a specified"
    )
    assert problematic.unit_type is UnitType.NUMBERED_ITEM
    assert not problematic.is_complete


def test_missing_item_22_is_not_reconstructed():
    import json
    from pathlib import Path

    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    raw = next(
        chunk
        for chunk in payload["chunks"]
        if chunk["chunk_id"] == "ff10accb8ee6929c"
    )
    chunk = HybridSearchResult(
        chunk_id=raw["chunk_id"],
        document_name=raw["document_name"],
        category=raw["category"],
        section=raw["section"],
        page_number=raw["page_number"],
        text=raw["text"],
        bm25_rank=None,
        semantic_rank=None,
        rrf_score=0.0,
    )
    units = extract_source_units([chunk])

    exact_item_22 = "Possession, use, or distribution of drugs or psychotropic substances"
    assert all(exact_item_22 not in unit.text for unit in units)


def test_paragraph_boundary_is_preserved():
    chunk = _chunk("p1", "First paragraph has no terminal mark\n\nSecond paragraph.")
    units = extract_source_units([chunk])

    assert units[0].text == "First paragraph has no terminal mark"
    assert units[0].unit_type is UnitType.CONTINUATION
    assert not units[0].is_complete
    assert units[1].text == "Second paragraph."
    assert units[1].span.start > units[0].span.end


def test_metadata_and_exact_offsets_are_preserved():
    chunk = _chunk(
        "m1",
        "A complete policy sentence.",
        document_name="rules.pdf",
        category="discipline",
        section="Appeals",
        page_number=5,
    )
    unit = extract_source_units([chunk])[0]

    assert unit.chunk_id == "m1"
    assert unit.document_name == "rules.pdf"
    assert unit.category == "discipline"
    assert unit.section == "Appeals"
    assert unit.page_number == 5
    assert unit.full_chunk_text == "A complete policy sentence."


def test_heading_is_detected_conservatively():
    chunk = _chunk("h1", "APPEAL PROCEDURE")
    units = extract_source_units([chunk])

    assert len(units) == 1
    assert units[0].text == "APPEAL PROCEDURE"
    assert units[0].unit_type is UnitType.HEADING
    assert units[0].is_complete
    assert units[0].extraction_method is ExtractionMethod.HEADING_DETECTION


def test_lowercase_continuation_is_incomplete():
    chunk = _chunk("c1", "for further action")
    units = extract_source_units([chunk])

    assert units[0].text == "for further action"
    assert units[0].unit_type is UnitType.CONTINUATION
    assert not units[0].is_complete


def test_empty_chunk_is_safe():
    assert extract_source_units([_chunk("empty", ""), _chunk("spaces", "   \n")]) == ()


def test_duplicate_text_keeps_each_occurrence():
    chunk = _chunk("dup", "Repeated rule. Repeated rule.")
    units = extract_source_units([chunk])

    assert [unit.text for unit in units] == ["Repeated rule.", "Repeated rule."]
    assert [unit.span.start for unit in units] == [0, 15]


def test_extraction_is_deterministic():
    chunk = _chunk("det", "Appeal is due in 5 days. The decision is final.")
    first = extract_source_units([chunk])
    second = extract_source_units([chunk])
    assert first == second


def test_invalid_span_is_rejected():
    with pytest.raises(ValueError):
        SourceUnit(
            chunk_id="bad",
            document_name="rules.pdf",
            category="discipline",
            section="General",
            page_number=1,
            full_chunk_text="abc",
            text="ab",
            span=SourceSpan(1, 3),
            unit_type=UnitType.SENTENCE,
            is_complete=True,
            extraction_method=ExtractionMethod.SENTENCE_SPLIT,
        )

    with pytest.raises(ValueError):
        SourceSpan(3, 2)


def test_mismatch_is_rejected():
    with pytest.raises(ValueError, match="must exactly match"):
        SourceUnit(
            chunk_id="bad",
            document_name="rules.pdf",
            category="discipline",
            section="General",
            page_number=1,
            full_chunk_text="abc",
            text="wrong",
            span=SourceSpan(0, 3),
            unit_type=UnitType.PARAGRAPH,
            is_complete=True,
            extraction_method=ExtractionMethod.PARAGRAPH_SPLIT,
        )


def test_real_discipline_json_defect_chunks_are_exact():
    import json
    from pathlib import Path

    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    by_id = {chunk["chunk_id"]: chunk for chunk in payload["chunks"]}

    ids = (
        "ff10accb8ee6929c",
        "d75de57ebb19414a",
        "8b899f2ff08fe95d",
        "d8fdccb230b145e7",
    )
    retrieved = tuple(
        HybridSearchResult(
            chunk_id=raw["chunk_id"],
            document_name=raw["document_name"],
            category=raw["category"],
            section=raw["section"],
            page_number=raw["page_number"],
            text=raw["text"],
            bm25_rank=None,
            semantic_rank=None,
            rrf_score=0.0,
        )
        for chunk_id in ids
        for raw in [by_id[chunk_id]]
    )

    units = extract_source_units(retrieved)
    assert len(units) > 0
    assert all(
        unit.full_chunk_text[unit.span.start:unit.span.end] == unit.text
        for unit in units
    )
