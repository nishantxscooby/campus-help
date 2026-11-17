"""Command-line demonstration for BM25 search."""

import argparse
import logging

from .engine import BM25Retriever
from .loader import load_chunks


def main() -> int:
    parser = argparse.ArgumentParser(description="Search processed Campus Help chunks")
    parser.add_argument("--input", required=True, help="Milestone 1 JSON file")
    parser.add_argument("--query", required=True, help="Student question or keywords")
    parser.add_argument("--top-k", type=int, default=5, dest="top_k")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        retriever = BM25Retriever(load_chunks(args.input))
        results = retriever.search(args.query, top_k=args.top_k)
    except (OSError, ValueError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1

    if not results:
        print("No matching chunks found.")
        return 0
    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. [{result.score:.3f}] {result.document_name} | "
            f"{result.section} | page {result.page_number} | {result.category}\n"
            f"   {result.text}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
