"""Immutable search spans prepared from the operator's pinned PDFs and corpora."""

from dataclasses import dataclass
import gzip
import json
from pathlib import Path

from .service import SourceUnavailable, pinned_bytes

FORMAT = "campus-help-search-spans-v1"


@dataclass(frozen=True)
class SpanArtifact:
    path: Path
    sha256: str


def source_key(source):
    return dict(
        document=source.document.document_name,
        pdf_sha256=source.document.pdf_sha256,
        corpus_sha256=source.corpus_revision,
    )


def read_manifest(path):
    data = json.loads(path.read_text())
    if data.get("format") != FORMAT:
        raise ValueError("Unsupported search span manifest")
    entries = {row["document"]: row for row in data["documents"]}
    if len(entries) != len(data["documents"]):
        raise ValueError("Duplicate document in search span manifest")
    return entries


def artifact_for(source, entries, directory, required):
    entry = entries.get(source.document.document_name)
    if entry is None and not required:
        return None
    if not entry or any(entry.get(k) != v for k, v in source_key(source).items()):
        raise SourceUnavailable("No search index for this source revision")
    return SpanArtifact(directory / entry["file"], entry["sha256"])


def unpack(source, artifact):
    data = pinned_bytes(artifact.path, artifact.sha256)
    try:
        payload = json.loads(gzip.decompress(data))
        if payload["format"] != FORMAT or payload["source"] != source_key(source):
            raise ValueError("Wrong search span revision")
        return payload
    except (KeyError, OSError, EOFError, TypeError, ValueError) as exc:
        raise SourceUnavailable("Invalid search span artifact") from exc
