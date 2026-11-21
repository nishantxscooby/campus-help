"""Operator-owned document inventory. Only pinned, indexed versions enter search."""

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

from ..answer.verification import _canonical_chunks
from .service import SourceUnavailable, pinned_bytes
import pymupdf as fitz
from ..ingestion.table_rows import extract_tables
from ..answer.verification_contracts import ApprovedCorpus, DocumentVersion


@dataclass(frozen=True)
class Book:
    title: str
    source: ApprovedCorpus
    url: str
    version: str
    layout: bool = False
    unavailable: str = ""


def inventory(source, title, manifest=None):
    books = [Book(title, source, "/documents/handbook/pdf", source.document.pdf_sha256[:12])]
    if manifest:
        path = Path(manifest)
        for row in json.loads(path.read_text()):
            pdf = path.parent / row["pdf"]
            config = ApprovedCorpus(DocumentVersion(pdf.name, row["pdf_sha256"]), pdf,
                                    path.parent / row["corpus"], row["corpus_sha256"], "unreviewed")
            if any(b.source.document == config.document or b.source.document.pdf_sha256 == row["pdf_sha256"]
                   for b in books):
                raise ValueError("Duplicate document in library")
            unavailable = ""
            try:
                pdf_data = pinned_bytes(config.pdf_path, config.document.pdf_sha256)
                chunks = _canonical_chunks(config)
                if not chunks:
                    raise ValueError("Empty index")
                if row.get("layout"):
                    validate_layout(config, pdf_data, chunks)
            except (OSError, ValueError, RuntimeError, SourceUnavailable, KeyError, IndexError, TypeError):
                unavailable = "The document or its page index could not be validated."
            books.append(Book(row["title"], config, f'/documents/{row["pdf_sha256"]}/pdf',
                              row["version"], row.get("layout", False), unavailable))
    return tuple(books)

@lru_cache(maxsize=8)
def source_tables(pdf_data, number):
    with fitz.open(stream=pdf_data,filetype="pdf") as pdf:
        return extract_tables(pdf[number-1])


def validate_layout(config, pdf_data, chunks):
    data = json.loads(pinned_bytes(config.corpus_path, config.corpus_revision))
    if data["pdf_sha256"] != config.document.pdf_sha256:
        raise ValueError("Transcript belongs to another PDF")
    with fitz.open(stream=pdf_data,filetype="pdf") as pdf:
        if len(data["pages"]) != len(pdf):
            raise ValueError("Incomplete page index")
        seen = set()
        for number, entry in enumerate(data["pages"],1):
            if entry["page"] != number or entry["method"] not in {"ocr","native"} or not entry["regions"]:
                raise ValueError("Invalid transcript page")
            if entry.get("tables"):
                # Re-derive row membership from the pinned PDF. The image OCR
                # cross-check itself belongs to the digest-bound ingestion artifact.
                geometry = json.loads(json.dumps(entry["tables"]))
                for table in geometry:
                    for row in table["rows"]:
                        for cell in row:
                            for ref in cell:
                                ref.pop("image_agrees",None)
                if geometry != source_tables(pdf_data,number):
                    raise ValueError("Table witnesses differ from source geometry")
            last = 0
            for region in entry["regions"]:
                chunk = chunks[region["chunk_id"]]
                start,end = region["start"],region["end"]
                rect = fitz.Rect(region["bbox"])
                bounds = pdf[number-1].rect + (-.1, -.1, .1, .1)
                confidence = region["confidence"]
                if (chunk.chunk_id in seen or chunk.page_number != number or not last <= start < end <= len(entry["text"])
                        or chunk.text != entry["text"][start:end] or rect.is_empty
                        or not bounds.contains(rect) or not 0 <= confidence <= 100
                        or region["low_confidence"] is not (confidence < 80)):
                    raise ValueError("Invalid transcript region")
                last = end
                seen.add(chunk.chunk_id)
        if seen != set(chunks):
            raise ValueError("Unlocated transcript chunk")
