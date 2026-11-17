"""Command-line demonstration for local semantic search."""

import argparse
import logging
from pathlib import Path

from ..retrieval.loader import load_chunks
from .engine import SemanticRetriever
from .model import MODEL_NAME, load_model


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Campus Help chunks semantically")
    parser.add_argument("--input", required=True, help="Milestone 1 processed JSON file")
    parser.add_argument("--embeddings", required=True, help="Local NPZ embedding index")
    parser.add_argument("--query", required=True, help="Student question")
    parser.add_argument("--top-k", type=int, default=5, dest="top_k")
    parser.add_argument("--model", default=MODEL_NAME, help="Sentence-transformer model name")
    parser.add_argument(
        "--download-model",
        action="store_true",
        help="Allow downloading the model if it is not already cached",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        model = load_model(args.model, local_files_only=not args.download_model)
        index_path = Path(args.embeddings)
        if index_path.is_file():
            retriever = SemanticRetriever.from_index(model, str(index_path))
        else:
            retriever = SemanticRetriever.from_chunks(model, load_chunks(args.input))
            retriever.save(str(index_path))
        results = retriever.search(args.query, top_k=args.top_k)
    except (OSError, ValueError, RuntimeError) as exc:
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
