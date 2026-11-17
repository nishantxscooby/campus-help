"""Command-line demonstration for hybrid retrieval."""

import argparse
import logging

from ..retrieval.engine import BM25Retriever
from ..retrieval.loader import load_chunks
from ..semantic.engine import SemanticRetriever
from ..semantic.model import MODEL_NAME, load_model
from .engine import HybridRetriever


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid Campus Help search with RRF")
    parser.add_argument("--input", required=True, help="Milestone 1 processed JSON file")
    parser.add_argument("--embeddings", required=True, help="Local semantic NPZ index")
    parser.add_argument("--query", required=True, help="Student question")
    parser.add_argument("--top-k", type=int, default=5, dest="top_k")
    parser.add_argument("--rrf-k", type=int, default=60, dest="rrf_k")
    parser.add_argument("--model", default=MODEL_NAME, help="Sentence-transformer model name")
    parser.add_argument(
        "--download-model",
        action="store_true",
        help="Allow downloading the model if it is not already cached",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        chunks = load_chunks(args.input)
        model = load_model(args.model, local_files_only=not args.download_model)
        hybrid = HybridRetriever(
            BM25Retriever(chunks),
            SemanticRetriever.from_index(model, args.embeddings),
            rrf_k=args.rrf_k,
        )
        results = hybrid.search(args.query, top_k=args.top_k)
    except (OSError, ValueError, RuntimeError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1

    if not results:
        print("No matching chunks found.")
        return 0
    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. [{result.rrf_score:.6f}] {result.document_name} | "
            f"{result.section} | page {result.page_number} | {result.category} | "
            f"BM25 rank={result.bm25_rank} semantic rank={result.semantic_rank}\n"
            f"   {result.text}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
