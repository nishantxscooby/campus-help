"""FastAPI entry point for the local student policy desk."""

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ..answer.verification_contracts import ApprovedCorpus, FactRegistry
from .passages import PassageRelease, authenticate, locate, validate_catalog
from ..answer.verification import _canonical_chunks
from .composition import compose, reviewed_calculation
from .library import inventory
from .eligibility import row_response
from .row_evidence import citations as reading_citations
from .search import focus, queries, search
from .reviews import load_release
from .service import PolicyDesk, SourceUnavailable, bundled_corpus, pinned_bytes


ROOT = Path(__file__).resolve().parents[2]
PDF_URL = "/documents/handbook/pdf"
REFUSALS = {
    "unsupported_document": "Scholarship policy is outside the indexed collection. This desk searches the discipline handbook.",
    "possible_typo": "Did you mean rustication? The passages below list a possible penalty. Which incident are you asking about?",
    "penalty_mapping": "I found a passage about rustication. These excerpts do not establish which outcome applies to your incident.",
    "comparison": "The passages concern two different settings. The debar passage concerns committee membership. I found no student debarment definition to compare.",
    "student_debarment": "I found no student debarment rule in the indexed discipline handbook. The occurrence below concerns a committee member. Are you asking about exam eligibility?",
    "related_only": "I found a related passage, but it does not verify every detail in your question.",
    "clarify_appeal": "Are you asking who reviews a penalty, or when to file an appeal?",
    "clarify_hostel": "Which hostel rule or incident do you mean? Different provisions address different conduct.",
    "clarify_penalty": "Which conduct or penalty are you asking about?",
    "source_context": "The available passage needs more context to support an answer.",
    "unsupported_or_ambiguous": "I couldn’t verify that question in the handbook. Try asking about one specific policy or procedure.",
    "no_evidence": "I couldn’t find enough evidence in the handbook to answer that question.",
    "awaiting_review": "This policy hasn’t been independently reviewed for answers yet. You can consult the source document directly.",
    "incomplete_proof": "The reviewed evidence doesn’t establish all the details of your question.",
}


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    history: list[Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=800)]] = Field(default_factory=list, max_length=4)
    question: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=800)]


class Citation(BaseModel):
    document_name: str
    title: str
    section: str
    pdf_page_number: int
    chunk_id: str
    coordinates: Literal["parent_chunk", "pdf_page_text", "ocr_transcript", "layout_transcript"] = "parent_chunk"
    start: int
    end: int
    exact_quotation: str
    pdf_url: str


class ReadingCitation(Citation):
    confidence: float | None = None
    bbox: tuple = ()
    table: dict | None = None
    version: str = ""


class AskResponse(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    reason: str
    message: str
    citations: list[Citation]
    excerpts: list[ReadingCitation] = []
    retrieval_mode: Literal["hybrid", "bm25"] | None = None


class Document(BaseModel):
    status: str = "indexed"
    version: str
    pdf_sha256: str
    title: str
    document_name: str
    pdf_url: str


class Health(BaseModel):
    status: Literal["ok"]


def create_app(
    *, corpus: ApprovedCorpus | None = None, registry: FactRegistry | None = None,
    title: str = "Students’ Discipline and Conduct Rules",
) -> FastAPI:
    data_dir = Path(os.environ.get("CAMPUS_HELP_DATA_DIR", ROOT / "data"))
    source = corpus or bundled_corpus(data_dir)
    catalog = None
    trusted_release = False
    if source.document == bundled_corpus(ROOT / "data").document:
        catalog = PassageRelease.model_validate_json((ROOT / "docs/discipline-passages.json").read_bytes())
    release_path = os.getenv("CAMPUS_HELP_REVIEW_FILE")
    release_digest = os.getenv("CAMPUS_HELP_REVIEW_SHA256")
    if release_path is not None or release_digest is not None:
        if not release_path or not release_digest or registry is not None:
            raise ValueError("Configure one pinned review release")
        data = pinned_bytes(Path(release_path), release_digest)
        if json.loads(data).get("format") == "reviewed-passages-v1":
            catalog = PassageRelease.model_validate_json(data)
            trusted_release = True
        else:
            source, registry = load_release(Path(release_path), release_digest, source)
    if catalog:
        validate_catalog(catalog, source)
    manifest = os.getenv("CAMPUS_HELP_LIBRARY")
    if manifest is None and corpus is None and (data_dir / "library.json").is_file():
        manifest = data_dir / "library.json"
    collection = inventory(source, title, manifest)
    books = tuple(book for book in collection if not book.unavailable)
    app = FastAPI(title="Campus Help", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @lru_cache(maxsize=1)
    def desk() -> PolicyDesk:
        return PolicyDesk(source, registry, semantic_index=os.getenv("CAMPUS_HELP_SEMANTIC_INDEX"))

    @app.exception_handler(SourceUnavailable)
    async def source_unavailable(request: Request, exc: SourceUnavailable):
        return JSONResponse({"detail": "The policy source is unavailable. Please try again later."}, status_code=503)

    @app.exception_handler(RequestValidationError)
    async def invalid_question(request: Request, exc: RequestValidationError):
        return JSONResponse({"detail": "Send one question between 1 and 800 characters."}, status_code=422)

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        logging.getLogger(__name__).exception("Policy service error")
        return JSONResponse({"detail": "Campus Help could not complete this request."}, status_code=500)

    @app.get("/health", response_model=Health)
    def health():
        return Health(status="ok")

    @app.get("/documents", response_model=list[Document])
    def documents():
        result = []
        for book in collection:
            if not book.unavailable:
                pinned_bytes(book.source.pdf_path, book.source.document.pdf_sha256)
                pinned_bytes(book.source.corpus_path, book.source.corpus_revision)
            result.append(Document(title=book.title, document_name=book.source.document.document_name,
                                   status="unavailable" if book.unavailable else "indexed", pdf_url=book.url, version=book.version, pdf_sha256=book.source.document.pdf_sha256))
        return result

    @app.get(PDF_URL, response_class=Response)
    def handbook():
        return Response(pinned_bytes(source.pdf_path, source.document.pdf_sha256), media_type="application/pdf")

    @app.get("/documents/{identity}/pdf", response_class=Response)
    def additional_pdf(identity: str):
        for book in books[1:]:
            if book.source.document.pdf_sha256 == identity:
                return Response(pinned_bytes(book.source.pdf_path, identity), media_type="application/pdf")
        raise HTTPException(status_code=404, detail="Unknown indexed document")

    @app.post("/ask", response_model=AskResponse)
    def ask(payload: AskRequest):
        facets = queries(payload.question, payload.history)
        contextual = any(context for _, context in facets)
        if catalog:
            cards, route = locate(payload.question, catalog)
            # Keep reviewed bindings and narrow clarifications. Open-ended scenarios
            # go through library search even when they mention a registered topic.
            remaining = set(focus(payload.question)) - {"punishment", "punishments", "penalty", "penalties", "incident"}
            if route == "penalty_mapping" or (route == "clarify_penalty" and (remaining or payload.history)):
                route = ""
            if route == "clarify_hostel" and remaining - {"hostel", "break", "breaking"}:
                route = ""
            if len(facets) > 1 and route not in {"exact", "comparison", "clarify_appeal"}:
                route = ""
            if route == "unsupported_document":
                requested = [b for b in collection if "scholarship" in b.title.casefold()]
                if requested and all(b.unavailable for b in requested):
                    return AskResponse(status="insufficient_evidence", reason="unavailable_document",
                                       message="The indexed copy of the scholarship policy is unavailable.", citations=[])
                if requested:
                    route = ""
            if contextual or (len(books)>1 and route == "clarify_penalty" and "scholarship" in payload.question.lower()):
                route = ""
            if route:
                excerpts = []
                try:
                    pdf = pinned_bytes(source.pdf_path, source.document.pdf_sha256)
                    chunks = _canonical_chunks(source)
                    for card in cards:
                        authenticate(card, pdf, chunks)
                        for span in card.witnesses:
                            chunk = chunks.get(span.chunk_id)
                            excerpts.append(ReadingCitation(
                                title=title, document_name=source.document.document_name,
                                chunk_id=span.chunk_id or "", section=chunk.section if chunk else "",
                                coordinates="parent_chunk" if chunk else "pdf_page_text",
                                pdf_page_number=span.page, start=span.start, end=span.end,
                                exact_quotation=span.quotation, pdf_url=f"{PDF_URL}#page={span.page}",
                            ))
                except (IndexError, KeyError, ValueError) as exc:
                    raise SourceUnavailable from exc
                if route in {"exact", "numeric"}:
                    if trusted_release and cards[0].status == "APPROVED" and (len(books) == 1 or title.casefold() in payload.question.casefold()):
                        answer = reviewed_calculation(payload.question,cards[0]) if route == "numeric" else cards[0].claim
                        if answer:
                            return AskResponse(status="answered", reason="reviewed_passage", message=answer,
                                               citations=excerpts)
                    route = "awaiting_review" if cards[0].status == "PENDING_REVIEW" else "related_only"
                return AskResponse(status="insufficient_evidence", reason=route, message=REFUSALS[route],
                                   citations=[], excerpts=excerpts)
        eligibility = row_response(payload.question,payload.history,books)
        if eligibility:
            message, spans = eligibility
            return AskResponse(status="insufficient_evidence",reason="table_reading",message=message,
                               citations=[],excerpts=reading_citations(spans))
        bound_authority = registry is not None and any(
            fact.object and fact.object.casefold() in payload.question.casefold() for fact in registry.facts
        )
        legacy_request = registry is not None and (bound_authority or payload.question.startswith("Who is authorized to "))
        if not legacy_request or len(books) > 1 or contextual:
            # Explicit document titles narrow a single-subject query. Mixed questions
            # still search the complete collection.
            search_books = books
            if len(facets) == 1:
                question_terms = {word.removesuffix("s") for word in focus(payload.question)}
                named = tuple(b for b in books if any(word.removesuffix("s") in question_terms
                                                       for word in focus(b.title)))
                if named:
                    search_books = named
            spans, mode, covered, total = search(payload.question, payload.history, search_books,
                                 os.getenv("CAMPUS_HELP_SEARCH_MODE", "auto") != "bm25")
            if spans:
                message = compose(payload.question, spans, contextual, covered, total)
                return AskResponse(status="insufficient_evidence", reason="reading_material", message=message,
                                   citations=[], excerpts=reading_citations(spans), retrieval_mode=mode)
            subject = next((b.title for b in collection if b.unavailable and
                            set(focus(b.title)) & set(focus(payload.question))), None)
            missing = (f"I couldn’t locate an attendance requirement in {search_books[0].title}."
                       if "attendance" in focus(payload.question) and len(search_books) == 1 else
                       "I couldn’t locate a supporting passage in the indexed documents. Which rule or incident do you mean?")
            return AskResponse(status="insufficient_evidence", reason="no_evidence", citations=[],
                               message=f"{subject} is currently unavailable for search." if subject else missing,
                               retrieval_mode=mode)
        decision = desk().ask(payload.question)
        if catalog and decision.reason == "unsupported_or_ambiguous":
            return AskResponse(status="insufficient_evidence", reason="no_evidence",
                               message=REFUSALS["no_evidence"], citations=[])
        witness = decision.witness
        if witness is None:
            return AskResponse(status="insufficient_evidence", reason=decision.reason,
                               message=REFUSALS[decision.reason], citations=[])
        citation = witness.citation
        return AskResponse(status="answered", reason=decision.reason, message="", citations=[Citation(
            title=title, document_name=citation.document_name, section=citation.section,
            pdf_page_number=citation.pdf_page_number, chunk_id=citation.chunk_id,
            start=citation.source_span.start, end=citation.source_span.end, exact_quotation=witness.exact_quotation,
            pdf_url=f"{PDF_URL}#page={citation.pdf_page_number}",
        )])

    dist = ROOT / "frontend" / "dist"
    if (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


app = create_app()
