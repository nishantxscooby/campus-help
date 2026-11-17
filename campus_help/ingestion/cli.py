"""Command-line interface for PDF ingestion."""

import argparse
import logging

from .pipeline import write_chunks_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract and chunk a Campus Help PDF")
    parser.add_argument("--input", required=True, help="Path to the source PDF")
    parser.add_argument("--output", required=True, help="Path for generated JSON")
    parser.add_argument("--category", required=True, help="Document category")
    parser.add_argument("--max-chars", type=int, default=1200)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        write_chunks_json(args.input, args.output, args.category, args.max_chars)
    except (OSError, ValueError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
