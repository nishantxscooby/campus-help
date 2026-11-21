"""Locate table evidence by closed cell boundaries in the rendered PDF."""

import re

import numpy as np
import pymupdf as fitz
from scipy import ndimage


def _boxes(page):
    scale = 2
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csGRAY)
    pixels = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)
    white = ~ndimage.binary_dilation(pixels < 170)
    labels, _ = ndimage.label(white)
    sizes = np.bincount(labels.ravel())
    cells = []
    slopes = []
    for label, (ys, xs) in enumerate(ndimage.find_objects(labels), 1):
        w, h = xs.stop - xs.start, ys.stop - ys.start
        if (
            w < 30
            or h < 13
            or w >= pix.w * 0.98
            or h >= pix.h * 0.9
            or sizes[label] < 0.45 * w * h
            or xs.start == 0
            or ys.start == 0
        ):
            continue
        interior = labels[ys, xs] == label
        if w > 160 and w > 2 * h:
            columns = np.arange(w // 8, 7 * w // 8)
            heights = interior[:, columns].argmax(axis=0)
            slopes.append(float(np.polyfit(columns, heights, 1)[0]))
        cells.append((xs, ys, interior))
    slope = float(np.median(slopes)) if slopes else 0.0
    for xs, ys, interior in cells:
        y, x = np.nonzero(interior)
        x, y = (x + xs.start) / scale, (y + ys.start) / scale
        # Align measurement axes with the scan. Citations retain original PDF axes.
        u, v = x + slope * y, y - slope * x
        yield dict(
            box=(float(u.min()), float(v.min()), float(u.max()), float(v.max())),
            bbox=[xs.start / scale, ys.start / scale, xs.stop / scale, ys.stop / scale],
            slope=slope,
        )


def word_spans(page):
    raw = page.get_text()
    words = []
    offset = 0
    for x, y, r, b, token, *_ in page.get_text("words"):
        start = raw.find(token, offset)
        if start < 0 or raw[offset:start].strip():
            return raw, []  # unmappable reading order
        offset = start + len(token)
        words.append((start, offset, [(x + r) / 2, (y + b) / 2], [x, y, r, b]))
    return raw, words


def _references(cell, words, raw):
    left, top, right, bottom = cell["box"]
    refs = []
    for start, end, (x, y), _ in words:
        u, v = x + cell["slope"] * y, y - cell["slope"] * x
        if not (left <= u <= right and top <= v <= bottom):
            continue
        if refs and not raw[refs[-1]["end"] : start].strip():
            refs[-1]["end"] = end
            refs[-1]["text"] = raw[refs[-1]["start"] : end]
        else:
            refs.append(dict(start=start, end=end, text=raw[start:end], bbox=cell["bbox"]))
    return refs


HEADER = re.compile(
    r"\b(program(?:me)?|name|CGPA|description|fee|amount|eligibility|requirement|deadline|unit|"
    r"offen[cs]e|penalty|penalties|remarks|particulars|attendance|duration|date|category|rate|conduct)\b",
    re.I,
)


def extract_tables(page):
    raw, words = word_spans(page)
    if not words:
        return []
    cells = list(_boxes(page))
    for cell in cells:
        cell["refs"] = _references(cell, words, raw)

    def right_of(cell):
        l, t, r, b = cell["box"]
        return [
            c
            for c in cells
            if abs(c["box"][0] - r) < 3.5 and c["box"][1] <= t + 2 and c["box"][3] >= b - 2
        ]

    def below(cell):
        l, t, r, b = cell["box"]
        return [
            c
            for c in cells
            if abs(c["box"][0] - l) < 3 and abs(c["box"][2] - r) < 3 and abs(c["box"][1] - b) < 3.5
        ]

    tables = []
    for first in cells:
        left, top, _, bottom = first["box"]
        if any(
            abs(c["box"][2] - left) < 3.5 and min(c["box"][3], bottom) - max(c["box"][1], top) > 4
            for c in cells
        ):
            continue  # A subcolumn cannot serve as the subject of the entire row.
        headers = [first]
        while len(right := right_of(headers[-1])) == 1:
            nxt = right[0]
            if abs(nxt["box"][1] - first["box"][1]) > 2 or abs(nxt["box"][3] - first["box"][3]) > 2:
                break
            headers.append(nxt)
        if len(headers) < 2 or not all(c["refs"] for c in headers):
            continue
        names = [" ".join(ref["text"] for ref in c["refs"]) for c in headers]
        if (
            not all(len(name) < 100 for name in names)
            or not HEADER.search(names[0])
            or not any(HEADER.search(n) for n in names[1:])
        ):
            continue
        rows = []
        left_cell = first
        while len(children := below(left_cell)) == 1:
            left_cell = children[0]
            row = [left_cell]
            for header in headers[1:]:
                # Use the original row's vertical interval even past a merged cell.
                last = dict(box=(0, left_cell["box"][1], row[-1]["box"][2], left_cell["box"][3]))
                east = right_of(last)
                if len(east) != 1 or abs(east[0]["box"][2] - header["box"][2]) > 3:
                    break
                row.append(east[0])
            if len(row) != len(headers) or not all(c["refs"] for c in row):
                break
            rows.append([c["refs"] for c in row])
        if rows:
            start = min(c["refs"][0]["start"] for c in headers)
            end = max(ref["end"] for row in rows for cell in row for ref in cell)
            lines = list(re.finditer(r"[^\n]+", raw[:start]))
            headings = [line for line in lines if len(line[0]) > 12 and line[0].isupper()]
            section = headings[-1] if headings else None

            def interval(match):
                boxes = [
                    fitz.Rect(box) for s, e, _, box in words if match.start() <= s and e <= match.end()
                ]
                rect = fitz.Rect()
                for box in boxes:
                    rect |= box
                return dict(start=match.start(), end=match.end(), text=match[0], bbox=list(rect))

            notes = []
            context = []
            if section:
                # Keep the intervening source, including qualifications and duplicated
                # clauses in the PDF. Nothing outside this section is inherited.
                begin = section.end() + 1
                for line in lines:
                    if line.start() < begin:
                        continue
                    if line[0].rstrip().endswith((".", ":")) or line == lines[-1]:
                        text = raw[begin : line.end()]
                        rect = fitz.Rect()
                        for s, e, _, box in words:
                            if begin <= s and e <= line.end():
                                rect |= fitz.Rect(box)
                        if text.strip():
                            context.append(
                                dict(start=begin, end=line.end(), text=text, bbox=list(rect))
                            )
                        begin = line.end() + 1
            for line in re.compile(r"[^\n]+").finditer(raw, end):
                if not re.match(r"^\s*(?:\*|†|notes?\b|footnote\b)", line[0], re.I):
                    break
                notes.append(interval(line))
            tables.append(
                dict(
                    headers=[c["refs"] for c in headers],
                    rows=rows,
                    section=interval(section) if section else None,
                    context=context,
                    notes=notes,
                )
            )
    return tables


def tiered_rows(page, grids):
    """Bind native subheaders to data cells only within the same printed table."""
    raw, words = word_spans(page)
    if not words:
        return []
    result = []
    for grid in grids:
        for index, upper in enumerate(grid[:-2]):
            lower = grid[index + 1]
            # A grouped heading spans multiple subcolumns. The row label spans
            # both header tiers, so the cell below it must be empty in the grid.
            if not upper[0] or lower[0] or sum(bool(c) for c in lower) < 2:
                continue
            header_cells = [c for c in upper + lower if c]
            data = grid[index + 2 :]
            first = data[0]
            if not all(first) or not HEADER.search(" ".join(c[1] for c in header_cells)):
                continue

            def refs(cell):
                box, text = cell
                evidence = _references(dict(box=box, bbox=list(box), slope=0), words, raw)
                actual = "".join(r["text"] for r in evidence)
                if "".join(actual.split()) != "".join(text.split()):
                    return None
                return evidence

            headers = []
            for col in first:
                x0, _, x1, _ = col[0]
                headings = [refs(c) for c in header_cells if c[0][0] <= x0 + 1 and c[0][2] >= x1 - 1]
                if not headings or not all(headings):
                    break
                headers.append([r for h in headings for r in h])
            if len(headers) != len(first):
                continue
            subject = 1 if re.fullmatch(r"(?:sr\.?\s*)?no\.?", upper[0][1].strip(), re.I) else 0
            rows = []
            for row in data:
                if not all(row):
                    break
                boxes = [c[0] for c in row]
                if any(abs(c[1] - boxes[0][1]) > 1 or abs(c[3] - boxes[0][3]) > 1 for c in boxes):
                    break
                cells = [refs(c) for c in row]
                if any(c is None for c in cells) or not cells[subject]:
                    break
                rows.append(cells)
            if rows:
                result.append(
                    dict(
                        headers=headers,
                        subject=subject,
                        row_start=index + 3,
                        rows=rows,
                        section=None,
                        context=[],
                        notes=[],
                    )
                )
            break
    return result
