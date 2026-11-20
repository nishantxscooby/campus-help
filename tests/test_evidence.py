import json
from pathlib import Path

import pytest

from campus_help.answer.evidence import score_source_units, select_evidence
from campus_help.answer.models import (
    EvidenceSelection,
    ExtractionMethod,
    SourceSpan,
    SourceUnit,
    UnitType,
)
from campus_help.answer.source_units import extract_source_units
from campus_help.hybrid.engine import HybridSearchResult


def _unit(
    text: str,
    *,
    chunk_id: str = "chunk",
    unit_type: UnitType = UnitType.SENTENCE,
    is_complete: bool = True,
    start: int = 0,
) -> SourceUnit:
    return SourceUnit(
        chunk_id=chunk_id,
        document_name="rules.pdf",
        category="discipline",
        section="Policy",
        page_number=3,
        full_chunk_text=text,
        text=text,
        span=SourceSpan(start, start + len(text)),
        unit_type=unit_type,
        is_complete=is_complete,
        extraction_method=(
            ExtractionMethod.SENTENCE_SPLIT
            if unit_type is UnitType.SENTENCE
            else ExtractionMethod.NUMBERED_ITEM_SPLIT
        ),
    )


def _full_chunk_unit(
    full_text: str,
    text: str,
    start: int,
    *,
    chunk_id: str = "chunk",
    unit_type: UnitType = UnitType.SENTENCE,
    is_complete: bool = True,
) -> SourceUnit:
    return SourceUnit(
        chunk_id=chunk_id,
        document_name="rules.pdf",
        category="discipline",
        section="Policy",
        page_number=3,
        full_chunk_text=full_text,
        text=text,
        span=SourceSpan(start, start + len(text)),
        unit_type=unit_type,
        is_complete=is_complete,
        extraction_method=ExtractionMethod.SENTENCE_SPLIT,
    )


def test_exact_token_overlap_and_term_matching():
    unit = _unit("The appeal must be filed within five working days.")
    scored = score_source_units("appeal five working days", [unit])[0]

    assert "appeal" in scored.matched_terms
    assert "working" in scored.matched_terms
    assert scored.query_term_coverage == pytest.approx(1.0)
    assert scored.relevance_score > 0.15


def test_query_term_coverage_is_fractional():
    unit = _unit("The appeal deadline is stated.")
    scored = score_source_units(
        "appeal deadline punishment",
        [unit],
    )[0]

    assert scored.query_term_coverage == pytest.approx(2 / 3)


def test_number_matching_and_mismatching():
    matching = _unit("The appeal deadline is 5 working days.")
    mismatching = _unit("The appeal deadline is 10 working days.")

    match_score = score_source_units("appeal deadline 5 working days", [matching])[0]
    mismatch_score = score_source_units("appeal deadline 5 working days", [mismatching])[0]

    assert match_score.matched_numbers == ("5",)
    assert match_score.mismatched_numbers == ()
    assert mismatch_score.matched_numbers == ()
    assert mismatch_score.mismatched_numbers == ("5",)
    assert match_score.relevance_score > mismatch_score.relevance_score


def test_number_units_days_and_years_are_distinguished():
    days = _unit("The appeal deadline is 5 days.")
    years = _unit("The suspension period is 5 years.")

    days_score = score_source_units("appeal deadline 5 days", [days])[0]
    years_score = score_source_units("appeal deadline 5 days", [years])[0]

    assert days_score.matched_numbers == ("5",)
    assert years_score.matched_numbers == ()
    assert years_score.mismatched_numbers == ("5",)
    assert days_score.relevance_score > years_score.relevance_score


def test_different_numbers_with_identical_surrounding_words():
    five = _unit("The appeal deadline is 5 working days.")
    ten = _unit("The appeal deadline is 10 working days.")
    five_score = score_source_units("appeal deadline 5 working days", [five])[0]
    ten_score = score_source_units("appeal deadline 5 working days", [ten])[0]

    assert five_score.relevance_score > ten_score.relevance_score
    assert ten_score.mismatched_numbers == ("5",)


def test_no_meaningful_terms_after_stop_words():
    unit = _unit("The appeal process is documented.")
    scored = score_source_units("how can", [unit])[0]

    assert scored.matched_terms == ()
    assert scored.query_term_coverage == 0.0
    assert not select_evidence("how can", (scored,), max_evidence=3).selected_candidates


def test_repeated_terms_do_not_duplicate_query_coverage():
    unit = _unit("An appeal must be filed.")
    scored = score_source_units("appeal appeal appeal", [unit])[0]

    assert scored.matched_terms == ("appeal",)
    assert scored.query_term_coverage == 1.0


def test_negation_and_condition_remain_unresolved():
    negated = _unit("The university will not suspend a student.")
    condition = _unit("Suspension is prohibited unless misconduct occurs.")

    negated_score = score_source_units("not suspend", [negated])[0]
    condition_score = score_source_units("unless the student is suspended", [condition])[0]

    assert negated_score.relevance_score > 0.15
    assert condition_score.relevance_score > 0.15
    assert negated_score.matched_terms
    assert condition_score.matched_terms


def test_heading_is_excluded():
    heading = _unit(
        "APPEAL PROCEDURE",
        unit_type=UnitType.HEADING,
    )
    selection = select_evidence(
        "appeal procedure",
        score_source_units("appeal procedure", [heading]),
    )

    assert selection.selected_candidates == ()
    assert selection.excluded_candidates[0].source_unit is heading


def test_incomplete_fragment_is_excluded():
    fragment = _unit(
        "to the Vice-Chancellor",
        is_complete=False,
        unit_type=UnitType.CONTINUATION,
    )
    selection = select_evidence(
        "to whom should an appeal be filed",
        score_source_units("to whom should an appeal be filed", [fragment]),
    )

    assert selection.selected_candidates == ()


def test_complete_numbered_item_is_selected():
    item = _unit(
        "1. A written appeal must be filed within 5 working days.",
        unit_type=UnitType.NUMBERED_ITEM,
    )
    selection = select_evidence(
        "appeal written 5 working days",
        score_source_units("appeal written 5 working days", [item]),
        max_evidence=3,
    )

    assert len(selection.selected_candidates) == 1
    assert selection.selected_candidates[0].source_unit.text == item.text


def test_duplicate_evidence_is_deduplicated():
    first = _unit("The rule is repeated.", chunk_id="a")
    second = _unit("The rule is repeated.", chunk_id="a")
    selection = select_evidence(
        "rule repeated",
        score_source_units("rule repeated", [first, second]),
    )

    assert len(selection.selected_candidates) == 1
    assert selection.diagnostics.deduplicated_count == 1


def test_repeated_text_with_different_offsets_is_deduplicated():
    full_text = "The rule is repeated. The rule is repeated."
    first = _full_chunk_unit(
        full_text,
        "The rule is repeated.",
        0,
        chunk_id="same",
    )
    second = _full_chunk_unit(
        full_text,
        "The rule is repeated.",
        22,
        chunk_id="same",
    )
    selection = select_evidence(
        "rule repeated",
        score_source_units("rule repeated", [first, second]),
    )

    assert len(selection.selected_candidates) == 1


def test_stable_ordering_uses_score_then_metadata():
    later_page = _unit(
        "An appeal to the Vice-Chancellor.",
        chunk_id="z",
    )
    earlier_page = SourceUnit(
        chunk_id="a",
        document_name="rules.pdf",
        category="discipline",
        section="Appeals",
        page_number=2,
        full_chunk_text="An appeal to the Vice-Chancellor.",
        text="An appeal to the Vice-Chancellor.",
        span=SourceSpan(0, 33),
        unit_type=UnitType.SENTENCE,
        is_complete=True,
        extraction_method=ExtractionMethod.SENTENCE_SPLIT,
    )
    scored = score_source_units(
        "appeal Vice-Chancellor",
        [later_page, earlier_page],
    )
    selection = select_evidence(
        "appeal Vice-Chancellor",
        scored,
        max_evidence=2,
    )
    assert [item.source_unit.chunk_id for item in selection.selected_candidates] == ["a", "z"]


def test_empty_question_and_empty_collection():
    unit = _unit("Policy text.")
    assert score_source_units("   ", [unit])[0].relevance_score == 0.0
    assert score_source_units("rule", []) == ()

    selection = select_evidence(
        "",
        score_source_units("", []),
    )
    assert selection.selected_candidates == ()


def test_invalid_max_evidence():
    with pytest.raises(ValueError, match="max_evidence"):
        select_evidence("appeal", (), max_evidence=0)


def test_no_relevant_evidence():
    unit = _unit("The library closes at 6 pm.")
    selection = select_evidence(
        "disciplinary appeal deadline",
        score_source_units("disciplinary appeal deadline", [unit]),
    )

    assert selection.selected_candidates == ()


def test_multiple_relevant_candidates():
    appeal = _unit("A written appeal is filed within 5 working days.")
    authority = _unit("The Vice-Chancellor reviews major penalties.")
    selection = select_evidence(
        "appeal Vice-Chancellor 5 days penalty",
        score_source_units(
            "appeal Vice-Chancellor 5 days penalty",
            [appeal, authority],
        ),
        max_evidence=2,
    )

    assert len(selection.selected_candidates) == 2


def test_exact_source_quotation_and_span_are_preserved():
    full_text = "Prefix. The appeal deadline is 5 working days."
    unit = _full_chunk_unit(
        full_text,
        "The appeal deadline is 5 working days.",
        8,
        chunk_id="span",
    )
    selection = select_evidence(
        "appeal deadline 5 working days",
        score_source_units(
            "appeal deadline 5 working days",
            [unit],
        ),
    )
    selected = selection.selected_candidates[0].source_unit

    assert selected.text == "The appeal deadline is 5 working days."
    assert selected.full_chunk_text[selected.span.start:selected.span.end] == selected.text


def test_negative_keyword_overlap_is_not_answerability():
    unit = _unit("The appeal form is mentioned in a library notice.")
    scored = score_source_units("appeal library", [unit])[0]
    selection = select_evidence(
        "appeal library",
        (scored,),
    )

    assert len(selection.selected_candidates) == 1
    assert "library" in scored.matched_terms
    assert scored.relevance_score < 1.0


def test_same_text_in_different_chunks_is_not_deduplicated():
    first = _unit("The rule applies.", chunk_id="policy-a")
    second = _unit("The rule applies.", chunk_id="policy-b")
    selection = select_evidence(
        "rule applies",
        score_source_units("rule applies", [first, second]),
        max_evidence=2,
    )

    assert len(selection.selected_candidates) == 2
    assert {item.source_unit.chunk_id for item in selection.selected_candidates} == {
        "policy-a",
        "policy-b",
    }


def test_identical_wording_in_different_policy_sections_is_preserved():
    general_text = "Written notice is required."
    appeal_text = "Written notice is required."
    general = SourceUnit(
        chunk_id="general",
        document_name="rules.pdf",
        category="discipline",
        section="General",
        page_number=2,
        full_chunk_text=general_text,
        text=general_text,
        span=SourceSpan(0, len(general_text)),
        unit_type=UnitType.SENTENCE,
        is_complete=True,
        extraction_method=ExtractionMethod.SENTENCE_SPLIT,
    )
    appeal = SourceUnit(
        chunk_id="appeal",
        document_name="rules.pdf",
        category="discipline",
        section="Appeals",
        page_number=5,
        full_chunk_text=appeal_text,
        text=appeal_text,
        span=SourceSpan(0, len(appeal_text)),
        unit_type=UnitType.SENTENCE,
        is_complete=True,
        extraction_method=ExtractionMethod.SENTENCE_SPLIT,
    )
    selection = select_evidence(
        "written notice",
        score_source_units("written notice", [general, appeal]),
        max_evidence=2,
    )

    assert {item.source_unit.section for item in selection.selected_candidates} == {
        "General",
        "Appeals",
    }


def test_two_different_conditions_both_remain_candidates():
    first = _unit("The penalty is 5 days unless the offence is minor.")
    second = _unit("The penalty is 5 days except for first offences.")
    selection = select_evidence(
        "5 days penalty unless except",
        score_source_units(
            "5 days penalty unless except",
            [first, second],
        ),
        max_evidence=2,
    )

    assert len(selection.selected_candidates) == 2


def test_conflicting_passages_with_similar_wording_are_both_selected():
    shorter = _unit("The maximum suspension period is 30 days.")
    longer = _unit("The maximum suspension period is 60 days.")
    selection = select_evidence(
        "maximum suspension 30 60 days",
        score_source_units(
            "maximum suspension 30 60 days",
            [shorter, longer],
        ),
        max_evidence=2,
    )

    assert len(selection.selected_candidates) == 2


def test_complete_sentence_dependent_on_earlier_paragraph_is_preserved():
    sentence = _unit(
        "The notice must be filed within that period.",
        chunk_id="dependent",
    )
    selection = select_evidence(
        "notice filed period",
        score_source_units("notice filed period", [sentence]),
    )

    assert len(selection.selected_candidates) == 1
    assert selection.selected_candidates[0].source_unit.text == sentence.text


def test_real_discipline_corpus_examples():
    payload = json.loads(
        Path("data/output/discipline-rules.json").read_text(encoding="utf-8")
    )
    by_id = {chunk["chunk_id"]: chunk for chunk in payload["chunks"]}

    ids = (
        "74b85be0218069f0",
        "0320a43289fbdbe8",
        "ff10accb8ee6929c",
        "d75de57ebb19414a",
    )
    chunks = []
    for chunk_id in ids:
        raw = by_id[chunk_id]
        chunks.append(
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
        )

    units = extract_source_units(chunks)
    appeal_units = [
        unit
        for unit in units
        if unit.chunk_id == "74b85be0218069f0"
        and unit.is_complete
    ]
    selection = select_evidence(
        "appeal penalty 5 working days",
        score_source_units("appeal penalty 5 working days", appeal_units),
        max_evidence=2,
    )

    assert selection.selected_candidates
    assert all(
        unit.source_unit.full_chunk_text[
            unit.source_unit.span.start:unit.source_unit.span.end
        ] == unit.source_unit.text
        for unit in selection.selected_candidates
    )
