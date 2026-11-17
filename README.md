# Campus Help - Milestones 1 and 2

Milestone 1 provides a local PDF ingestion pipeline. It extracts text with
PyMuPDF, cleans layout noise without changing policy content, identifies
simple section headings, chunks text at paragraph and section boundaries, and
writes structured JSON records.
Milestone 2 adds local BM25 keyword retrieval over those JSON chunks.
Milestone 3 adds local semantic retrieval using the
`all-MiniLM-L6-v2` sentence-transformer and NumPy cosine similarity.
Milestone 4 combines BM25 and semantic candidates using Reciprocal Rank
Fusion (RRF).

## Project structure

```text
Campus Help/
├── campus_help/
│   └── ingestion/
│       ├── cleaner.py       # Conservative text normalization
│       ├── chunker.py       # Section- and paragraph-aware chunking
│       ├── extractor.py     # PyMuPDF extraction and PDF errors
│       ├── models.py        # Typed intermediate and output records
│       ├── pipeline.py      # End-to-end orchestration and JSON writing
│       └── cli.py            # Command-line entry point
│   ├── retrieval/
│       ├── engine.py         # BM25 index and search
│       ├── loader.py         # Processed JSON loader
│       ├── tokenizer.py      # Query/index tokenization
│       └── cli.py            # Search command-line demonstration
│   └── semantic/
│       ├── model.py          # Local model loading and embeddings
│       ├── storage.py        # NumPy embedding index persistence
│       ├── engine.py         # Cosine-similarity search
│       └── cli.py            # Semantic search demonstration
│   └── hybrid/
│       ├── engine.py         # RRF fusion and diagnostics
│       └── cli.py            # Hybrid search demonstration
├── data/
│   ├── input/               # Source PDFs
│   └── output/              # Generated JSON
├── tests/
│   ├── test_cleaner.py
│   ├── test_chunker.py
│   └── test_extractor.py
├── pyproject.toml
└── README.md
```

The project intentionally has no web framework, database, generative LLM, or
RAG framework dependency.

## Installation

Python 3.10+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run ingestion

```bash
python -m campus_help.ingestion.cli \
  --input data/input/student-handbook.pdf \
  --output data/output/student-handbook.json \
  --category academics
```

The output is a JSON object containing source metadata and a `chunks` array.
Each chunk includes `chunk_id`, `document_name`, `section`, `page_number`,
`category`, and cleaned `text`.

## Search processed chunks

```bash
python -m campus_help.retrieval.cli \
  --input data/output/student-handbook.json \
  --query "What is the attendance requirement?" \
  --top-k 5
```

Search returns positively scoring BM25 matches only. Empty queries, unknown
terms, and empty indexes return no results. Missing or malformed JSON files
produce an error and a non-zero command exit.

## Semantic search

Install dependencies with `python -m pip install -e ".[dev]"`. On the first
use, download `all-MiniLM-L6-v2` while online:

```bash
python -m campus_help.semantic.cli \
  --input data/output/student-handbook.json \
  --embeddings data/output/student-handbook-embeddings.npz \
  --query "How much attendance is required?" \
  --download-model
```

The command stores normalized 384-dimensional embeddings and chunk metadata in
the local NPZ file. Later searches use the cached model and index offline:

```bash
python -m campus_help.semantic.cli \
  --input data/output/student-handbook.json \
  --embeddings data/output/student-handbook-embeddings.npz \
  --query "How much attendance is required?"
```

The model must be downloaded and cached before offline use. Semantic search
returns up to five results whose cosine similarity is at least 0.2; adjust
`min_similarity` through the Python API when a different relevance threshold
is needed.

## Hybrid search

Hybrid retrieval requests ten candidates from each retriever, combines them
with RRF using `k=60`, deduplicates by `chunk_id`, and returns five results by
default:

```bash
python -m campus_help.hybrid.cli \
  --input data/output/student-handbook.json \
  --embeddings data/output/student-handbook-embeddings.npz \
  --query "What happens after a discipline violation?" \
  --top-k 5
```

Results include `bm25_rank`, `semantic_rank`, and `rrf_score`. A missing rank
is represented as `null`; raw BM25 and cosine scores are never added together.
The semantic model must be cached locally, and the embedding NPZ must exist
before the hybrid command can run.

Scanned/image-only PDFs are reported explicitly because OCR is outside this
milestone. Empty and corrupted PDFs also result in a non-zero command exit and
an explanatory log message.

## Test

```bash
python -m pytest
```
