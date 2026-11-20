# Campus Help — GitHub Handover

## Repository

- GitHub: `https://github.com/nishantxscooby/campus-help.git`
- Local workspace: `/Users/nishant/Campus Help`
- Branch: `main`

## Project purpose

Campus Help is a local extractive university-helpdesk prototype for Bennett
University. It ingests official PDFs, creates searchable chunks, retrieves
candidate passages with BM25, semantic embeddings, and RRF hybrid retrieval,
and prepares exact quotations with citations.

The system is not generative and does not use paid APIs.

## Verified repository state

At handover:

- Complete suite: 228 tests passing
- Python compilation: passing
- M6.3F targeted regressions: included in the suite
- Git remote: `origin`
- Remote URL: `https://github.com/nishantxscooby/campus-help.git`
- Remote tracking: `main`
- The answer pipeline does not enable automatic `ANSWERED` decisions

## Completed milestones

### M1

- PyMuPDF extraction
- Text cleaning
- Structure-aware chunking
- Page and PDF metadata
- Deterministic chunk IDs
- JSON serialization

### M2

- Unicode tokenization
- Rank-BM25 index
- Configurable top-K search
- Metadata-preserving results

### M3

- `all-MiniLM-L6-v2`
- 384-D embeddings
- NumPy cosine similarity
- Normalized NPZ local storage

### M4

- BM25 and semantic candidate retrieval
- RRF with `k=60`
- Candidate pool `10 + 10`
- Top-K `5`
- Deterministic tie-breaking

### M4.1

- 40-question evaluation dataset
- 32 answerable and 8 unsupported questions
- BM25, semantic, and hybrid comparison script
- Raw result and human-review documents
- Relevance judgments remain manually reviewable and partially provisional

### M5

- Exact source-unit extraction
- Source offsets and metadata provenance
- Lexical candidate scoring
- Candidate evidence selection
- Exact quotation assembly
- JSON-compatible citation drafts

### M6.1–M6.3F

- Provenance and context validation
- Question-planning and evidence-matching foundations
- Sufficiency diagnostics
- Fail-closed sufficiency pipeline
- Targeted M6.3F regressions

No M6.3G or M6.4 implementation is included.

## Architecture

```text
PDF
  -> PyMuPDF extraction
  -> cleaning and chunking
  -> processed JSON
  -> BM25 and local semantic indexes
  -> hybrid RRF retrieval
  -> source-unit extraction
  -> candidate scoring
  -> evidence selection
  -> extractive draft and citation
  -> provenance/context/sufficiency diagnostics
```

The answer package is under `campus_help/answer/`.

Important modules:

- `models.py`
- `source_units.py`
- `evidence.py`
- `assembly.py`
- `validation.py`
- `question_planning.py`
- `evidence_matching.py`
- `sufficiency.py`
- `sufficiency_pipeline.py`

## Data and generated artifacts

The active discipline PDF is:

```text
data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf
```

The processed corpus is:

```text
data/output/discipline-rules.json
```

The semantic NPZ is:

```text
data/output/discipline-rules-embeddings.npz
```

The NPZ is ignored by Git through `*.npz`. The discipline JSON and source PDFs
are repository data.

The scholarship PDF exists at `data/input/Scholarship-Policy-25-26_.pdf` but
is not ingested or embedded.

## Setup

```bash
cd "/Users/nishant/Campus Help"
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Verified interpreter:

```text
/Users/nishant/.pyenv/versions/3.12.6/bin/python
```

No environment-variable names or secret values are required by the current
implementation.

## Verification commands

```bash
/Users/nishant/.pyenv/versions/3.12.6/bin/python -m pytest
/Users/nishant/.pyenv/versions/3.12.6/bin/python \
  -m compileall -q campus_help tests
```

M4.1 evaluation:

```bash
/Users/nishant/.pyenv/versions/3.12.6/bin/python scripts/m4_1_evaluate.py
```

Controlled M4 experiments:

```bash
/Users/nishant/.pyenv/versions/3.12.6/bin/python \
  scripts/m4_controlled_experiments.py \
  --output docs/m4-controlled-experiments-results.json
```

Both evaluation scripts completed successfully. The controlled-results JSON
was regenerated and may show JSON object key-order differences from set
iteration.

## Git state and secrets

`.gitignore` excludes:

- Python caches and bytecode
- pytest cache
- virtual environments
- egg-info directories
- `.env` files
- `.npz` embedding files
- editor and OS files

No API keys, passwords, or tokens were found in project source.

Do not commit credentials or `.env` files.

## Known limitations

- OCR is not implemented.
- The processed discipline PDF is the primary verified corpus.
- M4.1 recall is not full-corpus recall.
- Human relevance labels need independent approval.
- Some chunk boundaries and PDF text are incomplete or malformed.
- M5 extraction does not reconstruct cross-chunk rules.
- M5.2 lexical scoring cannot understand negation or semantic entailment.
- Unsupported questions can still retrieve candidate text.
- M6.3 remains fail-closed and is not semantic sufficiency validation.
- Automatic `ANSWERED` decisions remain disabled.
- No FastAPI, React frontend, database, authentication, Docker, or CI exists.
- Retrieval and PDF metadata are not cross-document validated against all
  source PDFs.

## Next work

1. Complete independent M4.1 human label review.
2. Resolve extraction-defect issues without silently correcting policy text.
3. Add an approved M6.3G/M6.4 semantic sufficiency mechanism only later.
4. Add FastAPI after answer-validation semantics are stable.
5. Process additional official PDFs.
6. Add frontend integration after API contracts are finalized.
