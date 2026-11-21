"""Build reproducible page transcripts; never substitute OCR numbers for native text."""
import argparse
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import subprocess
import re

import pymupdf as fitz
from .table_rows import extract_tables, word_spans


def indexed_tables(page, native):
    tables = extract_tables(page)
    if native or not tables:
        return tables
    # Read each short numerical cell a second time from its image. The OCR
    # layer, the rendered glyphs and the cell coordinates all share one PDF pin.
    _, words = word_spans(page)
    checks = {}
    for table in tables:
        for row in table["rows"]:
            for refs in row:
                if len(refs) != 1:
                    continue
                ref = refs[0]
                if not re.search(r"\d",ref["text"]) or len(ref["text"])>60:
                    continue
                if ref["start"] not in checks:
                    box = fitz.Rect()
                    for start,end,_,coords in words:
                        if ref["start"]<=start and end<=ref["end"]:
                            box |= fitz.Rect(coords)
                    pix = page.get_pixmap(clip=box+(-2,-2,2,2),dpi=300)
                    proc = subprocess.run(["tesseract","stdin","stdout","--psm","7","-l","eng","tsv"],
                                          input=pix.tobytes("png"),capture_output=True,check=True,timeout=60)
                    tokens = [w for w in csv.DictReader(StringIO(proc.stdout.decode()),delimiter="\t",
                              quoting=csv.QUOTE_NONE) if w["level"]=="5" and w["text"].strip()]
                    checks[ref["start"]] = (bool(tokens) and min(float(w["conf"]) for w in tokens)>=80
                        and " ".join(w["text"] for w in tokens) == " ".join(ref["text"].split()))
                ref["image_agrees"] = checks[ref["start"]]
    return tables


def words_to_blocks(tsv, scale):
    groups = {}
    for row in csv.DictReader(StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        if row["level"] != "5" or not row["text"].strip():
            continue
        key = (row["block_num"], row["par_num"])
        groups.setdefault(key, []).append(row)
    for words in groups.values():
        lines = {}
        for w in words:
            lines.setdefault(w["line_num"], []).append(w["text"])
        text = "\n".join(" ".join(line) for line in lines.values())
        x = min(int(w["left"]) for w in words)
        y = min(int(w["top"]) for w in words)
        right = max(int(w["left"])+int(w["width"]) for w in words)
        bottom = max(int(w["top"])+int(w["height"]) for w in words)
        yield text, [round(v/scale, 2) for v in (x,y,right,bottom)], min(float(w["conf"]) for w in words)


def build(pdf, category):
    data = pdf.read_bytes()
    pdf_hash = sha256(data).hexdigest()
    pages, chunks = [], []
    with fitz.open(stream=data,filetype="pdf") as doc:
        for page in doc:
            native = bool(page.get_text().strip()) and any(
                span["type"] != 3 for span in page.get_texttrace()
            )
            if native:
                blocks = [(b[4].strip(), list(b[:4]), 100) for b in page.get_text("blocks") if b[6]==0]
            else:
                pix = page.get_pixmap(dpi=300, alpha=False)
                proc = subprocess.run(["tesseract","stdin","stdout","--dpi","300","-l","eng","tsv"],
                                      input=pix.tobytes("png"),capture_output=True,check=True,timeout=180)
                blocks = words_to_blocks(proc.stdout.decode(), 300/72)
            transcript = ""
            regions = []
            for text, bbox, confidence in blocks:
                if not text.strip():
                    continue
                if transcript:
                    transcript += "\n\n"
                start = len(transcript)
                transcript += text
                chunk_id = f"{pdf_hash[:16]}-p{page.number+1}-{start}"
                chunks.append(dict(chunk_id=chunk_id,document_name=pdf.name,section="Page transcript",
                                   page_number=page.number+1,text=text,category=category))
                regions.append(dict(start=start,end=len(transcript),chunk_id=chunk_id,bbox=bbox,
                                    confidence=confidence,low_confidence=confidence<80))
            if not regions:
                raise ValueError(f"No readable text on page {page.number+1}")
            pages.append(dict(page=page.number+1,method="native" if native else "ocr",
                              text=transcript,regions=regions,tables=indexed_tables(page,native)))
    return dict(document_name=pdf.name,category=category,pdf_sha256=pdf_hash,pages=pages,chunks=chunks)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--category", required=True)
    args=parser.parse_args()
    output=json.dumps(build(args.pdf,args.category),ensure_ascii=False,indent=2)+"\n"
    args.output.write_text(output)


if __name__ == "__main__":
    main()
