"""Searchable row descriptors and exact, separate PDF witness intervals."""

from dataclasses import replace


def text_of(refs):
    return " ".join(" ".join(ref["text"].split()) for ref in refs)


def descriptors(tables, scanned):
    for table in tables:
        headers = [text_of(refs) for refs in table["headers"]]
        for number, cells in enumerate(table["rows"], table.get("row_start", 2)):
            yield dict(
                row=number,
                column=table.get("subject", 0) + 1,
                headers=headers,
                header_cells=table["headers"],
                cells=cells,
                section_source=table["section"],
                context=table["context"],
                notes=table["notes"],
                scanned=scanned,
            )


def search_text(span):
    row = span.table or {}
    if "cells" not in row:
        return span.text
    return " ".join([span.heading, *row["headers"], *(text_of(c) for c in row["cells"])])


def witnesses(span):
    row = span.table or {}
    if "cells" not in row:
        return [span]
    subject = row["column"] - 1
    refs = [
        *row["cells"][subject],
        *(r for i, cell in enumerate(row["cells"]) if i != subject for r in cell),
    ]
    refs.extend(r for header in row["header_cells"] for r in header)
    if row["section_source"]:
        refs.append(row["section_source"])
    refs.extend(row["context"])
    refs.extend(row["notes"])
    return [
        replace(
            span,
            start=r["start"],
            end=r["end"],
            text=r["text"],
            bbox=tuple(r["bbox"]),
            table=(
                {
                    "row": row["row"],
                    "column": row["column"],
                    "headers": row["headers"],
                    "values": [text_of(cell) for cell in row["cells"]],
                }
                if i == 0
                else None
            ),
        )
        for i, r in enumerate(refs)
    ]


def citations(spans):
    seen = set()
    result = []
    for span in spans:
        for witness in witnesses(span):
            key = (witness.book.url, witness.page, witness.coordinates, witness.start, witness.end)
            if key not in seen:
                result.append(witness.citation())
                seen.add(key)
    return result
