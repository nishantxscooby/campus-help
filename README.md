# Campus Help

Campus Help is a local, extractive university-helpdesk retrieval prototype for
Bennett University documents. It uses PyMuPDF, BM25, local
`all-MiniLM-L6-v2` embeddings, NumPy cosine similarity, and Reciprocal Rank
Fusion (RRF). It does not use generative LLMs or paid APIs.

## Run the local website

From the repository root, use Python 3.10+ and Node 22.12+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
npm --prefix frontend ci
npm --prefix frontend run build
python -m uvicorn campus_help.web.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. FastAPI serves the built React app and its API from the same origin. For frontend development, keep FastAPI running and start `npm --prefix frontend run dev` in another terminal. Open http://127.0.0.1:5173. Vite proxies API requests to port 8000. Local CORS allows localhost and 127.0.0.1 on port 5173.

The defaults use the bundled data. To locate the same pinned files elsewhere, set `CAMPUS_HELP_DATA_DIR=/path/to/data` before starting FastAPI, preserving the `input/` and `output/` layout. To proxy to a different backend port, run `CAMPUS_HELP_API_ORIGIN=http://127.0.0.1:8001 npm --prefix frontend run dev`. The web application requires no credentials, database, or embedding download.

`GET /health` reports process liveness. `GET /documents` lists indexed editions, availability and PDF links. `POST /ask` accepts one question of up to 800 characters.

```bash
curl http://127.0.0.1:8000/ask -H 'Content-Type: application/json' -d '{"question":"What is the deadline to file an appeal?"}'
```

The bundled handbook returns `insufficient_evidence` with reason `awaiting_review`, two authenticated page 5 excerpts and an empty verified citation list for this question. Students can open the handbook in the source library.

## Implemented milestones

- M1: PDF ingestion, cleaning, metadata-preserving chunks, and JSON output
- M2: BM25 keyword retrieval
- M3: local semantic retrieval
- M4: RRF hybrid retrieval
- M4.1: 40-question retrieval evaluation and human-review materials
- M5: source units, evidence scoring/selection, and extractive citations
- M6.1–M6.3F: provenance, context, sufficiency diagnostics, and fail-closed
  pipeline evaluation

- M6.3G preserves source-unit boundaries and citation spans.
- M6.4A authenticates candidate evidence against pinned source versions.

The website searches the discipline handbook and the 2025–26 Scholarship Policy. Answers require an authenticated, independently reviewed question binding. The bundled release contains six pending discipline facts. Students can read cited passages from both documents and see which conditions remain unresolved.

## M6.4A source authentication

`campus_help.answer.verification.verify_question_evidence` accepts the original
`ValidationContext`. The application supplies two keyword-only configuration
objects from `campus_help.answer.verification_contracts`:

- `ApprovedCorpus` pins a single document name, PDF SHA-256, SHA-256 of the
  exact processed JSON bytes (the corpus revision), local file paths, and
  expected review revision.
- `FactRegistry` holds offline approval records for a review scope. Each
  witness identifies the PDF, corpus and review revisions, UTF-8 parent-text
  digest, exact quotation and existing citation with half-open character
  offsets in the parent chunk. Unknown fact properties are represented by
  `None`; a known empty set of conditions or exceptions is an empty tuple.

The trust root is the application's independently approved configuration.
Provision expected hashes and the registry separately from request data.
Computing an expected digest from the file under examination establishes no
independent trust. This repository ships no production fact approvals or
institutional source attestation. Supply `approved_corpus=None` when pins
are unavailable; the verifier reports missing source. With a pinned corpus
and no registry, canonical evidence can still be checked.

The verifier hashes and consumes the same bytes, revalidates the draft,
compares retrieved parents to the pinned JSON, and repeats extraction on
canonical parents. Selected and registered witnesses require their complete
parent to occur unambiguously on the cited PDF page (layout whitespace may
differ). Quotation equality and offsets are always checked on the original
chunk text. Ambiguous PDF layout can therefore prevent authentication.
Page and section metadata carry source identity, not a policy relationship.

A report distinguishes canonical witnesses from references to configured
facts sharing the required witness locations and relation family. Both are
provenance diagnostics. The original question remains explicitly unresolved,
including qualifiers the existing planner cannot bind. All proof obligations
remain open. The separate M6.3D pipeline retains its fail-closed behavior.

## Project structure

```text
campus_help/
  ingestion/       PDF extraction and chunk generation
  retrieval/       BM25 index and search
  semantic/        Sentence Transformer embeddings and local NPZ storage
  hybrid/          Reciprocal Rank Fusion
  web/             FastAPI routes and controlled answer service
  answer/          Source units, evidence, assembly, and validation
data/
  input/           Source PDFs
  output/          Processed JSON and embeddings
  evaluation/      M4.1 questions and labels
frontend/          React UI, Vite build and Playwright browser tests
docs/              Retrieval evaluation and handover reports
scripts/           M4 evaluation and experiment runners
tests/             pytest suite
pyproject.toml     Package and CLI configuration
```

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
python scripts/m4_1_evaluate.py
```

Run controlled M4 experiments:

```bash
python \
  scripts/m4_controlled_experiments.py \
  --output docs/m4-controlled-experiments-results.json
```

M4.1 relevance judgments remain provisional where the report says so. Recall
is not full-corpus recall unless independently verified.

## Tests

With the Python environment active and frontend built, run the following from the repository root. The browser suite starts local servers on ports 8100 through 8106.

```bash
python -m pytest
python -m compileall -q campus_help tests
(cd frontend && npx playwright install chromium)
npm --prefix frontend run test:e2e
git diff --check
```

## Current limitations

- Scholarship search cites a pinned OCR transcript. The admission continuation table has 18 programme rows on page 4. The figures in its three enclosed CGPA cells were checked against a separate image reading. Students can inspect the original page. The application cannot confirm a renewal decision from this table.
- The discipline corpus contains known extraction defects.
- Page metadata is extraction-derived and not validated against every printed
  PDF page label.
- Unsupported questions can retrieve superficially relevant text.
- M4.1 labels require independent human verification.
- Public deployment and institutional approval of policy facts are pending.

## Independent review

The [discipline review guide](docs/discipline-review.md) links 12 pending passages to their PDF pages and documents the operator release format, review decisions, source pins and startup settings. Six focused question bindings now support independent review in the [passage release](docs/discipline-passages.json).

For the focused topics, the API looks up registered questions or reading passages directly. Case, surrounding whitespace and a final question mark are normalized for comparison. Uncertain spellings such as “restigate” prompt clarification. Rustication and debarment variants route to reading material. Only a fully reviewed question binding can yield a confirmed answer. The UI displays authenticated reading excerpts separately from verified citations. For other questions the app searches the indexed library using the local retrieval workflow below.

## Searching the indexed library

For open questions the API searches page passages from every configured PDF and returns exact native-text slices or exact slices of the pinned page transcript. The default uses BM25 and the cached local `all-MiniLM-L6-v2` encoder. The passage vectors are built in memory on first use. An unavailable encoder falls back to keyword search. Set `CAMPUS_HELP_SEARCH_MODE=bm25` for a lightweight offline run. The API reports the mode in `retrieval_mode`, also visible in source details. The older chunk NPZ remains usable by the retrieval CLI and legacy authority service.

The browser sends at most four earlier student questions. Follow-ups re-run retrieval. Search expansions and spelling suggestions affect ranking only. Authenticated reading excerpts retain the `insufficient_evidence` answer status. Table cells are shown individually. Each excerpt can be opened at its source page. A released `source_statement` can enable an exact reviewed question with a claim identical to its full parent quotation. The reviewer's scope and conflict checks are still required.

### Render and cold BM25 workers

Set `CAMPUS_HELP_SEARCH_MODE=bm25` on a memory-constrained service. A single worker can serve the built React application and API:

```bash
python -m uvicorn campus_help.web.api:app --host 0.0.0.0 --port "$PORT" --workers 1
```

Include `data/search-spans/` alongside the existing PDFs, corpora, library manifest and review configuration. The bundled release contains compressed, source-checked spans for both documents. The worker builds the small BM25 term index in memory. Library searches check the PDF, corpus and span artifact hashes. Loading the spans also validates their exact offsets against the PDF text or pinned page transcript. The scholarship layout is checked against a PDF-derived table geometry digest. Review status and answer authorization still use the existing verification path.

After changing a source edition, transcript or passage extractor, update the source pins and regenerate the span release **before starting the worker**:

```bash
python -m scripts.build_search_spans
```

The builder runs the full PDF layout extraction, re-derives scholarship table geometry, and checks citation slices. It publishes content-addressed artifacts before atomically replacing the manifest. This step has the memory cost of PDF table extraction. The shipped artifacts can be reused across worker restarts. The operator-controlled manifest, artifacts and source files must travel together.

For a custom library, build with `python -m scripts.build_search_spans --data-dir data --library /path/to/library.json --output /path/to/search-spans`. Point `CAMPUS_HELP_LIBRARY` and `CAMPUS_HELP_SPAN_MANIFEST` at their respective JSON manifests. An explicit span manifest requires a matching prepared index for every searchable document. Custom development libraries without a prepared entry retain the live extraction path. Optional sources that fail validation are listed as unavailable.

Run `python -m scripts.profile_bm25` with the dev dependencies to exercise a fresh in-process FastAPI worker on Linux or macOS. It reports application-import-to-health time, first-request latency, peak RSS in MiB and loaded numerical/model libraries. For a cold measurement, start a new Python process on each run.

### Add a document

1. Obtain the publisher's PDF, establish its identity and edition independently, and keep the expected PDF SHA-256 in operator configuration. The bundled additional-document manifest is `data/library.json`.
2. Generate the corpus with `python -m campus_help.ingestion.cli --input policy.pdf --output policy.json --category policy`. Inspect the text, document identity and page coverage. Record the exact JSON SHA-256 after inspection.
3. Create a local JSON array in a trusted manifest. Paths are relative to that manifest. For example:

   ```json
   [{"title":"Document title","version":"Published edition","pdf":"policy.pdf","corpus":"policy.json","pdf_sha256":"<reviewed PDF SHA-256>","corpus_sha256":"<reviewed JSON SHA-256>"}]
   ```

4. Set `CAMPUS_HELP_LIBRARY=/path/to/library.json` and restart FastAPI. Check `/documents` and open the listed PDF. Search checks both byte digests on each request. Additional documents have distinct PDF endpoints. A multi-document search returns reading material pending cross-document review.

### Scans, tables and numerical comparisons

The 2025–26 Scholarship Policy has 11 scanned pages with an invisible text layer. To regenerate its page transcript, install Tesseract with English language data (Homebrew: `brew install tesseract`, Debian/Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-eng`). Running the application with the bundled index does not require Tesseract.

```bash
python -m campus_help.ingestion.layout data/input/scholarship_policy_25-26.pdf data/output/scholarship-layout.json --category scholarship
```

The importer renders image-only and invisible-text pages at 300 dpi. Each region records a page, rectangle in PDF points, character interval in the transcript and lowest word confidence. Regions below 80 are flagged. Compare regions with the original page before pinning a regenerated artifact. OCR engine versions can change the transcript and its digest. Use `"layout": true` for these artifacts in the manifest. An optional edition that fails startup validation appears as unavailable.

Ruled tables use enclosed cell geometry, exact PDF-layer character intervals and matching column boundaries. A spanning cell is associated with a row only when it encloses that row’s vertical interval. The admission continuation table preserves its governing section and conditions. Its entries are unreviewed. The app can compare a student’s CGPA with a corroborated figure as conditional arithmetic and still requires independent approval for an eligibility decision. Ambiguous cells, incomplete headers and uncertain numerical readings lead back to the original page. The PDF link opens the original page. Search scores and OCR confidence cannot authorize a claim.

A native `source_statement` review may bind an exact question containing one `{value}` immediately before the unit. The comparison uses decimal arithmetic against a single explicit reviewed bound and reports only that numerical condition. Additional eligibility conditions still require review. No bundled scholarship threshold has such a release.

Run `python -m scripts.evaluate_library_reading --cases data/evaluation/scholarship-reading.json` for the additional scholarship reading checks. Run `python -m pytest tests/test_library_search.py` for real-corpus coverage, exact-offset, history and conflicting-document checks. Run `npm --prefix frontend run test:e2e` after the React build for live browser coverage.

Run `python -m scripts.evaluate_library_reading` for the six held-out page and phrase judgments. Prefix it with `CAMPUS_HELP_SEARCH_MODE=bm25` to evaluate the fallback on the same cases. The runner reports top-result relevance, coverage anywhere in the returned excerpts, total matching passages, exact PDF slices and confirmed-answer count. These are small, reproducible retrieval checks. Student satisfaction and unrestricted factual accuracy require separate human evaluation.
