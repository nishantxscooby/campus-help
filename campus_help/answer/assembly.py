"""Mechanical assembly and citation formatting for extracted evidence."""

from __future__ import annotations

from .models import (
    EvidenceCitation,
    EvidenceSelection,
    ExtractiveDraft,
    QuotedEvidence,
    SourceUnit,
)


class AssemblyValidationError(ValueError):
    """Raised when a selected source unit cannot be cited without alteration."""


def _validate_source_unit(unit: SourceUnit) -> None:
    if not isinstance(unit.document_name, str) or not unit.document_name.strip():
        raise AssemblyValidationError(
            f"Invalid document_name for chunk {unit.chunk_id!r}"
        )
    if not isinstance(unit.section, str) or not unit.section.strip():
        raise AssemblyValidationError(
            f"Invalid section for chunk {unit.chunk_id!r}"
        )
    if not isinstance(unit.chunk_id, str) or not unit.chunk_id.strip():
        raise AssemblyValidationError("Invalid empty chunk_id")
    if (
        isinstance(unit.page_number, bool)
        or not isinstance(unit.page_number, int)
        or unit.page_number < 1
    ):
        raise AssemblyValidationError(
            f"Invalid PDF page number for chunk {unit.chunk_id!r}"
        )

    start = unit.span.start
    end = unit.span.end
    if isinstance(start, bool) or isinstance(end, bool):
        raise AssemblyValidationError(
            f"Invalid boolean source span for chunk {unit.chunk_id!r}"
        )
    if not isinstance(start, int) or not isinstance(end, int):
        raise AssemblyValidationError(
            f"Invalid non-integer source span for chunk {unit.chunk_id!r}"
        )
    if start < 0 or end < start:
        raise AssemblyValidationError(
            f"Invalid source span [{start}, {end}) for chunk {unit.chunk_id!r}"
        )
    if end > len(unit.full_chunk_text):
        raise AssemblyValidationError(
            f"Source span [{start}, {end}) is outside chunk {unit.chunk_id!r}"
        )

    try:
        quoted_text = unit.full_chunk_text[start:end]
    except (IndexError, TypeError) as exc:
        raise AssemblyValidationError(
            f"Cannot read source span for chunk {unit.chunk_id!r}"
        ) from exc
    if quoted_text != unit.text:
        raise AssemblyValidationError(
            f"Quotation does not match source span for chunk {unit.chunk_id!r}"
        )
    if not isinstance(unit.text, str):
        raise AssemblyValidationError(
            f"Invalid quotation type for chunk {unit.chunk_id!r}"
        )
    if not unit.text:
        raise AssemblyValidationError(
            f"Empty quotation is invalid for chunk {unit.chunk_id!r}"
        )


def assemble_evidence(
    question: str,
    selection: EvidenceSelection,
) -> ExtractiveDraft:
    """Project selected candidates into exact quotations and machine citations."""
    quotations: list[QuotedEvidence] = []

    for scored in selection.selected_candidates:
        unit = scored.source_unit
        _validate_source_unit(unit)
        citation = EvidenceCitation(
            document_name=unit.document_name,
            section=unit.section,
            pdf_page_number=unit.page_number,
            chunk_id=unit.chunk_id,
            source_span=unit.span,
        )
        quotations.append(
            QuotedEvidence(
                exact_quotation=unit.text,
                citation=citation,
            )
        )

    return ExtractiveDraft(
        question=question,
        quotations=tuple(quotations),
    )


def format_citation(citation: EvidenceCitation) -> str:
    """Return a deterministic human-readable citation."""
    return (
        f"Document: {citation.document_name}\n"
        f"PDF Page: {citation.pdf_page_number}\n"
        f"Section: {citation.section}\n"
        f"Chunk ID: {citation.chunk_id}"
    )
