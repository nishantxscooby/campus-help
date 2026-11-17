# M4 Controlled Retrieval Experiments

## Baseline and safeguards

The existing production implementations were inspected and not modified:

- BM25: `BM25Retriever.search(query, top_k=...)`
- Semantic: `SemanticRetriever.search(query, top_k=..., min_similarity=...)`
- Hybrid: `HybridRetriever` with `candidate_k=10`, `rrf_k=60`, and top-five
  output

The existing manually reviewed relevance labels from
[`m4-retrieval-evaluation.md`](./m4-retrieval-evaluation.md) were reused
without changing the five questions or labels. They are pooled-candidate
labels, not full-corpus judgments.

The project-scoped Git status was recorded before experiments. The workspace
is an uncommitted repository with the existing project files and generated
artifacts untracked; no files were reset, discarded, or overwritten. The only
experiment additions are this report, the reproducibility script, and its raw
results file.

Dataset:

- `data/output/discipline-rules.json`
- 294 chunks
- `data/output/discipline-rules-embeddings.npz`
- locally cached `all-MiniLM-L6-v2`

The threshold experiments used an experiment-only adapter around the existing
semantic `min_similarity` parameter. Production `HybridRetriever` was not
changed.

## Commands

```bash
python scripts/m4_controlled_experiments.py \
  --output docs/m4-controlled-experiments-results.json
python -m pytest
```

The raw ranked outputs and query-level relevance rank maps are saved in
[`m4-controlled-experiments-results.json`](./m4-controlled-experiments-results.json).

## Metrics

Recall is **pooled candidate Recall@5**: the denominator is the manually
reviewed relevant set in the union of the three methods' original top-five
results for each query. It is not recall over all 294 chunks. Precision@5,
MRR, and relevant-chunk counts use the same labels.

### Baseline comparison

| Method/configuration | Mean Precision@5 | Mean pooled Recall@5 | Mean MRR | Relevant hits by Q1-Q5 |
|---|---:|---:|---:|---|
| BM25-only | 0.400 | 0.433 | 0.600 | 0, 0, 2, 5, 3 |
| Semantic-only, threshold 0.20 | **0.680** | **0.727** | **1.000** | 4, 4, 2, 5, 2 |
| Hybrid, pool 10, RRF k=60, threshold 0.20 | 0.560 | 0.587 | 0.867 | 3, 2, 1, 5, 3 |

### Experiment A: candidate pool size

RRF `k=60` and semantic threshold `0.20` were held constant.

| BM25 + semantic pool | Mean Precision@5 | Mean pooled Recall@5 | Mean MRR | Relevant hits by Q1-Q5 |
|---:|---:|---:|---:|---|
| 10 + 10 (baseline) | **0.560** | **0.587** | **0.867** | 3, 2, 1, 5, 3 |
| 20 + 20 | 0.400 | 0.487 | 0.717 | 2, 2, 1, 2, 3 |
| 30 + 30 | 0.400 | 0.487 | 0.867 | 2, 2, 1, 2, 3 |

Larger candidate pools did not improve retrieval. They introduced more
single-source candidates into the fusion set and displaced relevant results
from the final five.

### Experiment B: RRF constant

Candidate pool `10 + 10` and threshold `0.20` were held constant.

| RRF k | Mean Precision@5 | Mean pooled Recall@5 | Mean MRR | Relevant hits by Q1-Q5 |
|---:|---:|---:|---:|---|
| 20 | 0.560 | 0.587 | 0.867 | 3, 2, 1, 5, 3 |
| 40 | 0.560 | 0.587 | 0.867 | 3, 2, 1, 5, 3 |
| 60 (baseline) | 0.560 | 0.587 | 0.867 | 3, 2, 1, 5, 3 |
| 80 | 0.560 | 0.587 | 0.867 | 3, 2, 1, 5, 3 |

All four settings produced identical top-five memberships and ranks for these
queries. Changing `k` alone provides no evidence for a production adjustment.

### Experiment C: semantic threshold

Candidate pool `10 + 10`, RRF `k=60`, and output top five were held constant.
The candidate counts below are the number of semantic chunks above threshold
when searching the full 294-chunk index, in Q1-Q5 order.

| Threshold | Semantic candidates Q1-Q5 | Mean Precision@5 | Mean pooled Recall@5 | Mean MRR | Relevant hits by Q1-Q5 |
|---:|---|---:|---:|---:|---|
| 0.20 (baseline) | 196, 215, 171, 192, 175 | 0.560 | 0.587 | 0.867 | 3, 2, 1, 5, 3 |
| 0.25 | 171, 182, 139, 157, 144 | 0.560 | 0.587 | 0.867 | 3, 2, 1, 5, 3 |
| 0.30 | 149, 153, 77, 135, 107 | 0.560 | 0.587 | 0.867 | 3, 2, 1, 5, 3 |
| 0.35 | 103, 139, 53, 113, 48 | 0.560 | 0.587 | 0.867 | 3, 2, 1, 5, 3 |

No manually labeled relevant chunk disappeared from the hybrid top five as
the threshold increased. However, the unchanged result set does not show
that higher thresholds are safer: it only shows that the top ten semantic
results for these five questions remained above each tested threshold.

## Per-query relevant-rank comparisons

`-` means the known relevant chunk was absent from the method's top five.
These are the manually reviewed IDs from the existing evaluation.

### Baseline and candidate pools

| Query | Configuration | Relevant chunk ranks |
|---|---|---|
| Q1 investigation | Hybrid pool 10 | `0cdb342f55dd0425`: 4; `047e458c9fdc7f71`: 5; `1c5dc37875e96455`: -; `94dc298b1e4ee1aa`: -; `5edf7961bdb76d97`: 3 |
| Q1 investigation | Hybrid pool 20 | `0cdb342f55dd0425`: 5; `047e458c9fdc7f71`: -; `1c5dc37875e96455`: -; `94dc298b1e4ee1aa`: -; `5edf7961bdb76d97`: 3 |
| Q1 investigation | Hybrid pool 30 | `0cdb342f55dd0425`: -; `047e458c9fdc7f71`: -; `1c5dc37875e96455`: 4; `94dc298b1e4ee1aa`: -; `5edf7961bdb76d97`: 3 |
| Q2 punishments | Hybrid pool 10 | `8fce4c0b6a83c0fd`: 4; `edf7b7286aaebfc1`: 1; `37d8228a915497c0`: -; `0396efee68c45a18`: - |
| Q2 punishments | Hybrid pool 20 | `8fce4c0b6a83c0fd`: 4; `edf7b7286aaebfc1`: 1; `37d8228a915497c0`: -; `0396efee68c45a18`: - |
| Q2 punishments | Hybrid pool 30 | `8fce4c0b6a83c0fd`: -; `edf7b7286aaebfc1`: 1; `37d8228a915497c0`: 4; `0396efee68c45a18`: - |
| Q3 misconduct actions | Hybrid pool 10 | `407ea400e4a6bc87`: 1; `4fdfafc18b3d0fed`: -; `8af09b282ba7ab35`: - |
| Q3 misconduct actions | Hybrid pool 20 | `407ea400e4a6bc87`: 1; `4fdfafc18b3d0fed`: -; `8af09b282ba7ab35`: - |
| Q3 misconduct actions | Hybrid pool 30 | `407ea400e4a6bc87`: 1; `4fdfafc18b3d0fed`: -; `8af09b282ba7ab35`: - |
| Q4 trouble broadly | Hybrid pool 10 | 5 relevant chunks retrieved; ranks include `4500b5e1df5458ab`: 1 and `a243fd01c2a2a7e1`: 2 |
| Q4 trouble broadly | Hybrid pool 20 | 2 relevant chunks retrieved; `4500b5e1df5458ab`: 4; `a243fd01c2a2a7e1`: 5 |
| Q4 trouble broadly | Hybrid pool 30 | 2 relevant chunks retrieved; `4500b5e1df5458ab`: 1; `611b52029bcb3803`: 4 |
| Q5 appeal | Hybrid pool 10 | `94dc298b1e4ee1aa`: 1; `74b85be0218069f0`: 2; `503e6f5b4cfd5b7d`: 5 |
| Q5 appeal | Hybrid pool 20 | `94dc298b1e4ee1aa`: 1; `74b85be0218069f0`: 2; `503e6f5b4cfd5b7d`: 5 |
| Q5 appeal | Hybrid pool 30 | `94dc298b1e4ee1aa`: 1; `74b85be0218069f0`: 2; `503e6f5b4cfd5b7d`: 5 |

### RRF constants and thresholds

For every query, RRF `k=20`, `40`, `60`, and `80` produced the same relevant
rank map as the pool-10 baseline. Thresholds `0.25`, `0.30`, and `0.35` also
produced the same rank map as threshold `0.20`. Therefore there were no
query-level entered, disappeared, improved, or worsened relevant ranks in
Experiments B or C.

## Previously demoted semantic chunks

| Chunk | Query | Semantic baseline rank | Hybrid pool 10 | Pool 20 | Pool 30 | RRF/threshold variants |
|---|---|---:|---:|---:|---:|---|
| `0cdb342f55dd0425` | Q1 investigation | 1 | 4 | 5 | - | unchanged at 4 for all RRF k and thresholds |
| `047e458c9fdc7f71` | Q1 investigation | 2 | 5 | - | - | unchanged at 5 for all RRF k and thresholds |
| `8fce4c0b6a83c0fd` | Q2 punishments | 1 | 4 | 4 | - | unchanged at 4 for all RRF k and thresholds |

Neither larger pools nor different RRF constants rescued all three previously
demoted chunks. The pool-20 experiment worsened Q1 and did not improve Q2;
pool 30 caused the punishment chunk to disappear from the final five.

## Recommendation

Among the tested configurations, **semantic-only retrieval is the strongest
measured configuration** on this five-question set:

- Precision@5: 0.680
- pooled Recall@5: 0.727
- MRR: 1.000

No hybrid variant improved on the current pool-10/RRF-60 baseline, and the
current baseline was better than pool sizes 20 and 30. RRF constants and
semantic thresholds were performance-neutral for these queries.

Do **not** change production defaults based only on this small evaluation.
Keep the current hybrid configuration unchanged for compatibility and
comparison, while treating semantic retrieval as the primary candidate for
policy/procedural queries in this document. Before making that primary-choice
change, expand the manually judged query set across document categories and
include full-corpus relevance judgments or a larger judged pool.

## Limitations

- Five queries and one 23-page document are not a general retrieval
  benchmark.
- Recall is pooled-candidate recall, not full-corpus recall.
- The existing labels contain no judgments for chunks outside the pooled
  candidates; a relevant chunk entering a larger candidate pool can therefore
  remain unlabeled unless it was already in the reviewed set.
- Threshold candidate counts are full-index counts, while hybrid fusion uses
  only the top ten candidates from each source.
- No additional model, reranker, score fusion, or ingestion change was tested.
