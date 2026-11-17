# M4 Retrieval Evaluation

## Scope and method

This evaluation ran the existing BM25, semantic, and hybrid CLIs/interfaces
against the same processed Bennett University discipline document:

- Input: `data/output/discipline-rules.json`
- Chunks: 294
- Semantic index: `data/output/discipline-rules-embeddings.npz`
- Semantic model: locally cached `all-MiniLM-L6-v2`
- Candidate/output size: top 5
- Hybrid candidate pools: top 10 from BM25 and semantic retrieval
- Hybrid RRF constant: `k=60`

Relevance labels below are manual judgments from the returned chunk text, not
similarity-score thresholds. `R` means the chunk contains direct evidence for
the question; `N` means it does not. Text is shown as a verbatim excerpt.

## Query 1

**How does the university investigate a student misconduct complaint?**

| Method | Rank | Chunk ID | Page | Section | Score/diagnostics | Label | Evidence excerpt |
|---|---:|---|---:|---|---|:---:|---|
| BM25 | 1 | `407ea400e4a6bc87` | 2 | Giving undivided attention... | 6.523342 | N | Acts of Indiscipline and Misconduct definition |
| BM25 | 2 | `ad7780be90e752c6` | 19 | Any other | 5.790523 | N | Any other offence |
| BM25 | 3 | `06e306816d55b10f` | 8 | Aiding unauthorized entry... | 5.331592 | N | Any other offence |
| BM25 | 4 | `b2aca09647ea9cab` | 12 | Expulsion from | 4.197067 | N | Returning late to Campus |
| BM25 | 5 | `6a442d52ae26b7ef` | 13 | Page 13 of 23 | 3.941556 | N | Non-cooperation with staff |
| Semantic | 1 | `0cdb342f55dd0425` | 3 | Page 3 of 23 | 0.588107 | R | Witness statements, cross-examination, evidence review, show-cause notice, and recommendation |
| Semantic | 2 | `047e458c9fdc7f71` | 5 | Page 5 of 23 | 0.574029 | R | Proctorial Committee records proceedings and submits facts, evidence, recommendations |
| Semantic | 3 | `407ea400e4a6bc87` | 2 | Giving undivided attention... | 0.573797 | N | Misconduct definition |
| Semantic | 4 | `1c5dc37875e96455` | 4 | Page 4 of 23 | 0.557747 | R | Escalation to University Proctorial Committee and separation of investigator |
| Semantic | 5 | `94dc298b1e4ee1aa` | 3 | Final report and recommendations... | 0.552928 | R | Final report, approval, decision, and communication of punishment |
| Hybrid | 1 | `407ea400e4a6bc87` | 2 | Giving undivided attention... | RRF 0.032522; BM25 1; semantic 3 | N | Misconduct definition |
| Hybrid | 2 | `edf7b7286aaebfc1` | 8 | 4. PUNISHMENT | RRF 0.029851; BM25 7; semantic 7 | N | Punishment heading |
| Hybrid | 3 | `5edf7961bdb76d97` | 23 | 7. GENERAL | RRF 0.029437; BM25 6; semantic 10 | R | Inquiry, due process, and interim suspension |
| Hybrid | 4 | `0cdb342f55dd0425` | 3 | Page 3 of 23 | RRF 0.016393; BM25 null; semantic 1 | R | Investigation steps and evidence review |
| Hybrid | 5 | `047e458c9fdc7f71` | 5 | Page 5 of 23 | RRF 0.016129; BM25 null; semantic 2 | R | Committee inquiry record and report |

## Query 2

**What punishments can the university give students?**

| Method | Rank | Chunk ID | Page | Section | Score/diagnostics | Label | Evidence excerpt |
|---|---:|---|---:|---|---|:---:|---|
| BM25 | 1 | `b1a7f5e8eb20503f` | 15 | OR | 4.588178 | N | Abusive/offensive emails |
| BM25 | 2 | `09a8f3b9f3bb9c99` | 15 | OR | 4.588178 | N | Causing bodily harm |
| BM25 | 3 | `9fb8194ce0d428aa` | 21 | Police for appropriate action | 4.588178 | N | Hacking email accounts |
| BM25 | 4 | `4dcc82ef2816c227` | 15 | OR | 4.182308 | N | Abusive social-media content |
| BM25 | 5 | `e053751d39b8cf6e` | 13 | Using TV | 4.134938 | N | Hostel disturbance |
| Semantic | 1 | `8fce4c0b6a83c0fd` | 8 | CATEGORY II | 0.659915 | R | Admonition, fine, recovery, property costs, withdrawal of facilities |
| Semantic | 2 | `edf7b7286aaebfc1` | 8 | 4. PUNISHMENT | 0.655583 | R | Competent authority may impose listed punishments |
| Semantic | 3 | `37d8228a915497c0` | 13 | Scholarship/Internship/placement | 0.598549 | R | Withholding privileges or expulsion |
| Semantic | 4 | `067e151abf58a54b` | 6 | CATEGORY I | 0.597979 | N | Category I misconduct examples |
| Semantic | 5 | `0396efee68c45a18` | 21 | Causing bodily harm/injury | 0.597499 | R | Warning, counselling, suspension, withholding, expulsion |
| Hybrid | 1 | `edf7b7286aaebfc1` | 8 | 4. PUNISHMENT | RRF 0.030835; BM25 8; semantic 2 | R | Punishment rule |
| Hybrid | 2 | `09a8f3b9f3bb9c99` | 15 | OR | RRF 0.030415; BM25 2; semantic 10 | N | Bodily harm offence |
| Hybrid | 3 | `de043ef96a8ae1f6` | 2 | 2. APPLICATION OF RULES | RRF 0.029631; BM25 7; semantic 8 | N | Scope and peaceful protest rules |
| Hybrid | 4 | `8fce4c0b6a83c0fd` | 8 | CATEGORY II | RRF 0.016393; BM25 null; semantic 1 | R | Punishment list |
| Hybrid | 5 | `b1a7f5e8eb20503f` | 15 | OR | RRF 0.016393; BM25 1; semantic null | N | Abusive/offensive emails |

## Query 3

**What actions are considered disciplinary misconduct?**

| Method | Rank | Chunk ID | Page | Section | Score/diagnostics | Label | Evidence excerpt |
|---|---:|---|---:|---|---|:---:|---|
| BM25 | 1 | `407ea400e4a6bc87` | 2 | Giving undivided attention... | 3.523570 | R | Definition and introduction to violations |
| BM25 | 2 | `4fdfafc18b3d0fed` | 23 | Card/codes/access | 3.057954 | R | Unauthorized access and taking a dayscholar without authorization |
| BM25 | 3 | `5edf7961bdb76d97` | 23 | 7. GENERAL | 2.682562 | N | Inquiry and punishment safeguards |
| BM25 | 4 | `edf7b7286aaebfc1` | 8 | 4. PUNISHMENT | 2.662436 | N | Punishment rule |
| BM25 | 5 | `8995f95b4d376550` | 3 | Page 3 of 23 | 2.596296 | N | Enquiry procedure |
| Semantic | 1 | `8af09b282ba7ab35` | 7 | Page 7 of 23 | 0.678772 | R | Continuation stating an act may violate discipline and conduct |
| Semantic | 2 | `407ea400e4a6bc87` | 2 | Giving undivided attention... | 0.577943 | R | Misconduct definition |
| Semantic | 3 | `94dc298b1e4ee1aa` | 3 | Final report and recommendations... | 0.537131 | N | Final decision and appeal context |
| Semantic | 4 | `edf7b7286aaebfc1` | 8 | 4. PUNISHMENT | 0.536275 | N | Punishment rule |
| Semantic | 5 | `0cdb342f55dd0425` | 3 | Page 3 of 23 | 0.533044 | N | Investigation procedure |
| Hybrid | 1 | `407ea400e4a6bc87` | 2 | Giving undivided attention... | RRF 0.032522; BM25 1; semantic 2 | R | Misconduct definition |
| Hybrid | 2 | `edf7b7286aaebfc1` | 8 | 4. PUNISHMENT | RRF 0.031250; BM25 4; semantic 4 | N | Punishment rule |
| Hybrid | 3 | `5edf7961bdb76d97` | 23 | 7. GENERAL | RRF 0.030579; BM25 3; semantic 8 | N | Inquiry safeguards |
| Hybrid | 4 | `0cdb342f55dd0425` | 3 | Page 3 of 23 | RRF 0.030536; BM25 6; semantic 5 | N | Investigation procedure |
| Hybrid | 5 | `94dc298b1e4ee1aa` | 3 | Final report and recommendations... | RRF 0.030159; BM25 10; semantic 3 | N | Appeal/final decision context |

## Query 4

**What can get a student into trouble at university?**

| Method | Rank | Chunk ID | Page | Section | Score/diagnostics | Label | Evidence excerpt |
|---|---:|---|---:|---|---|:---:|---|
| BM25 | 1 | `a243fd01c2a2a7e1` | 17 | Page 17 of 23 | 6.634976 | R | Aiding unauthorized entry |
| BM25 | 2 | `4fdfafc18b3d0fed` | 23 | Card/codes/access | 5.784916 | R | Unauthorized access and unauthorized dayscholar area |
| BM25 | 3 | `43f290b1e738627a` | 11 | Refusal to | 4.460657 | R | Refusal to undergo breath analyser |
| BM25 | 4 | `bbbe8ba31bb3a719` | 17 | Refusal to | 4.460657 | R | Refusal to produce identity card |
| BM25 | 5 | `e053751d39b8cf6e` | 13 | Using TV | 4.134938 | R | Hostel disturbance and possible damage |
| Semantic | 1 | `4500b5e1df5458ab` | 6 | CATEGORY II | 0.620300 | R | Forgery, false information, disorder, unauthorized entry |
| Semantic | 2 | `09a8f3b9f3bb9c99` | 15 | OR | 0.591142 | R | Causing bodily harm |
| Semantic | 3 | `611b52029bcb3803` | 7 | Page 7 of 23 | 0.570496 | R | Damage, theft, ragging, unauthorized guests, intimidation |
| Semantic | 4 | `067e151abf58a54b` | 6 | CATEGORY I | 0.564189 | R | Violence, coercion, intimidation, privacy disturbance |
| Semantic | 5 | `0396efee68c45a18` | 21 | Causing bodily harm/injury | 0.554880 | R | Conduct and associated penalties |
| Hybrid | 1 | `4500b5e1df5458ab` | 6 | CATEGORY II | RRF 0.016393; BM25 null; semantic 1 | R | Misconduct examples |
| Hybrid | 2 | `a243fd01c2a2a7e1` | 17 | Page 17 of 23 | RRF 0.016393; BM25 1; semantic null | R | Unauthorized entry |
| Hybrid | 3 | `09a8f3b9f3bb9c99` | 15 | OR | RRF 0.016129; BM25 null; semantic 2 | R | Bodily harm |
| Hybrid | 4 | `4fdfafc18b3d0fed` | 23 | Card/codes/access | RRF 0.016129; BM25 2; semantic null | R | Unauthorized access |
| Hybrid | 5 | `43f290b1e738627a` | 11 | Refusal to | RRF 0.015873; BM25 3; semantic null | R | Breath analyser refusal |

## Query 5

**How can a student appeal a disciplinary punishment?**

| Method | Rank | Chunk ID | Page | Section | Score/diagnostics | Label | Evidence excerpt |
|---|---:|---|---:|---|---|:---:|---|
| BM25 | 1 | `503e6f5b4cfd5b7d` | 5 | Page 5 of 23 | 5.955597 | R | No more appeals after the final decision |
| BM25 | 2 | `94dc298b1e4ee1aa` | 3 | Final report and recommendations... | 5.420896 | R | Right to appeal to Vice Chancellor |
| BM25 | 3 | `5edf7961bdb76d97` | 23 | 7. GENERAL | 5.299156 | N | General punishment safeguards |
| BM25 | 4 | `74b85be0218069f0` | 5 | Page 5 of 23 | 5.063366 | R | Written appeal to Vice-Chancellor within 5 working days and review powers |
| BM25 | 5 | `fbf867d031fbe036` | 10 | OR | 4.713423 | N | Inebriated condition offence |
| Semantic | 1 | `94dc298b1e4ee1aa` | 3 | Final report and recommendations... | 0.664541 | R | Right to appeal to Vice Chancellor |
| Semantic | 2 | `74b85be0218069f0` | 5 | Page 5 of 23 | 0.613708 | R | Appeal procedure and five-working-day deadline |
| Semantic | 3 | `047e458c9fdc7f71` | 5 | Page 5 of 23 | 0.574353 | N | Inquiry record and punishment communication |
| Semantic | 4 | `edf7b7286aaebfc1` | 8 | 4. PUNISHMENT | 0.568572 | N | Punishment rule |
| Semantic | 5 | `15172f98ed03cfc8` | 19 | Committeecan | 0.562337 | N | Penalty severity |
| Hybrid | 1 | `94dc298b1e4ee1aa` | 3 | Final report and recommendations... | RRF 0.032522; BM25 2; semantic 1 | R | Right to appeal |
| Hybrid | 2 | `74b85be0218069f0` | 5 | Page 5 of 23 | RRF 0.031754; BM25 4; semantic 2 | R | Appeal procedure and deadline |
| Hybrid | 3 | `5edf7961bdb76d97` | 23 | 7. GENERAL | RRF 0.031025; BM25 3; semantic 6 | N | General safeguards |
| Hybrid | 4 | `15172f98ed03cfc8` | 19 | Committeecan | RRF 0.030536; BM25 6; semantic 5 | N | Penalty severity |
| Hybrid | 5 | `503e6f5b4cfd5b7d` | 5 | Page 5 of 23 | RRF 0.016393; BM25 1; semantic null | R | Appeals thereafter |

## Pooled evaluation metrics

The denominator for recall is the manually reviewed relevant set in the
**union of the three methods' top-five results for that query**. This is a
pooled-candidate evaluation, not recall over all 294 chunks. `P@5` is the
number of relevant results in the method's top five divided by five. `MRR`
uses the reciprocal rank of the first manually relevant result; no relevant
result contributes zero.

| Query | Manually relevant pooled chunks | Method | Relevant in top 1 | Relevant in top 3 | Relevant in top 5 | P@5 | Recall@5 | MRR |
|---|---:|---|:---:|:---:|:---:|---:|---:|---:|
| Investigation | 5 | BM25 | No | No | No | 0.00 | 0.00 | 0.000 |
| Investigation | 5 | Semantic | Yes | Yes | Yes | 0.80 | 0.80 | 1.000 |
| Investigation | 5 | Hybrid | No | Yes | Yes | 0.60 | 0.60 | 0.333 |
| Punishments | 4 | BM25 | No | No | No | 0.00 | 0.00 | 0.000 |
| Punishments | 4 | Semantic | Yes | Yes | Yes | 0.80 | 1.00 | 1.000 |
| Punishments | 4 | Hybrid | Yes | Yes | Yes | 0.40 | 0.50 | 1.000 |
| Misconduct actions | 3 | BM25 | Yes | Yes | Yes | 0.40 | 0.67 | 1.000 |
| Misconduct actions | 3 | Semantic | Yes | Yes | Yes | 0.40 | 0.67 | 1.000 |
| Misconduct actions | 3 | Hybrid | Yes | No | Yes | 0.20 | 0.33 | 1.000 |
| Trouble broadly | 10 | BM25 | Yes | Yes | Yes | 1.00 | 0.50 | 1.000 |
| Trouble broadly | 10 | Semantic | Yes | Yes | Yes | 1.00 | 0.50 | 1.000 |
| Trouble broadly | 10 | Hybrid | Yes | Yes | Yes | 1.00 | 0.50 | 1.000 |
| Appeal | 3 | BM25 | Yes | Yes | Yes | 0.60 | 1.00 | 1.000 |
| Appeal | 3 | Semantic | Yes | Yes | Yes | 0.40 | 0.67 | 1.000 |
| Appeal | 3 | Hybrid | Yes | Yes | Yes | 0.60 | 1.00 | 1.000 |

### Macro averages over these five questions

| Method | Mean Precision@5 | Mean Recall@5 | Mean MRR |
|---|---:|---:|---:|
| BM25 | 0.40 | 0.43 | 0.600 |
| Semantic | 0.68 | 0.73 | 1.000 |
| Hybrid | 0.56 | 0.59 | 0.867 |

## Findings

1. Semantic retrieval was strongest for procedural and policy-summary
   questions. It returned the investigation steps for Query 1, the punishment
   list for Query 2, and the appeal procedure for Query 5 at rank 1 or 2.
2. BM25 was strongest when the question matched concrete offense wording.
   Query 4 produced five manually relevant offense examples, but it struggled
   with “investigate” and “punishments” as concepts.
3. Hybrid did not always preserve semantic-only evidence near the top. For
   Query 1, investigation chunks `0cdb342f55dd0425` and
   `047e458c9fdc7f71` were semantic ranks 1 and 2 but hybrid ranks 4 and 5.
   For Query 2, `8fce4c0b6a83c0fd` was semantic rank 1 but hybrid rank 4.
4. Hybrid improved coverage for the appeal query, preserving both the general
   appeal right and the detailed five-working-day procedure.

## Limitations and recommendations

- Labels were manually reviewed only for the pooled top-five candidates, so
  Recall@5 is not corpus-wide recall and the macro averages are directional.
- The evaluation has five questions from one 23-page document. It is not a
  benchmark of general university helpdesk performance.
- Chunk boundaries sometimes split lists or sentences, as seen in the
  continuation chunk `8af09b282ba7ab35`. Better structure-aware list handling
  would improve human review and retrieval context.
- No algorithm was changed for this evaluation. Before changing RRF, expand
  the manually labeled query set and consider evaluating candidate-pool size,
  RRF `k`, semantic threshold, and optional source balancing.
- A future reranking experiment should be evaluated against the same fixed
  labels and should not add raw BM25 and cosine scores directly.
