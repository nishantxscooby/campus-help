# Campus Help

Campus Help is a local, extractive university-helpdesk retrieval prototype for
Bennett University documents. It uses PyMuPDF, BM25, local
`all-MiniLM-L6-v2` embeddings, NumPy cosine similarity, and Reciprocal Rank
Fusion (RRF). It does not use generative LLMs or paid APIs.

## Implemented milestones

- M1: PDF ingestion, cleaning, metadata-preserving chunks, and JSON output
- M2: BM25 keyword retrieval
- M3: local semantic retrieval
- M4: RRF hybrid retrieval
- M4.1: 40-question retrieval evaluation and human-review materials
- M5: source units, evidence scoring/selection, and extractive citations
- M6.1–M6.3F: provenance, context, sufficiency diagnostics, and fail-closed
  pipeline evaluation

Automatic `ANSWERED` decisions are not enabled.

## Project structure

```text
campus_help/
  ingestion/       PDF extraction and chunk generation
  retrieval/       BM25 index and search
  semantic/        Sentence Transformer embeddings and local NPZ storage
  hybrid/          Reciprocal Rank Fusion
  answer/          Source units, evidence, assembly, and validation
data/
  input/           Source PDFs
  output/          Processed JSON and embeddings
  evaluation/      M4.1 questions and labels
docs/              Retrieval evaluation and handover reports
scripts/           M4 evaluation and experiment runners
tests/             pytest suite
pyproject.toml     Package and CLI configuration
```

## Installation

Python 3.10 or newer is required.

```bash
cd "/Users/nishant/Campus Help"
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

The environment currently used for verification is:

```text
/Users/nishant/.pyenv/versions/3.12.6/bin/python
```

No environment variables or secrets are required for the existing CLI modules.
The `.env` files are ignored. The Sentence Transformer model must be downloaded
and cached before semantic or hybrid offline use.

## PDF ingestion

```bash
python -m campus_help.ingestion.cli \
  --input data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf \
  --output data/output/discipline-rules.json \
  --category discipline
```

## BM25 search

```bash
python -m campus_help.retrieval.cli \
  --input data/output/discipline-rules.json \
  --query "How can a student appeal a disciplinary punishment?" \
  --top-k 5
```

## Semantic search

```bash
python -m campus_help.semantic.cli \
  --input data/output/discipline-rules.json \
  --embeddings data/output/discipline-rules-embeddings.npz \
  --query "How can a student appeal a disciplinary punishment?" \
  --top-k 5
```

Use `--download-model` on the first run if the model is not already cached.

## Hybrid search

```bash
python -m campus_help.hybrid.cli \
  --input data/output/discipline-rules.json \
  --embeddings data/output/discipline-rules-embeddings.npz \
  --query "How can a student appeal a disciplinary punishment?" \
  --top-k 5
```

Hybrid retrieval uses:

- Candidate pool: 10 BM25 and 10 semantic chunks
- RRF constant: `k=60`
- Semantic threshold: `0.2`
- Default output: 5 chunks

## Evaluation

Run M4.1:

```bash
/Users/nishant/.pyenv/versions/3.12.6/bin/python scripts/m4_1_evaluate.py
```

Run controlled M4 experiments:

```bash
/Users/nishant/.pyenv/versions/3.12.6/bin/python \
  scripts/m4_controlled_experiments.py \
  --output docs/m4-controlled-experiments-results.json
```

M4.1 relevance judgments remain provisional where the report says so. Recall
is not full-corpus recall unless independently verified.

## Tests

```bash
python -m pytest
/Users/nishant/.pyenv/versions/3.12.6/bin/python -m pytest
/Users/nishant/.pyenv/versions/3.12.6/bin/python \
  -m compileall -q campus_help tests
```

Verified baseline:

- 228 tests passing
- Python compilation passing
- 6 existing PyMuPDF/SWIG deprecation warnings

## Current limitations

- OCR is not implemented.
- Scholarship PDF is not ingested or embedded.
- The discipline corpus contains known extraction defects.
- Page metadata is extraction-derived and not validated against every printed
  PDF page label.
- Unsupported questions can retrieve superficially relevant text.
- M4.1 labels require independent human verification.
- No FastAPI, React frontend, database, authentication, or deployment setup
  exists.
