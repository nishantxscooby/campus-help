"""Search exact page spans. Search scores select reading material only."""

from collections import defaultdict
from functools import cached_property, lru_cache
from dataclasses import dataclass, replace
from difflib import get_close_matches
import json
import logging
import re
from threading import Lock

import fitz

from ..answer.verification import _canonical_chunks
from ..ingestion.models import DocumentChunk
from ..retrieval.engine import BM25Retriever
from ..retrieval.tokenizer import tokenize
from ..semantic.engine import SemanticRetriever
from ..semantic.model import MODEL_NAME, load_model
from .tables import cell_position, grid
from ..ingestion.table_rows import extract_tables, tiered_rows
from .row_evidence import descriptors, search_text
from .library import Book
from .service import SourceUnavailable, pinned_bytes


STOP = set("""a an the this that these those my i me you they he she it its it's s if in on of about for
document documents discipline disciplinary according regarding says stated to with is are am at by as has have can could mention tell much please would should what what's who which when where how do does
did get got gets happen happens tell say says explain policy policies rules rule handbook campus university
around lead able will have gets happens meri mere mujhe tum hai hain agar campus can does use does any
student students and or between versus compare difference any some please there was were be may not
kya hai hain ka ki ke ko mein me agar aur mujhe toh se kar sakta allowed catch caught""".split())
# Search expansions only. None authorize a claim or replace text in the citation.
ALIASES = {
    "retain": "continuation", "renewal": "continuation", "renew": "continuation",
    "smoke": "cigarettes tobacco", "smoking": "cigarettes tobacco", "cigarette": "cigarettes",
    "intoxication": "intoxicants inebriated", "drunk": "inebriated alcohol",
    "daaru": "alcohol", "sharab": "alcohol", "nasha": "intoxicants",
    "ladai": "violence", "fighting": "violence", "saza": "punishment",
    "punish": "punishment authority", "rusticated": "rustication", "deadline": "within days",
}
FOLLOW = re.compile(r"^(?:and\b|what about\b|what if\b|then\b)|\b(?:it|that|they|second offence|the deadline)\b", re.I)
FACET = re.compile(r"\s+(?:and|versus|vs\.?|aur)\s+|[?;]", re.I)
NUMBERED = re.compile(r"^(?:\d+[.)]|[ivx]+\.)\s", re.I)


def focus(question):
    return [w for w in tokenize(question) if w not in STOP and len(w) > 1]


def queries(question, history):
    """Reconstruct a bounded topic from student turns, abandoning it at a new independent question."""
    overview = re.fullmatch(r"(?:which|what) ([\w-]+) are available[?.!]?",question.strip(),re.I)
    if overview:
        return [(overview[1],[])]
    if multiple := re.search(r"\b(?:two|both|2|more than one|multiple)\s+(scholarships?)\b",question,re.I):
        return [("multiple scholarships",[])]
    parts = [p.strip() for p in FACET.split(question) if focus(p)]
    if not parts:
        parts = [question]
    dependent = FOLLOW.search(question) or re.search(r"what punishment|which penalty", question, re.I)
    context = []
    if dependent:
        for prior in reversed(history):
            context[:0] = focus(prior)
            if not FOLLOW.search(prior) and not re.search(r"what punishment|which penalty", prior, re.I):
                break
    return [(part, list(dict.fromkeys(context))) for part in parts[:4]]


@dataclass(frozen=True)
class Slice:
    book: Book
    page: int
    start: int
    end: int
    text: str
    heading: str
    cell: bool
    coordinates: str = "pdf_page_text"
    confidence: float = 100
    bbox: tuple = ()
    table: dict | None = None
    chunk_id: str = ""

    def citation(self):
        return dict(title=self.book.title, document_name=self.book.source.document.document_name,
                    section=self.heading, chunk_id=self.chunk_id, coordinates=self.coordinates,
                    confidence=self.confidence, bbox=self.bbox, table=self.table, version=self.book.version, start=self.start,
                    end=self.end, exact_quotation=self.text, pdf_page_number=self.page,
                    pdf_url=f"{self.book.url}#page={self.page}")


def row_slices(book, number, tables, scanned):
    for row in descriptors(tables, scanned):
        ref = row["cells"][row["column"]-1][0]
        section = row["section_source"]
        yield Slice(book,number,ref["start"],ref["end"],ref["text"],section["text"] if section else "",
                    True,bbox=tuple(ref["bbox"]),table=row)


def page_slices(book, page):
    tables = grid(page)
    raw = page.get_text()
    cursor = 0
    spans = []
    heading = ""
    for block in page.get_text("blocks"):
        if block[6] != 0:
            continue
        value = block[4].strip()
        if not value:
            continue
        start = raw.find(value, cursor)
        if start < 0:
            continue
        end = start + len(value)
        cursor = end
        if re.fullmatch(r"Page \d+ of \d+", value, re.I):
            continue
        if 4 < len(value) < 100 and (value.isupper() or value.endswith(":")):
            heading = value
        # Narrow multi-line blocks can be table cells. Keep each intact. Join only adjacent
        # wide prose lines in reading order when the first visibly continues into the next.
        position = cell_position(tables, block[:4])
        cell = position is not None or block[2]-block[0] < page.rect.width * .48 and "\n" in value
        if spans:
            prev, rect = spans[-1]
            if (not cell and not prev.cell and prev.heading == heading and not NUMBERED.match(value)
                    and not prev.text.rstrip().endswith((".", ":", "?", ";", ")")) and prev.text != heading
                    and rect[2]-rect[0] > page.rect.width * .57 and 0 <= block[1]-rect[3] <= 10
                    and (abs(rect[0]-block[0]) < 24 or
                         (NUMBERED.match(prev.text) and 0 < block[0]-rect[0] < page.rect.width*.09))
                    and not raw[prev.end:start].strip()
                    and end-prev.start < 1400):
                start = prev.start
                block = (*tuple(fitz.Rect(rect[:4]) | fitz.Rect(block[:4])), *block[4:])
                spans.pop()
        spans.append((Slice(book, page.number+1, start, end, raw[start:end], heading, cell, bbox=tuple(block[:4]), table=position), block))
    result = [span for span, _ in spans if len(tokenize(span.text)) >= 3]
    if tables:
        result.extend(row_slices(book,page.number+1,tiered_rows(page,tables) or extract_tables(page),False))
    return result


@lru_cache(maxsize=8)
def layout_rows(book):
    data = json.loads(pinned_bytes(book.source.corpus_path, book.source.corpus_revision))
    return tuple(s for page in data["pages"] for s in row_slices(
        book,page["page"],page.get("tables",[]),page["method"]=="ocr"))


def transcript_slices(book):
    yield from layout_rows(book)
    data = json.loads(pinned_bytes(book.source.corpus_path, book.source.corpus_revision))
    for page in data["pages"]:
        heading = ""
        for r in page["regions"]:
            text = page["text"][r["start"]:r["end"]]
            first = text.splitlines()[0]
            if len(first) > 10 and first.isupper():
                heading = first
            if len(tokenize(text)) < 3 or first.startswith(("Established Under", "Address:", "Email:")):
                continue
            yield Slice(book,page["page"],r["start"],r["end"],text,heading,False,
                        "ocr_transcript" if page["method"] == "ocr" else "layout_transcript",
                        r["confidence"],tuple(r["bbox"]),chunk_id=r["chunk_id"])


@lru_cache(maxsize=1)
def local_model():
    try:
        return load_model(MODEL_NAME, local_files_only=True)
    except (ImportError, OSError, RuntimeError, ValueError):
        logging.getLogger(__name__).info("Local encoder unavailable; using BM25")
        return None


class LibrarySearch:
    def __init__(self, books, semantic):
        rows = []
        self.spans = {}
        self.vocab = set()
        for book in books:
            source = book.source
            pdf = pinned_bytes(source.pdf_path, source.document.pdf_sha256)
            if book.layout:
                passages = transcript_slices(book)
            else:
                indexed = {p.page_number for p in _canonical_chunks(source).values()}
                with fitz.open(stream=pdf, filetype="pdf") as doc:
                    passages = [s for page in sorted(indexed) for s in page_slices(book, doc[page-1])]
            for span in passages:
                row = bool(span.table and "cells" in span.table)
                key = f"{source.document.pdf_sha256}/{span.page}/{span.coordinates}/{span.start}/{int(row)}"
                rows.append(DocumentChunk(key, source.document.document_name, span.heading, span.page,
                                          "page", search_text(span)))
                self.spans[key] = span
                self.vocab.update(tokenize(search_text(span)))
        self.lexical = BM25Retriever(rows)
        self.encoder = None
        model = local_model() if semantic and rows else None
        if model is not None:
            try:
                self.encoder = SemanticRetriever.from_chunks(model, rows)
            except (RuntimeError, OSError, ValueError):
                logging.getLogger(__name__).warning("Cannot embed local page index; using BM25")
        self.lock = Lock()

    @property
    def mode(self):
        return "hybrid" if self.encoder else "bm25"

    def alternatives(self, w):
        terms = {w, *ALIASES.get(w, "").split()}
        for plural in (w + "s", w + "es"):
            if plural in self.vocab:
                terms.add(plural)
        for suffix in ("s", "ing", "ed", "ity"):
            if w.endswith(suffix) and len(w) > len(suffix) + 3 and w[:-len(suffix)] in self.vocab:
                terms.add(w[:-len(suffix)])
        if w not in self.vocab and len(terms) == 1 and len(w) >= 5:
            # Require a unique one-edit repair, including an adjacent transposition.
            plausible = []
            for other in get_close_matches(w, self.vocab_sorted, n=6, cutoff=.75):
                short, long = sorted((w, other), key=len)
                if len(long) == len(short) + 1:
                    near = any(long[:i]+long[i+1:] == short for i in range(len(long)))
                elif len(long) == len(short):
                    near = sum(a != b for a,b in zip(w,other)) == 1 or any(
                        w[:i]+w[i:i+2][::-1]+w[i+2:] == other for i in range(len(w)-1))
                else:
                    near = False
                if near:
                    plausible.append(other)
            if len(plausible) == 1:
                terms.add(plausible[0])
        return terms

    def rank(self, part, context):
        words = focus(part)
        groups = [self.alternatives(w) for w in context + words]
        if not groups:
            return []
        expanded = " ".join(sorted(set.union(*groups)))
        scores = defaultdict(float)
        similarities = {}
        ranks = [self.lexical.search(expanded, top_k=25)]
        if context:
            context_query = " ".join(sorted(set.union(*groups[:len(context)])))
            ranks.append(self.lexical.search(context_query, top_k=12))
        if self.encoder:
            with self.lock:
                try:
                    matches = self.encoder.search(" ".join(context + [part]), top_k=25) if self.encoder else []
                except (RuntimeError, ValueError, OSError):
                    logging.getLogger(__name__).warning("Local encoder failed; continuing with keyword search")
                    self.encoder = None
                    matches = []
            similarities = {r.chunk_id:r.score for r in matches}
            ranks.append(matches)
        for hits in ranks:
            for rank, hit in enumerate(hits, 1):
                scores[hit.chunk_id] += 1/(60+rank)
        overview_terms = {w.removesuffix("s") for w in words} - {"available"}
        if overview_terms and not context:
            for key, span in self.spans.items():
                if (overview_terms <= {w.removesuffix("s") for w in focus(span.book.title)}
                        and re.search(r"\bfollowing categories\b", span.text, re.I)):
                    scores[key] += .15
        candidates = []
        for key, fusion in scores.items():
            span = self.spans[key]
            tokens = set(tokenize(search_text(span)))
            if span.table and "cells" in span.table:
                # A column repeated on every row cannot identify a requested subject.
                if not any(group.intersection(tokenize(span.text)) for group in groups):
                    continue
                column_words = {w for i,h in enumerate(span.table["headers"],1)
                                if i!=span.table["column"] for w in tokenize(h)}
                if not span.book.layout and not any(group & column_words for group in groups):
                    continue
                name = " ".join(re.findall(r"\w+",span.text.casefold()))
                phrase = " ".join(re.findall(r"\w+",part.casefold()))
                exact_row = bool(re.search(r"\b"+re.escape(name)+r"\b",phrase))
                if exact_row and any(set(words).intersection(tokenize(h)) for h in span.table["headers"]):
                    fusion += .4
            hits = [bool(group & tokens) for group in groups]
            heading_tokens = set(tokenize(span.heading)) if span.book.layout else set()
            similarity = similarities.get(key, 0)
            if context and not any(hits[:len(context)]):
                continue
            # Never elevate a continuation or isolated sanction cell into an apparent rule.
            stripped = span.text.lstrip()
            listed_transcript = span.book.layout and re.match(r"^[ivxlcdm]+[.,)]\s+[|\s]*[A-Z]", stripped)
            if (stripped[:1].islower() and not NUMBERED.match(stripped) and not listed_transcript) or len(tokens) < 3:
                continue
            if "attendance" in words and "attendance" not in tokens:
                continue
            topic_groups = [g for g in groups if any(w in ALIASES for w in g)]
            if topic_groups and not any(g & tokens for g in topic_groups):
                continue
            heading_matches = sum(not hit and bool(group & heading_tokens) for hit,group in zip(hits,groups))
            coverage = (sum(hits) + .35 * heading_matches)/len(hits) if any(hits) else 0
            unresolved = any(not group.intersection(self.vocab) for group in groups)
            if not context and similarity < .48 and (coverage < .5 or (unresolved and coverage <= .5)):
                continue
            variant_hits = sum(1/(i+1) for w in context+words
                               for i, term in enumerate(ALIASES.get(w,"").split()) if term in tokens)
            score = coverage + fusion*5 + similarity*.3 + .2*variant_hits
            if span.coordinates == "ocr_transcript":
                if span.confidence < 80:
                    score -= .14
                score += .16 * len(set(words) & set(tokenize(span.heading)))
            # Prefer a readable numbered provision to a duplicate in a narrow table.
            if span.table and span.text.count("\n") > 3:
                score -= .22
            if span.heading == span.text.splitlines()[0] and len(span.text.splitlines()) == 1:
                score -= .35
            if overview_terms and overview_terms <= {w.removesuffix("s") for w in focus(span.book.title)}:
                if re.search(r"\bfollowing categories\b",span.text,re.I) and len(span.text) < 750:
                    score += 1.8
                elif re.search(r"\b(includes|categories of|offers various)\b", span.text, re.I):
                    score += .9
                elif len(tokens) < 6:
                    score -= .5
            candidates.append((score, key))
        ordered = [self.spans[key] for _, key in sorted(candidates, reverse=True)]
        # Printed tables often repeat a complete list item with a different row number
        # and break words inside the column. Compare only for selection, never for citation.
        def wording(span):
            return re.sub(r"[^\w]+", "", re.sub(r"^\d+[.)]?\s+", "", span.text.casefold()))

        readable = {(span.book, wording(span)) for span in ordered if not span.cell}
        return [span for span in ordered if not span.cell or (span.book, wording(span)) not in readable]

    @cached_property
    def vocab_sorted(self):
        return sorted(self.vocab)

    def find(self, question, history):
        parts = queries(question, history)
        lists = [self.rank(part, ctx) for part, ctx in parts]
        if parts == [("multiple scholarships",[])]:
            for span in lists[0]:
                for sentence in re.finditer(r"[^.!?]+[.!?]",span.text):
                    if re.search(r"\bmultiple\s+scholarships\b",sentence[0],re.I):
                        text = sentence[0].strip()
                        start = span.start + sentence.end()-len(sentence[0].lstrip())
                        return [replace(span,text=text,start=start,end=start+len(text))],1,1
            return [],0,1
        # For a scenario connecting conduct and a requested consequence, independently
        # retrieve both concepts without treating their co-occurrence as a mapping.
        terms = focus(question)
        if len(lists) == 1 and len(terms) == 2 and any(w.startswith(("rusticat","expuls","suspens")) for w in terms):
            lists = [self.rank(term, []) for term in terms]
        results = []
        seen = set()
        anchors = [self.alternatives(w) for w in focus(question)]
        for i in range(4):
            for hits in lists:
                if i >= len(hits):
                    continue
                span = hits[i]
                key = " ".join(span.text.casefold().split())
                # Additional sources should add a requested concept or a distinct document.
                matched = {i for i,g in enumerate(anchors) if g.intersection(tokenize(span.text))}
                previous = [r for r in results if r.book == span.book]
                adds = matched - {i for r in previous for i,g in enumerate(anchors) if g.intersection(tokenize(r.text))}
                if i and previous and not adds:
                    continue
                if i and results and not previous:
                    shared = set(tokenize(span.text))
                    if not any(len(shared & set(tokenize(r.text))) / max(1,len(shared | set(tokenize(r.text)))) > .55 for r in results):
                        continue
                if key not in seen:
                    results.append(span)
                    seen.add(key)
        return results[:5], sum(bool(hits) for hits in lists), len(lists)


@lru_cache(maxsize=4)
def cached_search(books, semantic):
    return LibrarySearch(books, semantic)


def search(question, history, books, semantic):
    # A cached index remains usable only while both independently pinned artifacts still match.
    for book in books:
        for path, pin in ((book.source.pdf_path, book.source.document.pdf_sha256),
                          (book.source.corpus_path, book.source.corpus_revision)):
            pinned_bytes(path, pin)
    try:
        engine = cached_search(books, semantic)
        results, covered, total = engine.find(question, history)
        return results, engine.mode, covered, total
    except (ValueError, IndexError, RuntimeError) as exc:
        raise SourceUnavailable from exc
