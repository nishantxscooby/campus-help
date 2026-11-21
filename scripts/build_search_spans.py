"""Build source-checked search artifacts before serving traffic."""

import argparse
from dataclasses import fields
import gzip
from hashlib import sha256
import io
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from campus_help.web.library import geometry_digest, inventory, source_tables
from campus_help.web.search import Slice, extract_spans, validate_slices
from campus_help.web.service import bundled_corpus, pinned_bytes
from campus_help.web.span_store import FORMAT, source_key

ROOT = Path(__file__).resolve().parents[1]


def atomic_write(path, data):
    with NamedTemporaryFile(dir=path.parent, delete=False) as output:
        tmp = Path(output.name)
    try:
        tmp.write_bytes(data)
        tmp.chmod(0o644)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def build(data_dir, library, output):
    # No prepared artifacts are consulted during generation. inventory()
    # reconstructs and verifies scholarship table geometry against the PDF.
    books = inventory(bundled_corpus(data_dir), "Students’ Discipline and Conduct Rules", library)
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for book in books:
        if book.unavailable:
            raise ValueError(f"Cannot prepare {book.title}: {book.unavailable}")
        spans = extract_spans(book)
        if not spans:
            raise ValueError(f"No searchable spans for {book.title}")
        validate_slices(book, spans)
        records = [
            {f.name: getattr(s, f.name) for f in fields(Slice) if f.name != "book"} for s in spans
        ]
        identity = source_key(book.source)
        payload = dict(format=FORMAT, source=identity, spans=records)
        if book.layout:
            pdf = pinned_bytes(book.source.pdf_path, book.source.document.pdf_sha256)
            layout = json.loads(pinned_bytes(book.source.corpus_path, book.source.corpus_revision))
            payload["layout_geometry"] = {
                str(page["page"]): geometry_digest(source_tables(pdf, page["page"]))
                for page in layout["pages"]
                if page.get("tables")
            }
        raw = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as stream:
            stream.write(raw.encode())
        data = buf.getvalue()
        digest = sha256(data).hexdigest()
        filename = f"{digest}.json.gz"
        atomic_write(output / filename, data)
        entries.append(dict(**identity, file=filename, sha256=digest))
        print(f"{book.title}: {len(spans)} spans, {len(data)} bytes, {digest}")
    atomic_write(
        output / "manifest.json",
        (json.dumps(dict(format=FORMAT, documents=entries), indent=2) + "\n").encode(),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--library", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build(
        args.data_dir,
        args.library or args.data_dir / "library.json",
        args.output or args.data_dir / "search-spans",
    )


if __name__ == "__main__":
    main()
