"""Read ruled grid coordinates. Retain ambiguous/merged cells without carrying labels across pages."""
import re

import pymupdf as fitz


def grid(page):
    if not page.get_drawings():
        return []
    result = []
    for table in page.find_tables(strategy="lines_strict").tables:
        if table.col_count < 2 or table.row_count < 2:
            continue
        # Read text clipped from each original cell; keep missing cells explicit.
        rows = []
        for row in table.rows:
            cells = []
            for box in row.cells:
                cells.append(None if box is None else (box, page.get_textbox(fitz.Rect(box)).strip()))
            rows.append(cells)
        result.append(rows)
    return result


def cell_position(grids, box):
    block = fitz.Rect(box)
    if not block.get_area():
        return None
    for rows in grids:
        for ri,row in enumerate(rows):
            for ci,cell in enumerate(row):
                if not cell or (fitz.Rect(cell[0]) & block).get_area()/block.get_area() < .95:
                    continue
                # A same-page header may be used only directly above this column,
                # with matching x bounds. Never pair a penalty with another cell by proximity.
                headers = []
                for prior in rows[:ri]:
                    candidate = prior[ci]
                    if not candidate or not candidate[1]:
                        continue
                    if (abs(candidate[0][0]-cell[0][0]) < 2 and abs(candidate[0][2]-cell[0][2]) < 2
                            and re.fullmatch(r"(?:[IVX]+\s+offen[cs]e|Remarks|Acts of Indiscipline)",
                                             " ".join(candidate[1].split()),re.I)):
                        headers.append(" ".join(candidate[1].split()))
                return {"row":ri+1,"column":ci+1,"bbox":list(cell[0]),"headers":headers}
    return None
