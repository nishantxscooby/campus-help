"""Source-bound reading guidance and comparisons. OCR never supplies an approved operand."""
from decimal import Decimal
import re
from .row_evidence import text_of

GRADE = re.compile(r"(?:(\d+(?:\.\d+)?)\s*(CGPA|SGPA|%)|(CGPA|SGPA)\s*(?:of\s+)?(\d+(?:\.\d+)?))", re.I)


def comparison(value, limit, operator):
    a,b = Decimal(value),Decimal(limit)
    return {">": a>b, ">=": a>=b, "<": a<b, "<=": a<=b}[operator]


BOUND = re.compile(r"(at least|at most|more than|less than|greater than|>=|<=|>|<)\s*(\d+(?:\.\d+)?)\s*(CGPA|SGPA|%|credits|working days|calendar days)(?!\w)", re.I)
OPERATORS = {"at least":">=", "at most":"<=", "more than":">", "greater than":">", "less than":"<"}


def reviewed_calculation(question, card):
    """Only called after authentication and independent approval of the complete question template."""
    for pattern in card.questions:
        if pattern.count("{value}") != 1:
            continue
        before,after = pattern.split("{value}")
        query = re.fullmatch(re.escape(before) + r"(\d{1,4}(?:\.\d{1,3})?)" + re.escape(after), question, re.I)
        if not query:
            continue
        # A number in a disqualification, exception, example or second clause
        # has no implicit direction of eligibility. Accept one affirmative requirement.
        requirement = re.fullmatch(
            r"(?:The |An? )?[A-Za-z][A-Za-z '\-]*? requires? (" + BOUND.pattern + r")\.",
            " ".join(card.claim.split()), re.I,
        )
        if not requirement or re.search(
                r"\b(not|no|except|unless|waived|instead|if|without|ineligible|disqualification)\b",
                card.claim, re.I):
            return None
        op, limit, unit = requirement.groups()[1:]
        if not re.match(r"\s*" + re.escape(unit) + r"(?!\w)", after, re.I):
            return None
        symbol = OPERATORS.get(op.lower(),op)
        fits = comparison(query[1],limit,symbol)
        return (f"{query[1]} {unit} {'meets' if fits else 'does not meet'} the numerical condition "
                f"({symbol} {limit} {unit}). This comparison covers only that condition.")
    return None


def compose(question, spans, contextual, covered, total):
    q = question.casefold()
    first = spans[0]
    seen = {}
    for span in spans:
        clause = " ".join(span.text.casefold().split())
        affirm = re.sub(r"\b(may|must|shall|can) not\b", r"\1", clause)
        negative = affirm != clause
        if affirm in seen and seen[affirm] != negative:
            return "The cited passages give opposite directions about the same action. I couldn’t verify which one applies."
        seen[affirm] = negative
    titles = list(dict.fromkeys(span.book.title for span in spans))
    if len(titles) > 1:
        return ("I found passages in " + " and ".join(titles) +
                ". Each citation has its own scope. I couldn’t verify a joint rule for your situation.")
    if first.table and "cells" in first.table:
        label = text_of(first.table["cells"][first.table["column"]-1])
        return f"I found the row for {label} in {first.book.title}. Its column headings and values are shown together."
    evidence = " ".join(" ".join(s.text.casefold().split()) for s in spans)
    grade = GRADE.search(question)
    if first.coordinates == "ocr_transcript":
        if "multiple scholarships" in evidence and re.search(r"\b(two|both|multiple|2|more than one)\b",q):
            return "The passage addresses students who qualify for more than one scholarship."
        year = re.search(r"\b(20\d{2})(?:\s*[-–/]\s*(\d{2,4}))?\b", question)
        edition = re.fullmatch(r"(20\d{2})[-–/](\d{2,4})",first.book.version)
        if year and edition and (year[1] != edition[1] or year[2] and year[2][-2:] != edition[2][-2:]):
            return f"The indexed edition is {first.book.version}. I can’t establish which rules applied in {year[0]}."
        if "attendance" in q and "attendance" not in evidence:
            return "I couldn’t establish an attendance threshold from the cited material."
        if grade and all(t in evidence for t in ("program-specific cgpa","no backlogs","supplementary","unfair","disciplinary conduct")):
            return (f"For {first.book.version}, the continuation passage calls for a programme-specific CGPA "
                    "and lists backlogs, supplementary exams, unfair means and disciplinary conduct as other checks. "
                    f"I can’t confirm eligibility from {grade[1] or grade[4]} {(grade[2] or grade[3]).upper()} alone. "
                    "Which programme and scholarship scheme apply?")
        if grade:
            value = grade[1] or grade[4]
            unit = (grade[2] or grade[3]).upper()
            return (f"I can’t confirm eligibility from {value} {unit} alone. "
                    f"The cited {first.book.version} passage lists the criteria to check. "
                    + ("Check your programme against its row in the original table." if
                       re.search(r"academic scholarship|admission scholarship", q) else
                       "Which programme and scholarship scheme are you on?"))
        if "sgpa" in q and "cgpa" in evidence:
            return "The cited text uses CGPA. I couldn’t establish that SGPA can be substituted."
        if "backlog" in q and "no backlogs" in evidence:
            return "The continuation provision specifically mentions backlogs and supplementary exams. Check the full set of conditions below."
        if "program-specific cgpa" in evidence and re.search(r"renew|continu|retain|semester",q):
            return "The continuation provision sets programme-specific conditions. Check the criteria and the programme table on the cited page."
        if "following categories" in evidence:
            return f"The {first.book.version} policy lists these options. Which one would you like to check?"
        return f"Here is the relevant wording from the {first.book.version} {first.book.title}. Check the original page for the table and any qualifying notes."
    consequence = re.search(r"punish|penalt|rusticat|offen[cs]e|what happens|catch|caught",q)
    if grade:
        return "I couldn’t verify an applicable threshold and its conditions for your figure. Which programme and requirement are you asking about?"
    if consequence:
        reply = ("I found separate passages for the terms in your question. I couldn’t establish that one leads to the other."
                 if len({s.page for s in spans}) > 1 and re.search(r"lead to|result in", q)
                 else "I found a related provision. I couldn’t verify which penalty applies to your situation.")
        if len(spans) == 1 and re.search(r"\sOR\s", first.text):
            reply = "The entry describes two alternatives joined by “OR”. It doesn’t establish which penalty would apply to you."
        if "second offence" in q or "second offense" in q:
            reply = "I couldn’t verify a second-offence penalty for this conduct from the cited text."
    elif first.cell and (entry := re.search(
            r"(Possession, use or distribution) of ([A-Za-z]+)(?:/[^.]+?)? on (the Campus)\b",
            " ".join(first.text.split()), re.I)):
        reply = (f"The table lists {entry[1].lower()} of {entry[2].lower()} on campus. "
                 "I couldn’t establish an off-campus rule or a specific penalty from this entry.")
    elif re.search(r"\b(can|may|allowed|permitted|around|outside)\b",q) and "on the campus" in evidence:
        reply = "The cited provision refers to conduct on the campus. It doesn’t establish permission outside that boundary."
    elif first.cell:
        reply = "The handbook lists this conduct in the table on the cited page. That entry alone doesn’t establish the applicable penalty."
    else:
        reply = f"The closest provision is on page {first.page} of {first.book.title}."
    if contextual:
        reply += " I used the subject of your earlier question."
    if covered < total:
        reply += " I could locate material for only part of your question."
    return reply
