"""Reproduce controlled M4 retrieval experiments without changing production code."""

import argparse
import json
from pathlib import Path
from typing import Any

from campus_help.hybrid.engine import HybridRetriever
from campus_help.retrieval.engine import BM25Retriever
from campus_help.retrieval.loader import load_chunks
from campus_help.semantic.engine import SemanticRetriever
from campus_help.semantic.model import load_model

QUERIES = [
    "How does the university investigate a student misconduct complaint?",
    "What punishments can the university give students?",
    "What actions are considered disciplinary misconduct?",
    "What can get a student into trouble at university?",
    "How can a student appeal a disciplinary punishment?",
]

# Reused from docs/m4-retrieval-evaluation.md; these are pooled-candidate labels.
RELEVANT_CHUNK_IDS = [
    {"0cdb342f55dd0425", "047e458c9fdc7f71", "1c5dc37875e96455",
     "94dc298b1e4ee1aa", "5edf7961bdb76d97"},
    {"8fce4c0b6a83c0fd", "edf7b7286aaebfc1", "37d8228a915497c0",
     "0396efee68c45a18"},
    {"407ea400e4a6bc87", "4fdfafc18b3d0fed", "8af09b282ba7ab35"},
    {"a243fd01c2a2a7e1", "4fdfafc18b3d0fed", "43f290b1e738627a",
     "bbbe8ba31bb3a719", "e053751d39b8cf6e", "4500b5e1df5458ab",
     "09a8f3b9f3bb9c99", "611b52029bcb3803", "067e151abf58a54b",
     "0396efee68c45a18"},
    {"503e6f5b4cfd5b7d", "94dc298b1e4ee1aa", "74b85be0218069f0"},
]


class ThresholdSemanticRetriever:
    """Experiment-only adapter for SemanticRetriever's existing threshold API."""

    def __init__(self, retriever: SemanticRetriever, threshold: float) -> None:
        self._retriever = retriever
        self._threshold = threshold

    def search(self, query: str, top_k: int = 5):
        return self._retriever.search(query, top_k=top_k, min_similarity=self._threshold)


def _serialize(results: list[Any]) -> list[dict[str, Any]]:
    return [result.to_dict() | {"rank": rank} for rank, result in enumerate(results, 1)]


def _metrics(results_by_query: list[list[Any]]) -> list[dict[str, Any]]:
    metrics = []
    for query_index, results in enumerate(results_by_query):
        ranks = {result.chunk_id: rank for rank, result in enumerate(results, 1)}
        known = {
            chunk_id: ranks.get(chunk_id)
            for chunk_id in RELEVANT_CHUNK_IDS[query_index]
        }
        hits = sum(rank is not None for rank in known.values())
        first = min((rank for rank in known.values() if rank is not None), default=0)
        metrics.append(
            {
                "relevant_retrieved": hits,
                "relevant_total": len(known),
                "precision_at_5": hits / 5,
                "pooled_recall_at_5": hits / len(known),
                "mrr": 1 / first if first else 0,
                "relevant_ranks": known,
            }
        )
    return metrics


def _run_hybrid(
    bm25: BM25Retriever,
    semantic: SemanticRetriever,
    candidate_k: int,
    rrf_k: int,
    threshold: float,
) -> dict[str, Any]:
    hybrid = HybridRetriever(
        bm25,
        ThresholdSemanticRetriever(semantic, threshold),
        candidate_k=candidate_k,
        rrf_k=rrf_k,
    )
    results = [hybrid.search(query, top_k=5) for query in QUERIES]
    return {"results": [_serialize(results) for results in results], "metrics": _metrics(results)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/output/discipline-rules.json")
    parser.add_argument("--embeddings", default="data/output/discipline-rules-embeddings.npz")
    parser.add_argument("--output", default="docs/m4-controlled-experiments-results.json")
    args = parser.parse_args()

    chunks = load_chunks(args.input)
    model = load_model()
    bm25 = BM25Retriever(chunks)
    semantic = SemanticRetriever.from_index(model, args.embeddings)

    bm25_results = [bm25.search(query, top_k=5) for query in QUERIES]
    semantic_results = [
        semantic.search(query, top_k=5, min_similarity=0.2) for query in QUERIES
    ]
    output: dict[str, Any] = {
        "queries": QUERIES,
        "chunk_count": len(chunks),
        "baseline": {
            "bm25": {"results": [_serialize(results) for results in bm25_results],
                     "metrics": _metrics(bm25_results)},
            "semantic": {"results": [_serialize(results) for results in semantic_results],
                         "metrics": _metrics(semantic_results)},
            "hybrid": _run_hybrid(bm25, semantic, 10, 60, 0.2),
        },
        "experiments": {"candidate_pool": {}, "rrf_k": {}, "semantic_threshold": {}},
    }
    for candidate_k in (10, 20, 30):
        output["experiments"]["candidate_pool"][str(candidate_k)] = _run_hybrid(
            bm25, semantic, candidate_k, 60, 0.2
        )
    for rrf_k in (20, 40, 60, 80):
        output["experiments"]["rrf_k"][str(rrf_k)] = _run_hybrid(
            bm25, semantic, 10, rrf_k, 0.2
        )
    for threshold in (0.20, 0.25, 0.30, 0.35):
        experiment = _run_hybrid(bm25, semantic, 10, 60, threshold)
        experiment["semantic_candidates_all"] = [
            len(semantic.search(query, top_k=len(chunks), min_similarity=threshold))
            for query in QUERIES
        ]
        output["experiments"]["semantic_threshold"][str(threshold)] = experiment

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote experiment results to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
