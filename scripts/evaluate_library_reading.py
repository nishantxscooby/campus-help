"""Report fixed page/word judgments separately from provenance and claim status."""
import argparse
import json
from hashlib import sha256
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from campus_help.web.api import create_app

ROOT = Path(__file__).resolve().parents[1]


def main():
    client = TestClient(create_app())
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=ROOT / "data/evaluation/library-held-out.json")
    cases = json.loads(parser.parse_args().cases.read_text())
    manifest = ROOT / "data/library.json"
    transcripts = {}
    for entry in json.loads(manifest.read_text()):
        if entry.get("layout"):
            artifact = (manifest.parent / entry["corpus"]).read_bytes()
            if sha256(artifact).hexdigest() != entry["corpus_sha256"]:
                raise ValueError("Unexpected page transcript version")
            transcripts[entry["pdf_sha256"]] = json.loads(artifact)["pages"]
    totals = dict(questions=len(cases), top_one=0, covered=0, excerpts=0, relevant=0, exact=0, confirmed=0)
    for case in cases:
        response = client.post("/ask", json={"question": case["question"]})
        response.raise_for_status()
        body = response.json()
        totals["confirmed"] += body["status"] == "answered"
        results = []
        for item in body["excerpts"]:
            page = item["pdf_page_number"]
            pdf = client.get(item["pdf_url"]).content
            with fitz.open(stream=pdf, filetype="pdf") as doc:
                text = doc[page-1].get_text()
                if item["coordinates"] in ("ocr_transcript", "layout_transcript"):
                    text = transcripts[sha256(pdf).hexdigest()][page-1]["text"]
                totals["exact"] += text[item["start"]:item["end"]] == item["exact_quotation"]
            passage = " ".join(item["exact_quotation"].casefold().split())
            relevant = (page in case["pages"] and all(word in passage for word in case["terms"])
                        and item["title"] == case.get("document", "Students’ Discipline and Conduct Rules"))
            results.append(relevant)
        totals["excerpts"] += len(results)
        totals["relevant"] += sum(results)
        totals["covered"] += any(results)
        totals["top_one"] += bool(results and results[0])
        print(case["question"], body["retrieval_mode"], results)
    print(json.dumps(totals))


if __name__ == "__main__":
    main()
