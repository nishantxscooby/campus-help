"""Measure one cold BM25 request per fresh process. Run with python -m scripts.profile_bm25."""

import json
import os
import resource
import sys
from time import perf_counter


def peak_mib():
    scale = 1024**2 if sys.platform == "darwin" else 1024
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale, 2)


def main():
    os.environ["CAMPUS_HELP_SEARCH_MODE"] = "bm25"
    from fastapi.testclient import TestClient

    start = perf_counter()
    from campus_help.web.api import app

    with TestClient(app) as client:
        client.get("/health").raise_for_status()
        ready = perf_counter()
        ready_peak = peak_mib()
        reply = client.post("/ask", json={"question": "Can I smoke around the campus?"})
        reply.raise_for_status()
        end = perf_counter()
        body = reply.json()
        print(
            json.dumps(
                dict(
                    startup_seconds=round(ready - start, 4),
                    ready_peak_mib=ready_peak,
                    first_ask_seconds=round(end - ready, 4),
                    peak_mib=peak_mib(),
                    mode=body["retrieval_mode"],
                    status=body["status"],
                    pages=[s["pdf_page_number"] for s in body["excerpts"]],
                    imported=[
                        m
                        for m in (
                            "torch",
                            "sentence_transformers",
                            "scipy",
                            "onnxruntime",
                            "numpy",
                            "pymupdf.table",
                        )
                        if m in sys.modules
                    ],
                )
            )
        )


if __name__ == "__main__":
    main()
