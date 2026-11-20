import json
from pathlib import Path

import pytest

from campus_help.answer.assembly import assemble_evidence
from campus_help.answer.evidence import score_source_units, select_evidence
from campus_help.answer.models import (
    AnswerStatus,
    AssessmentReadiness,
    ExtractionMethod,
    SourceSpan,
    SourceUnit,
    UnitType,
    ValidationContext,
    ValidationIssueCode,
)
from campus_help.answer.source_units import extract_source_units
from campus_help.answer.sufficiency_pipeline import evaluate_question_evidence
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


def _corpus_chunk(chunk_id: str) -> HybridSearchResult:
    corpus = Path(__file__).resolve().parents[1] / "data/output/discipline-rules.json"
    raw = next(
        row for row in json.loads(corpus.read_text(encoding="utf-8"))["chunks"]
        if row["chunk_id"] == chunk_id
    )
    return _chunk(**raw)


def test_real_appeal_deadline_through_citation_and_context_validation():
    parent = _corpus_chunk("74b85be0218069f0")
    units = extract_source_units([parent])
    deadline, = [unit for unit in units if "5 working days" in unit.text]
    assert deadline.text == (
        "A student having been awarded a penalty for any act(s) of indiscipline or misconduct shall have\n\n"
        "the right to file an appeal (in writing) for review of the decision to the Vice-Chancellor within\n\n"
        "5 working days of the service of the order."
    )
    assert deadline.is_complete and deadline.unit_type is UnitType.SENTENCE
    assert deadline.span == SourceSpan(346, 585)
    assert deadline.text == parent.text[346:585]

    question = "What is the deadline to file an appeal?"
    selected = select_evidence(question, score_source_units(question, units), max_evidence=1)
    draft = assemble_evidence(question, selected)
    context = ValidationContext(question, (parent,), selected, draft)
    assessment = evaluate_question_evidence(question, context=context)
    evidence, = assessment.validation_result.validated_evidence
    assert evidence.is_complete and evidence.quotation.exact_quotation == deadline.text
    citation = evidence.quotation.citation
    assert citation.document_name == parent.document_name
    assert citation.section == parent.section and citation.pdf_page_number == parent.page_number == 5
    assert citation.chunk_id == parent.chunk_id and citation.source_span == deadline.span
    assert ValidationIssueCode.LIKELY_CONTEXT_DEPENDENCY in {
        issue.code for issue in assessment.validation_result.issues
    }
    assert assessment.readiness is AssessmentReadiness.CONTEXT_BLOCKED
    assert assessment.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert not assessment.is_verified and not assessment.is_sufficient


@pytest.mark.parametrize("gap", ["\n", "\n\n", "\r\n \t\r\n"])
def test_visual_wrap_keeps_original_whitespace_and_distinct_occurrences(gap):
    rule = f"A student must{gap}attend the hearing."
    parent = _chunk("repeat", f" \t{rule}\n\n{rule}  ")
    first, second = extract_source_units([parent])
    for unit, start in ((first, 2), (second, 4 + len(rule))):
        assert unit.span == SourceSpan(start, start + len(rule))
        assert unit.text == parent.text[unit.span.start:unit.span.end] == rule
        assert unit.unit_type is UnitType.SENTENCE and unit.is_complete


def test_paragraphs_headings_and_new_items_stop_recovery():
    text = "Students must\n\nAPPEALS\nAppeals must be filed.\n\n1. A student may\n\n2. Students may appeal."
    units = extract_source_units([_chunk("boundaries", text)])
    assert [unit.text for unit in units] == [
        "Students must", "APPEALS", "Appeals must be filed.",
        "1. A student may", "2. Students may appeal.",
    ]
    assert units[1].unit_type is UnitType.HEADING
    assert not units[3].is_complete and units[4].is_complete


def test_wrapped_numbered_item_keeps_its_marker_and_incomplete_successor():
    parent = _chunk("rules", "1. Students shall be\n\nheard in person.\n\n2. A decision must be\n\nissued within")
    complete, incomplete = extract_source_units([parent])
    assert complete.text == "1. Students shall be\n\nheard in person."
    assert incomplete.text == "2. A decision must be\n\nissued within"
    assert complete.unit_type is incomplete.unit_type is UnitType.NUMBERED_ITEM
    assert complete.is_complete and not incomplete.is_complete


@pytest.mark.parametrize("tail", ["5 working days.", "5.", "of the order.", "iv.", "."])
def test_isolated_tails_are_incomplete_even_with_terminal_punctuation(tail):
    unit, = extract_source_units([_chunk("tail", tail)])
    assert unit.text == tail and not unit.is_complete
    assert unit.unit_type is UnitType.CONTINUATION


def test_visual_wrap_cannot_cross_a_chunk_or_supply_missing_text():
    first = _chunk("before", "A student must appeal within")
    second = _chunk("after", "5 working days.")
    units = extract_source_units([first, second])
    assert [(unit.chunk_id, unit.text, unit.is_complete) for unit in units] == [
        (first.chunk_id, first.text, False), (second.chunk_id, second.text, False),
    ]


def test_ambiguous_numeric_row_and_extra_blank_line_do_not_join():
    parent = _chunk("ambiguous", "Students must appeal within\n\n5. Suspension.\n\nStudents may\n\n\nappeal in writing.")
    units = extract_source_units([parent])
    assert [unit.text for unit in units] == [
        "Students must appeal within", "5. Suspension.", "Students may", "appeal in writing.",
    ]
    assert [unit.is_complete for unit in units] == [False, True, False, False]


def test_explicit_table_rows_with_numbers_keep_separate_spans():
    rows = ["Violation | Penalty", "1. Delay | Fine.", "2. Absence | Warning."]
    parent = _chunk("rows", "\n".join(rows))
    units = extract_source_units([parent])
    assert [unit.text for unit in units] == rows
    assert all(unit.unit_type is UnitType.TABLE_ROW and not unit.is_complete for unit in units)


def test_real_penalty_cells_remain_separate_and_incomplete():
    parent = _corpus_chunk("d75de57ebb19414a")
    units = extract_source_units([parent])
    assert [unit.text for unit in units] == parent.text.split("\n\n")
    assert all(not unit.is_complete for unit in units)
    assert [unit.unit_type for unit in units if unit.text.startswith("•")] == [UnitType.TABLE_ROW] * 2


def test_real_missing_item_and_malformed_wording_remain_as_extracted():
    parent = _corpus_chunk("ff10accb8ee6929c")
    assert parent.section.startswith("22.") and parent.text.startswith("23.")
    units = extract_source_units([parent])
    assert all("22." not in unit.text for unit in units)
    assert not next(unit for unit in units if unit.text.startswith("Sodexo staff")).is_complete
    item = next(unit for unit in units if unit.text.startswith("25."))
    assert item.is_complete and item.text == parent.text[parent.text.index("25. "):]

    parent = _corpus_chunk("d8fdccb230b145e7")
    units = extract_source_units([parent])
    malformed = next(unit for unit in units if unit.text.startswith("31."))
    assert malformed.text.startswith("31. Possession, me or distribution at prohibited")
    assert not malformed.is_complete
    assert all(unit.text == parent.text[unit.span.start:unit.span.end] for unit in units)


@pytest.mark.parametrize(("statement", "question"), [
    ("2 signatures are required for an appeal.", "How many signatures are required for an appeal?"),
    ("24 hours must elapse before the committee may meet.", "How many hours must elapse before the committee may meet?"),
    ("written appeals must be filed with the registrar.", "Where must written appeals be filed?"),
    ("3 signed forms are required.", "How many signed forms are required?"),
])
def test_standalone_policy_statement_reaches_validation(statement, question):
    parent = _chunk("standalone", statement)
    units = extract_source_units([parent])
    unit, = units
    assert unit.unit_type is UnitType.SENTENCE and unit.is_complete
    assert unit.extraction_method is ExtractionMethod.SENTENCE_SPLIT
    selected = select_evidence(question, score_source_units(question, units))
    candidate, = selected.selected_candidates
    assert candidate.source_unit == unit
    context = ValidationContext(question, (parent,), selected, assemble_evidence(question, selected))
    assessment = evaluate_question_evidence(question, context=context)
    evidence, = assessment.validation_result.validated_evidence
    citation = evidence.quotation.citation
    assert evidence.is_complete
    assert citation.source_span == unit.span == SourceSpan(0, len(statement))
    assert evidence.quotation.exact_quotation == parent.text[unit.span.start:unit.span.end]
    assert (citation.document_name, citation.pdf_page_number, citation.section, citation.chunk_id) == (
        parent.document_name, parent.page_number, parent.section, parent.chunk_id,
    )
    if statement[0].islower():
        assert evidence.is_context_dependent
        assert ValidationIssueCode.CONTEXT_DEPENDENT_QUOTATION in {
            issue.code for issue in assessment.validation_result.issues
        }
    assert assessment.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert not assessment.is_sufficient and not assessment.is_verified


@pytest.mark.parametrize("fragment", [
    "the University.", "awarded.", "period.", "to be an act of violation of discipline and conduct.",
    "if written appeals must be filed with the registrar.", "2 signatures are required for.",
    "24 hours must elapse before the committee may.", "forms that are required.",
])
def test_whole_chunk_fragment_is_ineligible(fragment):
    unit, = extract_source_units([_chunk("fragment", fragment)])
    assert unit.text == fragment and not unit.is_complete
    assert unit.unit_type is UnitType.CONTINUATION
    assert not select_evidence(fragment, score_source_units(fragment, [unit])).selected_candidates


@pytest.mark.parametrize("parent_text", [
    "A student is exempt unless\n\n2 signatures are required for an appeal.",
    "2 signatures are required for an appeal.\n\nunless the committee grants an exemption.",
])
def test_standalone_pattern_does_not_override_neighboring_context(parent_text):
    units = extract_source_units([_chunk("context", parent_text)])
    candidate, = [unit for unit in units if unit.text.startswith("2 signatures")]
    assert candidate.unit_type is UnitType.CONTINUATION and not candidate.is_complete


@pytest.mark.parametrize(("chunk_id", "page", "start", "end", "kind"), [
    ("de043ef96a8ae1f6", 2, 0, 137, UnitType.NUMBERED_ITEM),
    ("74b85be0218069f0", 5, 346, 585, UnitType.SENTENCE),
    ("067e151abf58a54b", 6, 220, 325, UnitType.NUMBERED_ITEM),
    ("4500b5e1df5458ab", 6, 959, 1163, UnitType.NUMBERED_ITEM),
    ("611b52029bcb3803", 7, 0, 141, UnitType.NUMBERED_ITEM),
    ("ff10accb8ee6929c", 7, 354, 482, UnitType.NUMBERED_ITEM),
    ("d8fdccb230b145e7", 7, 72, 193, UnitType.NUMBERED_ITEM),
])
def test_recovered_policy_span_keeps_exact_citation(chunk_id, page, start, end, kind):
    parent = _corpus_chunk(chunk_id)
    unit, = [unit for unit in extract_source_units([parent]) if unit.span == SourceSpan(start, end)]
    assert unit.is_complete and unit.unit_type is kind
    assert unit.text == parent.text[start:end] and "\n\n" in unit.text
    selected = select_evidence(unit.text, score_source_units(unit.text, [unit]))
    quotation, = assemble_evidence(unit.text, selected).quotations
    assert quotation.exact_quotation == unit.text
    assert quotation.citation.chunk_id == chunk_id
    assert quotation.citation.document_name == parent.document_name
    assert quotation.citation.section == parent.section
    assert quotation.citation.pdf_page_number == page
    assert quotation.citation.source_span == unit.span


def test_saved_hybrid_results_remain_fail_closed_with_extracted_units():
    path = Path(__file__).resolve().parents[1] / "docs/m4-1-retrieval-results.json"
    rows = json.loads(path.read_text(encoding="utf-8"))["methods"]["hybrid"]["query_results"]
    assert len(rows) == 40
    for row in rows:
        question = row["question"]
        parents = tuple(
            HybridSearchResult(**{key: value for key, value in result.items() if key != "rank"})
            for result in row["results"]
        )
        selected = select_evidence(question, score_source_units(question, extract_source_units(parents)))
        context = ValidationContext(question, parents, selected, assemble_evidence(question, selected))
        assessment = evaluate_question_evidence(question, context=context)
        assert assessment.status is AnswerStatus.INSUFFICIENT_EVIDENCE
        assert not assessment.is_verified and not assessment.is_sufficient
