"""Resolve a student's programme against published rows and read their exact evidence."""

from dataclasses import dataclass
import re

from .composition import comparison
from .row_evidence import text_of
from .search import layout_rows, search
from .service import pinned_bytes

GRADE = re.compile(
    r"\b(?:(\d+(?:\.\d+)?)\s*(cgpa|sgpa)|(cgpa|sgpa)\s*(?:(?:is|of|actually|now)\s+)*(\d+(?:\.\d+)?))\b",
    re.I,
)
SCHEME = re.compile(r"\b(admission|academic)\s+scholarship\b", re.I)
CONDITION = re.compile(r"\b(backlogs?|supplementary|ufm|disciplinary conduct)\b", re.I)
YEAR = re.compile(r"\b(20\d\d)[–/-](\d{2,4})\b")
NUMBER = r"(\d+(?:\.\d+)?)"


def numeric_bound(header, value):
    """Read one explicit CGPA bound when its direction agrees with the column heading."""
    if not re.search(r"\bCGPA\b", header, re.I) or re.search(r"\bSGPA\b", header, re.I):
        return None
    header = header.casefold()
    operators = {
        "at least": ">=",
        "at most": "<=",
        "greater than": ">",
        "less than": "<",
        "≥": ">=",
        "≤": "<=",
        ">=": ">=",
        "<=": "<=",
        ">": ">",
        "<": "<",
    }
    value = " ".join(value.casefold().split())
    if m := re.fullmatch(NUMBER + r"\s*(?:&|and)\s*(above|below)", value):
        op, limit = (">=" if m[2] == "above" else "<="), m[1]
    elif m := re.fullmatch(r"(" + "|".join(map(re.escape, operators)) + r")\s*" + NUMBER, value):
        op, limit = operators[m[1]], m[2]
    elif re.fullmatch(NUMBER, value) and ("minimum" in header or "maximum" in header):
        op, limit = (">=" if "minimum" in header else "<="), value
    else:
        return None
    if "minimum" in header and op.startswith("<") or "maximum" in header and op.startswith(">"):
        return None
    return op, limit


def normal(text):
    text = text.casefold().replace(".", " ").replace("&", " and ")
    for pattern, abbreviation in (
        (r"\bb\s*tech\b", "btech"),
        (r"\bm\s*tech\b", "mtech"),
        (r"\bartificial intelligence\b", "ai"),
        (r"\bmachine learning\b", "ml"),
        (r"\bcomputer science(?: and)? engineering\b", "cse"),
    ):
        text = re.sub(pattern, abbreviation, text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def programme_aliases(label):
    label_text = normal(label.split("(")[0])
    aliases = {normal(label), label_text}
    aliases.update(normal(a) for a in re.findall(r"\(([A-Z]{2,6})\)", label))
    if label_text.startswith("btech "):
        suffix = label_text.removeprefix("btech ")
        aliases.add(suffix)
        if len(suffix.split()) > 1:
            initials = "".join(w[0] for w in suffix.split() if w not in {"and", "of"})
            aliases.update((initials, "btech " + initials))
    return aliases


def resolve(text, labels):
    """Return candidates and whether an unrecognised specialisation prevents a match."""
    aliases = {label: programme_aliases(label) for label in labels}
    q = normal(text)
    terms = {alias for names in aliases.values() for alias in names}
    starts = {alias.split()[0] for alias in terms if alias}
    words = q.split()
    idx = next((i for i, w in enumerate(words) if w in starts), None)
    if idx is None:
        return [], False
    stop = set(
        "what which need needs require requires required have has cgpa sgpa scholarship for is with will can under in my and does do if student course programme program".split()
    )
    aliases_here = [alias for alias in terms if words[idx : idx + len(alias.split())] == alias.split()]
    longest = max(aliases_here, key=lambda a: len(a.split()), default="")
    after = words[idx + len(longest.split()) :]
    qualifier = (
        len(after) > 1
        and after[0] in {"and", "with", "in"}
        and not after[1][0].isdigit()
        and after[1] not in {"my", "i", "a", "an", "no", "one", "cgpa", "sgpa", "what", "scholarship"}
    )
    if longest and (not after or after[0] in stop or after[0][0].isdigit()) and not qualifier:
        exact = [label for label, names in aliases.items() if longest in names]
        return exact, len(exact) != 1 or "not" in words[max(0, idx - 2) : idx]
    end = idx + 1
    while end < len(words) and not words[end][0].isdigit() and words[end] not in stop:
        end += 1
    specific = set(words[idx:end]) - {"btech", "bachelor", "of", "master", "integrated"}
    candidates = [
        label
        for label, names in aliases.items()
        if specific and any(specific.intersection(alias.split()) for alias in names)
    ]
    return candidates, True


@dataclass
class Student:
    programme: str = ""
    options: tuple = ()
    ambiguous: bool = False
    grade: str = ""
    unit: str = ""
    scheme: str = ""
    year: str = ""
    condition: str = ""


def interpret(turns, labels):
    state = Student()
    active = False
    for index, text in enumerate(turns):
        choices, ambiguous = resolve(text, labels)
        scheme = SCHEME.search(text)
        if active and not scheme:
            scheme = re.fullmatch(
                r"(?:the |it.s |mine is |my scheme is )?(academic|admission)(?: one)?[.!]?",
                text.strip(),
                re.I,
            )
        grade = list(GRADE.finditer(text))
        condition = CONDITION.search(text)
        about = re.search(r"\b(scholarship|cgpa|sgpa|renewal)\b", text, re.I)
        if re.search(r"\bmy (?:course|programme|program) is\b", text, re.I) and not choices:
            ambiguous = True
        programme_turn = (choices or ambiguous) and re.match(
            r"(?:what about|my (?:course|programme|program) is|no,? i mean)", text, re.I
        )
        if not (
            about
            or programme_turn
            and (active or index == 0)
            or active
            and (choices or ambiguous or scheme or grade or condition)
        ):
            active, state = False, Student()
            continue
        if re.search(r"\b(?:available|hold two|two scholarships|both scholarships)\b", text, re.I):
            active, state = False, Student()
            continue
        active = True
        if (
            re.search(r"\b(?:my (?:course|programme|program) is|i mean)\b", text, re.I)
            and not choices
            and not grade
            and not scheme
        ):
            ambiguous = True
        if choices or ambiguous:
            state.programme = choices[0] if len(choices) == 1 and not ambiguous else ""
            state.options, state.ambiguous = tuple(choices), ambiguous
        if grade:
            m = grade[-1]
            state.grade, state.unit = m[1] or m[4], (m[2] or m[3]).upper()
        if scheme:
            state.scheme = scheme[1].lower()
        elif other := re.search(
            r"\b(?:on|hold|have|receive) (?:an? |the )?([\w-]+) scholarship\b", text, re.I
        ):
            if other[1].lower() not in {"my", "the", "a", "one", "this"}:
                state.scheme = other[1].lower()
        if condition:
            state.condition = condition[0].lower()
        if year := YEAR.search(text):
            state.year = year[1] + "–" + year[2][-2:]
    return state


def row_response(question, history, books):
    candidates = [book for book in books if book.layout]
    if not candidates:
        return None
    for book in candidates:
        pinned_bytes(book.source.pdf_path, book.source.document.pdf_sha256)
        pinned_bytes(book.source.corpus_path, book.source.corpus_revision)
    rows = [
        s
        for book in candidates
        for s in layout_rows(book)
        if re.search(r"\bprogram(?:me)?\b", s.table["headers"][0], re.I)
        and any("CGPA" in h.upper() for h in s.table["headers"][1:])
    ]
    if not rows:
        return None
    labels = {text_of(s.table["cells"][0]) for s in rows}
    state = interpret([*history, question], sorted(labels))
    if not (state.programme or state.ambiguous or state.scheme):
        return None
    if not (state.programme or state.ambiguous) and not state.grade:
        return None
    selected = [s for s in rows if text_of(s.table["cells"][0]) == state.programme]
    if state.ambiguous:
        choices = "; ".join(state.options[:5])
        return (
            "I couldn’t match that specialisation to one published programme. "
            + (
                f"Which exact programme appears on your offer letter? The table lists {choices}."
                if choices
                else "What is the exact programme name on your offer letter?"
            )
        ), []
    if not selected and not state.programme:
        return (
            f"I have your {state.scheme} scholarship and {state.grade} {state.unit}. Which programme are you enrolled in?",
            [],
        )
    if len(selected) != 1:
        return (
            "Several published rows could apply. Which document and edition govern your scholarship?",
            [],
        )
    (span,) = selected
    book = span.book
    if state.year and state.year != book.version:
        return (
            f"The indexed edition is {book.version}. I couldn’t establish the requirement for {state.year}.",
            [],
        )
    title = " ".join(span.heading.lower().split())
    if state.scheme and state.scheme + " scholarship" not in title:
        # Re-retrieve the separately named scheme; never use the admission table as its threshold.
        matches, _, _, _ = search(
            f"{state.scheme} scholarship performance criteria {state.programme}", [], (book,), False
        )
        matches = [
            s
            for s in matches
            if not s.table and state.scheme + " scholarship" in (s.text + " " + s.heading).lower()
        ]
        message = (
            f"I have {state.programme}"
            + (f" and {state.grade} {state.unit}" if state.grade else "")
            + ". The admission continuation table doesn’t establish eligibility for your scholarship scheme."
        )
        if any("top 10%" in s.text and "provided" in s.text for s in matches):
            message += " The Academic Scholarship passage also ties the award to your rank within the programme."
        return message, matches
    if "admission scholarship" not in title:
        return (
            f"I found a row for {state.programme}. Check the governing section before using the threshold.",
            [span],
        )
    index = next(i for i, h in enumerate(span.table["headers"]) if "cgpa" in h.lower())
    cell = span.table["cells"][index]
    value = text_of(cell)
    answer = f"The Admission Scholarship continuation row for {state.programme} lists “{value}” under {span.table['headers'][index]}."
    reliable = (
        len(cell) == 1
        and not span.table["notes"]
        and "as outlined below" in " ".join(r["text"].lower() for r in span.table["context"])
        and (not span.table["scanned"] or cell[0].get("image_agrees") is True)
    )
    bound = numeric_bound(span.table["headers"][index], value)
    if not reliable or not bound:
        answer += " I couldn’t verify the numerical reading. Check the original cell before using it."
    elif state.grade and state.unit == "CGPA":
        op, limit = bound
        fits = comparison(state.grade, limit, op)
        if op == ">=":
            answer += f" Your {state.grade} CGPA is {'at or above' if fits else 'below'} that figure."
        else:
            answer += f" Your {state.grade} CGPA {'meets' if fits else 'does not meet'} that numerical condition ({op} {limit})."
    elif state.unit == "SGPA":
        answer += f" Your {state.grade} SGPA can’t be compared directly with a CGPA requirement."
    context = " ".join(r["text"].lower() for r in span.table["context"])
    if "no backlogs or supplementary exams" in context:
        if state.condition in {"backlog", "backlogs", "supplementary"}:
            answer += " The same provision specifies “no backlogs or supplementary exams”."
        elif state.scheme == "admission" and "disciplinary conduct" in context and "ufm" in context:
            answer += " The other checks include backlogs, supplementary exams, unfair means and disciplinary conduct."
    if not state.scheme:
        answer += " Is yours the Admission Scholarship, the Academic Scholarship, or another scheme?"
    return answer, [span]
