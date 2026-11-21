# Campus Help — GitHub Handover

## Repository

- GitHub: `https://github.com/nishantxscooby/campus-help.git`
- Working branch: `feature/m6-4-factual-verification`

## Project purpose

Campus Help is a local extractive university-helpdesk prototype for Bennett
University. It ingests official PDFs, creates searchable chunks, retrieves
candidate passages with BM25, semantic embeddings, and RRF hybrid retrieval,
and prepares exact quotations with citations.

The system is not generative and does not use paid APIs.

## Verified repository state

The M6.4A baseline passed 297 Python tests before the web MVP. The website uses the pinned discipline corpus with an empty production fact registry. The browser tests use live FastAPI servers. The positive API test uses a separate synthetic PDF and registry.

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

M6.3G repaired source boundaries. M6.4A added canonical provenance checks and immutable review contracts. The web MVP adds a narrow authority-question check after authentication.

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

The 2025–26 Scholarship Policy is indexed from `data/input/scholarship_policy_25-26.pdf`. The pinned page transcript is `data/output/scholarship-layout.json`; its operator manifest is `data/library.json`. The replacement PDF retains the same eleven rendered pages as the earlier scan.

## Running and verifying the MVP

Follow the local website and test commands in [README.md](README.md). The bundled worker loads source-checked search spans from `data/search-spans/`. Rebuild that release after changing the sources or extraction logic. The README includes the Render BM25 configuration. The web entry point is `campus_help.web.api:app`. Open questions search both indexed documents using local hybrid retrieval with a BM25 fallback. The authority service checks selected evidence against the pinned JSON and PDF. Source files that fail digest checks produce a service error. The CLI also supports semantic and hybrid retrieval.

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

- Scholarship OCR regions are searchable. The page 4 index retains 18 programme rows, both headers, the enclosing vertical range of shared cells, and the admission continuation conditions. The B. Tech AI row has a separate numerical cell. Programme aliases and corrected CGPA values are resolved from bounded student turns. The UI labels row excerpts and numerical comparisons as unreviewed. The Academic Scholarship on page 5 has separate conditions.
- The processed discipline PDF is the primary verified corpus.
- M4.1 recall is not full-corpus recall.
- Human relevance labels need independent approval.
- Some chunk boundaries and PDF text are incomplete or malformed.
- M5 extraction does not reconstruct cross-chunk rules.
- M5.2 lexical scoring cannot understand negation or semantic entailment.
- Unsupported questions can still retrieve candidate text.
- M6.3 remains fail-closed and is not semantic sufficiency validation.
- The web service supports both the single authority template and reviewed question bindings with exact source spans.

## Remaining before public use

Obtain independent review of the source version, governing scope, exceptions and exact witnesses before provisioning university facts. Exercise approved questions and nearby counterexamples against that registry. A public release also needs an operating environment for the API and built assets. The local workflow uses loopback HTTP.

## Review release handover

The [review guide](docs/discipline-review.md) and [source manifest](docs/discipline-review.json) cover two authority passages and ten conduct list entries. None passes the whole-parent authority template. The operator can load a compatible reviewed release with the paired file and digest settings. Recheck all witnesses after corpus changes. Live browser fixtures exercise approval, refusal, invalid citations and stale sources independently of the university corpus.

The focused release covers the written appeal deadline, major and minor review authority, Category I rustication, committee-member eligibility and gambling under Category II. All six are pending. The [review instructions](docs/discipline-review.md#enable-the-first-reviewed-appeal-answer) include activation and a negative control.

Open questions now use the general library search described in the README. BM25 runs locally and reciprocal rank fusion uses a cached encoder when available. The six university passage records remain pending. Scholarship citations identify the original PDF page and offsets in the pinned OCR transcript. See the README to regenerate and validate the index. Real browser coverage includes sending a prior student question to resolve a follow-up and opening page-specific sources.
