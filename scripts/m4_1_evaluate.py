"""Run the manually labeled M4.1 retrieval evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from campus_help.hybrid.engine import (
    DEFAULT_CANDIDATE_K,
    DEFAULT_RRF_K,
    HybridRetriever,
)
from campus_help.retrieval.engine import BM25Retriever
from campus_help.retrieval.loader import load_chunks
from campus_help.semantic.engine import SemanticRetriever
from campus_help.semantic.model import load_model

TOP_K = 5
SEMANTIC_THRESHOLD = 0.2


def _serialize(results: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        result.to_dict() | {"rank": rank}
        for rank, result in enumerate(results, start=1)
    ]


def _evaluate_answerable(
    results: list[Any], relevant_ids: set[str]
) -> dict[str, Any]:
    ranks = {
        result.chunk_id: rank for rank, result in enumerate(results, start=1)
    }
    relevant_ranks = {
        chunk_id: ranks.get(chunk_id)
        for chunk_id in sorted(relevant_ids)
    }
    hits = sum(rank is not None for rank in relevant_ranks.values())
    first_rank = min(
        (rank for rank in relevant_ranks.values() if rank is not None),
        default=None,
    )
    return {
        "relevant_retrieved": hits,
        "relevant_total": len(relevant_ids),
        "precision_at_5": hits / TOP_K,
        "recall_at_5": hits / len(relevant_ids) if relevant_ids else None,
        "mrr": 1 / first_rank if first_rank else 0.0,
        "hit_rate_at_5": int(hits > 0),
        "relevant_ranks": relevant_ranks,
        "recall_status": "provisional_manual_set",
    }


def _evaluate_unanswerable(results: list[Any]) -> dict[str, Any]:
    scores = [
        float(
            result.score
            if hasattr(result, "score")
            else result.rrf_score
        )
        for result in results
    ]
    return {
        "result_count": len(results),
        "top_score": scores[0] if scores else None,
        "scores": scores,
        "manual_review_required": True,
        "interpretation": (
            "Retrieval scores are not calibrated evidence of answerability; "
            "inspect result text separately."
        ),
    }


def _macro(metrics: list[dict[str, Any]]) -> dict[str, float]:
    names = (
        "precision_at_5",
        "recall_at_5",
        "mrr",
        "hit_rate_at_5",
    )
    return {name: mean(float(metric[name]) for metric in metrics) for name in names}


def _run_method(
    name: str,
    questions: list[dict[str, Any]],
    search: Any,
) -> dict[str, Any]:
    query_results: list[dict[str, Any]] = []
    answerable_metrics: list[dict[str, Any]] = []
    for question in questions:
        results = search(question["question"], top_k=TOP_K)
        serialized = _serialize(results)
        if question["answerable"]:
            metrics = _evaluate_answerable(
                results, set(question["relevant_chunk_ids"])
            )
            answerable_metrics.append(metrics)
        else:
            metrics = _evaluate_unanswerable(results)
        query_results.append(
            {
                "question_id": question["question_id"],
                "question": question["question"],
                "answerable": question["answerable"],
                "results": serialized,
                "metrics": metrics,
            }
        )
    return {
        "method": name,
        "top_k": TOP_K,
        "answerable_macro": _macro(answerable_metrics),
        "query_results": query_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--questions", default="data/evaluation/m4_1_questions.json"
    )
    parser.add_argument(
        "--chunks", default="data/output/discipline-rules.json"
    )
    parser.add_argument(
        "--embeddings",
        default="data/output/discipline-rules-embeddings.npz",
    )
    parser.add_argument(
        "--output", default="docs/m4-1-retrieval-results.json"
    )
    args = parser.parse_args()

    questions_path = Path(args.questions)
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    if not isinstance(questions, list) or not questions:
        raise ValueError("Questions file must contain a non-empty JSON array")

    chunks = load_chunks(args.chunks)
    chunk_ids = {chunk.chunk_id for chunk in chunks}
    for question in questions:
        missing = set(question["relevant_chunk_ids"]) - chunk_ids
        if missing:
            raise ValueError(
                f"{question['question_id']} references unknown chunks: "
                f"{sorted(missing)}"
            )

    model = load_model()
    bm25 = BM25Retriever(chunks)
    semantic = SemanticRetriever.from_index(model, args.embeddings)
    hybrid = HybridRetriever(
        bm25,
        semantic,
        candidate_k=DEFAULT_CANDIDATE_K,
        rrf_k=DEFAULT_RRF_K,
    )

    output = {
        "evaluation": "M4.1 expanded retrieval evaluation",
        "questions_file": str(questions_path),
        "chunk_count": len(chunks),
        "answerable_count": sum(q["answerable"] for q in questions),
        "unanswerable_count": sum(not q["answerable"] for q in questions),
        "configuration": {
            "top_k": TOP_K,
            "semantic_threshold": SEMANTIC_THRESHOLD,
            "hybrid_candidate_k": DEFAULT_CANDIDATE_K,
            "hybrid_rrf_k": DEFAULT_RRF_K,
            "recall_denominator": (
                "manually verified relevant_chunk_ids per question; "
                "recall is provisional unless exhaustive annotation is confirmed"
            ),
        },
        "methods": {
            "bm25": _run_method("bm25", questions, bm25.search),
            "semantic": _run_method(
                "semantic",
                questions,
                lambda query, top_k: semantic.search(
                    query, top_k=top_k, min_similarity=SEMANTIC_THRESHOLD
                ),
            ),
            "hybrid": _run_method("hybrid", questions, hybrid.search),
        },
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote M4.1 results to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
