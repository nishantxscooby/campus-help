"""Operator-owned document inventory. Only pinned, indexed versions enter search."""

from dataclasses import dataclass
from functools import lru_cache
import json
from hashlib import sha256
from pathlib import Path

from ..answer.verification import _canonical_chunks
from .service import SourceUnavailable, pinned_bytes
import pymupdf as fitz
from .span_store import SpanArtifact, artifact_for, read_manifest, unpack
from ..answer.verification_contracts import ApprovedCorpus, DocumentVersion


@dataclass(frozen=True)
class Book:
    title: str
    source: ApprovedCorpus
    url: str
    version: str
    layout: bool = False
    unavailable: str = ""
    artifact: SpanArtifact | None = None

    def check_files(self):
        pinned_bytes(self.source.pdf_path,self.source.document.pdf_sha256)
        pinned_bytes(self.source.corpus_path,self.source.corpus_revision)
        if self.artifact:
            pinned_bytes(self.artifact.path,self.artifact.sha256)


def inventory(source, title, manifest=None, *, span_manifest=None, require_indexes=False):
    entries = read_manifest(span_manifest) if span_manifest else {}
    directory = span_manifest.parent if span_manifest else None
    primary_index = artifact_for(source, entries, directory, require_indexes)
    books = [Book(title, source, "/documents/handbook/pdf", source.document.pdf_sha256[:12],
                  artifact=primary_index)]
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
            artifact = None
            try:
                artifact = artifact_for(config, entries, directory, require_indexes)
                pdf_data = pinned_bytes(config.pdf_path, config.document.pdf_sha256)
                chunks = _canonical_chunks(config)
                if not chunks:
                    raise ValueError("Empty index")
                if row.get("layout"):
                    certificate = None
                    if artifact:
                        payload = unpack(config, artifact)
                        certificate = payload["layout_geometry"]
                        if not isinstance(certificate, dict):
                            raise ValueError("Missing PDF table geometry certificate")
                    validate_layout(config, pdf_data, chunks, certificate=certificate)
            except (OSError, ValueError, RuntimeError, SourceUnavailable, KeyError, IndexError, TypeError):
                unavailable = "The document or its page index could not be validated."
            books.append(Book(row["title"], config, f'/documents/{row["pdf_sha256"]}/pdf',
                              row["version"], row.get("layout", False), unavailable, artifact))
    return tuple(books)

@lru_cache(maxsize=8)
def source_tables(pdf_data, number):
    from ..ingestion.table_rows import extract_tables
    with fitz.open(stream=pdf_data,filetype="pdf") as pdf:
        return extract_tables(pdf[number-1])


def geometry_digest(tables):
    canonical = json.dumps(tables, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return sha256(canonical.encode()).hexdigest()


def validate_layout(config, pdf_data, chunks, *, certificate=None):
    data = json.loads(pinned_bytes(config.corpus_path, config.corpus_revision))
    if data["pdf_sha256"] != config.document.pdf_sha256:
        raise ValueError("Transcript belongs to another PDF")
    with fitz.open(stream=pdf_data,filetype="pdf") as pdf:
        if len(data["pages"]) != len(pdf):
            raise ValueError("Incomplete page index")
        seen = set()
        geometry_pins = {}
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
                if certificate is None and geometry != source_tables(pdf_data,number):
                    raise ValueError("Table witnesses differ from source geometry")
                geometry_pins[str(number)] = geometry_digest(geometry)
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
        if certificate is not None and geometry_pins != certificate:
            raise ValueError("Layout differs from the PDF-derived geometry certificate")
