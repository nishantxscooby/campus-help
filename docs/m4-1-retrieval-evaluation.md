# M4.1 Expanded Retrieval Evaluation

## Scope and reproducibility

This evaluation compares the unchanged production interfaces:

1. BM25 keyword retrieval
2. Local `all-MiniLM-L6-v2` semantic retrieval
3. RRF hybrid retrieval

The corpus is `data/output/discipline-rules.json` (294 chunks) and the
existing local index is `data/output/discipline-rules-embeddings.npz`.
All methods use top 5 output. Semantic retrieval uses its existing threshold
of `0.2`; hybrid uses the existing candidate pool of 10 and RRF `k=60`.
No model, scoring algorithm, ingestion code, or production default changed.

Run:

```bash
python scripts/m4_1_evaluate.py
python -m pytest
python -m compileall -q campus_help tests scripts
```

The raw ranked outputs, metadata, source ranks, scores, and query metrics are
in [`m4-1-retrieval-results.json`](./m4-1-retrieval-results.json).

## Dataset and labels

The dataset contains 40 questions:

| Category | Questions |
|---|---:|
| Prohibited activities | 10 |
| Investigation procedure | 6 |
| Conduct and responsibilities | 5 |
| Punishments and penalties | 5 |
| Committees and powers | 4 |
| Appeals and review | 2 |
| Unsupported | 8 |
| **Total** | **40** |

There are 32 answerable questions and 8 unsupported questions. Labels were
manually established from exact source chunks, with page references recorded
in [`m4-1-relevance-judgments.md`](./m4-1-relevance-judgments.md). The labels
are verified evidence sets, not automatically selected top results. They are
not proven exhaustive over all 294 chunks, so Recall@5 is explicitly
**provisional manual-set recall**, not full-corpus recall.

## Aggregate answerable results

| Method | Precision@5 | Recall@5* | MRR | Hit Rate@5 |
|---|---:|---:|---:|---:|
| BM25 | 0.188 | 0.589 | 0.590 | 0.781 |
| Semantic | 0.200 | 0.609 | 0.612 | 0.750 |
| Hybrid (RRF) | **0.219** | **0.677** | **0.686** | **0.844** |

\* Recall uses the manually listed relevant chunk IDs for each question and
is provisional because exhaustive corpus annotation was not established.
Precision is low in part because several questions require multiple evidence
chunks while only five results are returned.

On this expanded set, the current hybrid configuration has the best aggregate
values among the three methods. This differs from the earlier five-question
evaluation and demonstrates why the default should not be changed based on
the smaller sample alone.

## Query-level results

Each cell is `relevant results in top five / 5, MRR`. A zero means no listed
relevant chunk appeared in the top five.

| Question | BM25 | Semantic | Hybrid |
|---|---|---|---|
| M41-Q001 | 1/5, 0.50 | 1/5, 0.50 | 1/5, 0.50 |
| M41-Q002 | 1/5, 1.00 | 1/5, 1.00 | 1/5, 1.00 |
| M41-Q003 | 1/5, 0.50 | 2/5, 1.00 | 1/5, 1.00 |
| M41-Q004 | 1/5, 1.00 | 1/5, 1.00 | 1/5, 1.00 |
| M41-Q005 | 1/5, 0.50 | 1/5, 0.50 | 1/5, 0.50 |
| M41-Q006 | 0/5, 0.00 | 0/5, 0.00 | 0/5, 0.00 |
| M41-Q007 | 0/5, 0.00 | 1/5, 1.00 | 1/5, 0.33 |
| M41-Q008 | 1/5, 1.00 | 1/5, 0.33 | 1/5, 1.00 |
| M41-Q009 | 2/5, 1.00 | 2/5, 0.50 | 3/5, 1.00 |
| M41-Q010 | 0/5, 0.00 | 1/5, 0.25 | 1/5, 0.25 |
| M41-Q011 | 1/5, 0.50 | 2/5, 1.00 | 2/5, 1.00 |
| M41-Q012 | 2/5, 1.00 | 2/5, 1.00 | 2/5, 1.00 |
| M41-Q013 | 2/5, 0.50 | 2/5, 1.00 | 2/5, 0.50 |
| M41-Q014 | 1/5, 1.00 | 2/5, 1.00 | 1/5, 1.00 |
| M41-Q015 | 0/5, 0.00 | 1/5, 0.50 | 1/5, 0.20 |
| M41-Q016 | 1/5, 0.20 | 0/5, 0.00 | 0/5, 0.00 |
| M41-Q017 | 2/5, 1.00 | 2/5, 1.00 | 2/5, 1.00 |
| M41-Q018 | 1/5, 0.50 | 0/5, 0.00 | 1/5, 0.33 |
| M41-Q019 | 1/5, 1.00 | 1/5, 0.50 | 1/5, 1.00 |
| M41-Q020 | 0/5, 0.00 | 0/5, 0.00 | 0/5, 0.00 |
| M41-Q021 | 1/5, 1.00 | 1/5, 1.00 | 1/5, 1.00 |
| M41-Q022 | 1/5, 0.33 | 2/5, 1.00 | 2/5, 1.00 |
| M41-Q023 | 1/5, 1.00 | 1/5, 0.50 | 1/5, 1.00 |
| M41-Q024 | 1/5, 1.00 | 0/5, 0.00 | 1/5, 1.00 |
| M41-Q025 | 1/5, 1.00 | 0/5, 0.00 | 1/5, 0.33 |
| M41-Q026 | 0/5, 0.00 | 0/5, 0.00 | 0/5, 0.00 |
| M41-Q027 | 0/5, 0.00 | 0/5, 0.00 | 0/5, 0.00 |
| M41-Q028 | 2/5, 0.33 | 1/5, 1.00 | 1/5, 1.00 |
| M41-Q029 | 1/5, 1.00 | 1/5, 1.00 | 1/5, 1.00 |
| M41-Q030 | 1/5, 0.50 | 1/5, 1.00 | 2/5, 1.00 |
| M41-Q031 | 1/5, 0.50 | 1/5, 1.00 | 1/5, 1.00 |
| M41-Q032 | 1/5, 1.00 | 1/5, 1.00 | 1/5, 1.00 |

## Unsupported questions and refusal limitations

All eight unsupported questions returned results from the discipline corpus
because retrieval always selects the closest available text. For example,
BM25 produced high lexical scores for Q038 (library overdue fine) and Q040
(dining price), while semantic retrieval produced its highest unsupported
score for Q037 (hostel room application). These results were manually judged
unrelated to the requested fact; they are not evidence that the questions are
answerable.

The system currently has no calibrated abstention or answerability classifier.
Therefore this evaluation reports result counts and raw scores in the JSON,
but does not claim a refusal accuracy metric. A future refusal evaluation
needs separately labeled supported/unsupported questions and a defined
abstention rule.

## Citation and evidence quality

Manual review of the labeled chunks found:

- Page and document metadata were preserved in all inspected retrieved
  records.
- Procedural questions often require multiple chunks. For example, Q017
  needs both complaint intake (`8995f95b4d376550`, page 3) and witness/evidence
  handling (`0cdb342f55dd0425`, page 3).
- Hybrid generally improved multi-evidence coverage for Q009 and Q030, but a
  top-five result can still omit a necessary detail.
- Some chunks are continuations or headings. A citation to only a continuation
  can be incomplete, so an answer layer must cite adjacent evidence or return
  multiple chunks.
- Unsupported questions can retrieve text with high scores; score magnitude
  alone must not be presented as citation evidence.

## Failure cases and recommendation

BM25 missed or ranked weakly for broad policy language (Q006, Q007, Q010,
Q015, Q020, Q026, and Q027). Semantic retrieval handled synonyms better but
missed several exact procedural or penalty chunks (Q006, Q016, Q018, Q020,
Q024–Q027). Hybrid inherited some failures but had the strongest overall
coverage and MRR, including the complete listed set for Q009.

The evidence supports **keeping the current hybrid configuration as the
production default for now**, not replacing it with semantic-only retrieval.
This is a 40-question, single-document evaluation with provisional relevance
recall and no abstention labels; it is evidence of a current benchmark result,
not proof of universal superiority. Existing M4 defaults and reports remain
unchanged. A larger multi-document, independently reviewed test set and a
separate refusal/answerability experiment are needed before tuning or
changing defaults.
