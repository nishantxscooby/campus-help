"""Deterministic question intent recognition and requirement planning for M6.3B."""

from __future__ import annotations

import re
from typing import Sequence

from ..retrieval.tokenizer import tokenize
from .models import (
    EvidenceRequirement,
    QuestionIntentType,
    QuestionValidationPlan,
)

STOP_WORDS = frozenset(
    {
        "a",
        "about",
        "an",
        "and",
        "are",
        "at",
        "be",
        "been",
        "being",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "may",
        "might",
        "not",
        "of",
        "on",
        "or",
        "shall",
        "should",
        "that",
        "the",
        "these",
        "this",
        "those",
        "to",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "whose",
        "why",
        "will",
        "with",
        "would",
    }
)

# Prohibition / Permissibility patterns
PROHIBITION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "Is <action> (strictly) prohibited/banned/disallowed/forbidden (in/at/on/within <scope>)?"
    re.compile(
        r"^is\s+(.+?)\s+(?:strictly\s+)?(prohibited|banned|disallowed|forbidden)(?:\s+(in|at|on|within)\s+(.+?))?\??$",
        re.IGNORECASE,
    ),
    # "Is <action> allowed/permitted (in/at/on/within <scope>)?"
    re.compile(
        r"^is\s+(.+?)\s+(allowed|permitted)(?:\s+(in|at|on|within)\s+(.+?))?\??$",
        re.IGNORECASE,
    ),
    # "Is <action> treated as a disciplinary violation/offence/misconduct (in/at/on/within <scope>)?"
    re.compile(
        r"^is\s+(.+?)\s+(?:treated\s+as\s+)?(?:a\s+)?(?:disciplinary\s+)?(violation|offence|infraction|misconduct)(?:\s+(in|at|on|within)\s+(.+?))?\??$",
        re.IGNORECASE,
    ),
    # "Can/May students/a student <action> without being punished/penalty/disciplinary action (under/in <scope>)?"
    re.compile(
        r"^(?:can|may)\s+(?:students?|a\s+student|anyone)\s+(.+?)\s+without\s+(being\s+punished|penalty|disciplinary\s+action)(?:\s+(?:under|in)\s+(.+?))?\??$",
        re.IGNORECASE,
    ),
    # "Can/May a student/students <action> in/at/on/within <scope>?"
    re.compile(
        r"^(?:can|may)\s+(?:students?|a\s+student|anyone)\s+(.+?)\s+(in|at|on|within)\s+(.+?)\??$",
        re.IGNORECASE,
    ),
)

# Disciplinary Authority patterns
AUTHORITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "Who has authority/power/powers/jurisdiction over/to/for <action>?"
    re.compile(
        r"^who\s+has\s+(?:the\s+)?(?:authority|power|powers|jurisdiction|responsibility)\s+(over|to|for)\s+(.+?)\??$",
        re.IGNORECASE,
    ),
    # "Who is authorized/empowered to <action>?"
    re.compile(
        r"^who\s+is\s+(?:authorized|empowered)\s+to\s+(.+?)\??$",
        re.IGNORECASE,
    ),
    # "Which/What authority/official/body/committee has authority / is authorized to / can impose / imposes <action>?"
    re.compile(
        r"^(?:which|what)\s+(?:authority|official|body|committee|office)\s+(?:has\s+(?:the\s+)?(?:power|authority)\s+to|is\s+authorized\s+to|can\s+impose|imposes|decides|handles)\s+(.+?)\??$",
        re.IGNORECASE,
    ),
    # "Who imposes/decides/orders <action>?"
    re.compile(
        r"^who\s+(?:imposes|decides|orders)\s+(.+?)\??$",
        re.IGNORECASE,
    ),
)

# Policy Applicability patterns
APPLICABILITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "Do/Does the <policy> (rules/policy/code) apply if/to/when <target>?"
    re.compile(
        r"^do(?:es)?\s+(?:the\s+|these\s+)?(.+?)\s+(?:rules?|policy|code)\s+apply\s+(if|to|when)\s+(.+?)\??$",
        re.IGNORECASE,
    ),
    # "Do/Does the <policy> (rules/policy/code) cover <target>?"
    re.compile(
        r"^do(?:es)?\s+(?:the\s+|these\s+)?(.+?)\s+(?:rules?|policy|code)\s+cover\s+(.+?)\??$",
        re.IGNORECASE,
    ),
    # "Is the <policy> (rules/policy/code) applicable to <target>?"
    re.compile(
        r"^is\s+(?:the\s+|these\s+)?(.+?)\s+(?:rules?|policy|code)\s+applicable\s+to\s+(.+?)\??$",
        re.IGNORECASE,
    ),
    # "Are <target> covered/governed by the <policy> (rules/policy/code)?"
    re.compile(
        r"^are\s+(.+?)\s+(?:covered|governed)\s+by\s+(?:the\s+|these\s+)?(.+?)\s*(?:rules?|policy|code)\??$",
        re.IGNORECASE,
    ),
)

# Procedural Deadline patterns
DEADLINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "How many days/hours/weeks/months are allowed / do students have to/for <procedure>?"
    re.compile(
        r"^how\s+many\s+(days|hours|weeks|months|working\s+days)\s+(?:are\s+allowed|do\s+students\s+have|are\s+given|is\s+allowed|is\s+the\s+limit)\s+(?:to|for)\s+(.+?)\??$",
        re.IGNORECASE,
    ),
    # "What is the deadline / What are the deadlines / What deadlines are stated for <procedure>?"
    re.compile(
        r"^what\s+(?:is\s+the\s+deadline|are\s+the\s+deadlines|deadlines\s+are|deadline\s+is|is\s+the\s+time\s+limit|is\s+the\s+timeframe)(?:\s+(?:for|to|stated\s+for))?\s+(.+?)\??$",
        re.IGNORECASE,
    ),
    # "Within how many days/weeks/hours must/should/can <procedure>?"
    re.compile(
        r"^within\s+how\s+many\s+(days|hours|weeks|months|working\s+days)\s+(?:must|should|can)\s+(.+?)\??$",
        re.IGNORECASE,
    ),
)

# Multi-part interrogative clauses pattern
MULTIPART_CONJUNCTION_PATTERN = re.compile(
    r"\b(?:and|or|as\s+well\s+as)\s+(?:who|whom|whose|what|when|where|how|why|is|are|can|do|does)\b",
    re.IGNORECASE,
)
COMPOUND_WH_PATTERN = re.compile(
    r"\bhow\s+soon\s+and\s+to\s+whom\b",
    re.IGNORECASE,
)


def _extract_anchors(text: str) -> tuple[str, ...]:
    """Extract deterministic, meaningful factual anchor tokens from text."""
    terms: list[str] = []
    seen: set[str] = set()
    for token in tokenize(text):
        if token in STOP_WORDS or len(token) < 2:
            continue
        if token not in seen:
            seen.add(token)
            terms.append(token)
    return tuple(terms)


def _clean_phrase(text: str) -> str:
    """Trim whitespace and trailing punctuation from extracted phrase."""
    return text.strip().rstrip("?.!").strip()


def _is_multipart_or_ambiguous(text: str) -> bool:
    """Check if the question is an ambiguous multi-part query spanning distinct clauses."""
    # Multiple explicit question marks
    if text.count("?") > 1:
        return True

    # Semicolons separating clauses
    if ";" in text:
        return True

    # Multi-part conjunction followed by interrogative word
    if MULTIPART_CONJUNCTION_PATTERN.search(text):
        return True

    # Compound interrogatives like "how soon and to whom"
    if COMPOUND_WH_PATTERN.search(text):
        return True

    return False


def _match_prohibition(
    text: str,
) -> tuple[str, str, str | None] | None:
    """Attempt conservative match for prohibition/permissibility intent.

    Returns (action, permission_relation, scope) or None.
    """
    # Pattern 1: Is <action> (strictly) prohibited/banned... (in <scope>)?
    m = PROHIBITION_PATTERNS[0].match(text)
    if m:
        action = _clean_phrase(m.group(1))
        relation = m.group(2).lower()
        scope = _clean_phrase(m.group(4)) if m.group(4) else None
        return action, relation, scope

    # Pattern 2: Is <action> allowed/permitted (in <scope>)?
    m = PROHIBITION_PATTERNS[1].match(text)
    if m:
        action = _clean_phrase(m.group(1))
        relation = m.group(2).lower()
        scope = _clean_phrase(m.group(4)) if m.group(4) else None
        return action, relation, scope

    # Pattern 3: Is <action> treated as a violation... (in <scope>)?
    m = PROHIBITION_PATTERNS[2].match(text)
    if m:
        action = _clean_phrase(m.group(1))
        relation = m.group(2).lower()
        scope = _clean_phrase(m.group(4)) if m.group(4) else None
        return action, relation, scope

    # Pattern 4: Can/May students <action> without being punished... (under <scope>)?
    m = PROHIBITION_PATTERNS[3].match(text)
    if m:
        action = _clean_phrase(m.group(1))
        relation = "permissible_without_penalty"
        scope = _clean_phrase(m.group(3)) if m.group(3) else None
        return action, relation, scope

    # Pattern 5: Can a student <action> in <scope>?
    m = PROHIBITION_PATTERNS[4].match(text)
    if m:
        action = _clean_phrase(m.group(1))
        relation = "permissible"
        scope = _clean_phrase(m.group(3)) if m.group(3) else None
        return action, relation, scope

    return None


def _match_authority(
    text: str,
) -> str | None:
    """Attempt conservative match for disciplinary authority intent.

    Returns action/mandate description or None.
    """
    for pattern in AUTHORITY_PATTERNS:
        m = pattern.match(text)
        if m:
            # Action is the last capture group
            action = _clean_phrase(m.group(m.lastindex or 1))
            return action
    return None


def _match_applicability(
    text: str,
) -> tuple[str, str] | None:
    """Attempt conservative match for policy applicability intent.

    Returns (policy_scope, target) or None.
    """
    # Pattern 1: Do the <policy> rules apply (if/to/when) <target>?
    m = APPLICABILITY_PATTERNS[0].match(text)
    if m:
        policy_scope = _clean_phrase(f"{m.group(1)} rules")
        target = _clean_phrase(m.group(3))
        return policy_scope, target

    # Pattern 2: Do the <policy> rules cover <target>?
    m = APPLICABILITY_PATTERNS[1].match(text)
    if m:
        policy_scope = _clean_phrase(f"{m.group(1)} rules")
        target = _clean_phrase(m.group(2))
        return policy_scope, target

    # Pattern 3: Is the <policy> rules applicable to <target>?
    m = APPLICABILITY_PATTERNS[2].match(text)
    if m:
        policy_scope = _clean_phrase(f"{m.group(1)} rules")
        target = _clean_phrase(m.group(2))
        return policy_scope, target

    # Pattern 4: Are <target> covered/governed by <policy> rules?
    m = APPLICABILITY_PATTERNS[3].match(text)
    if m:
        target = _clean_phrase(m.group(1))
        policy_scope = _clean_phrase(f"{m.group(2)} rules")
        return policy_scope, target

    return None


def _match_deadline(
    text: str,
) -> tuple[str, str] | None:
    """Attempt conservative match for procedural deadline intent.

    Returns (procedure, requested_unit_or_type) or None.
    """
    # Pattern 1: How many days are allowed to/for <procedure>?
    m = DEADLINE_PATTERNS[0].match(text)
    if m:
        unit = m.group(1).lower()
        procedure = _clean_phrase(m.group(2))
        return procedure, unit

    # Pattern 2: What is the deadline for/to <procedure>?
    m = DEADLINE_PATTERNS[1].match(text)
    if m:
        procedure = _clean_phrase(m.group(1))
        return procedure, "deadline"

    # Pattern 3: Within how many days must/should/can <procedure>?
    m = DEADLINE_PATTERNS[2].match(text)
    if m:
        unit = m.group(1).lower()
        procedure = _clean_phrase(m.group(2))
        return procedure, unit

    return None


def _build_prohibition_requirements(
    action: str,
    relation: str,
    scope: str | None,
) -> tuple[EvidenceRequirement, ...]:
    """Generate explicit evidence requirements for prohibition/permissibility."""
    action_anchors = _extract_anchors(action)
    requirements: list[EvidenceRequirement] = [
        EvidenceRequirement(
            requirement_id="req-conduct",
            description=f"Identify rule or policy provisions covering '{action}'",
            intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
            factual_anchors=action_anchors,
            expected_predicate="regulated_conduct",
            is_verified=False,
        ),
        EvidenceRequirement(
            requirement_id="req-permissibility-status",
            description=f"Establish whether '{action}' is prohibited, permitted, or classified as a violation",
            intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
            factual_anchors=("prohibited", "banned", "allowed", "permitted", "violation"),
            expected_predicate="permissibility_status",
            is_verified=False,
        ),
    ]

    if scope:
        scope_anchors = _extract_anchors(scope)
        requirements.append(
            EvidenceRequirement(
                requirement_id="req-scope",
                description=f"Establish rule applicability to location or context: '{scope}'",
                intent_type=QuestionIntentType.PROHIBITION_PERMISSIBILITY,
                factual_anchors=scope_anchors,
                expected_predicate="location_or_context_scope",
                is_verified=False,
            )
        )

    return tuple(requirements)


def _build_authority_requirements(
    action: str,
) -> tuple[EvidenceRequirement, ...]:
    """Generate explicit evidence requirements for disciplinary authority."""
    action_anchors = _extract_anchors(action)
    return (
        EvidenceRequirement(
            requirement_id="req-authority-role",
            description=f"Identify the designated institutional official, body, or committee with authority for '{action}'",
            intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
            factual_anchors=("authority", "power", "powers", "officer", "committee", "body", "jurisdiction"),
            expected_predicate="institutional_authority_role",
            is_verified=False,
        ),
        EvidenceRequirement(
            requirement_id="req-disciplinary-action",
            description=f"Establish the disciplinary action or subject matter concerning '{action}'",
            intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
            factual_anchors=action_anchors,
            expected_predicate="disciplinary_mandate",
            is_verified=False,
        ),
        EvidenceRequirement(
            requirement_id="req-authority-relationship",
            description=f"Establish that the identified authority is empowered or authorized to execute '{action}'",
            intent_type=QuestionIntentType.DISCIPLINARY_AUTHORITY,
            factual_anchors=("authorized", "empowered", "vested", "competent", "jurisdiction"),
            expected_predicate="authority_relationship",
            is_verified=False,
        ),
    )


def _build_applicability_requirements(
    policy_scope: str,
    target: str,
) -> tuple[EvidenceRequirement, ...]:
    """Generate explicit evidence requirements for policy applicability."""
    target_anchors = _extract_anchors(target)
    policy_anchors = _extract_anchors(policy_scope)
    return (
        EvidenceRequirement(
            requirement_id="req-applicability-target",
            description=f"Identify policy provisions addressing '{target}'",
            intent_type=QuestionIntentType.POLICY_APPLICABILITY,
            factual_anchors=target_anchors,
            expected_predicate="target_category_or_circumstance",
            is_verified=False,
        ),
        EvidenceRequirement(
            requirement_id="req-policy-scope",
            description=f"Identify the relevant policy framework or rule set ('{policy_scope}')",
            intent_type=QuestionIntentType.POLICY_APPLICABILITY,
            factual_anchors=policy_anchors,
            expected_predicate="governing_policy",
            is_verified=False,
        ),
        EvidenceRequirement(
            requirement_id="req-applicability-relationship",
            description=f"Establish whether '{policy_scope}' applies to or governs '{target}'",
            intent_type=QuestionIntentType.POLICY_APPLICABILITY,
            factual_anchors=("apply", "applies", "applicable", "cover", "covers", "jurisdiction", "extent"),
            expected_predicate="applicability_relationship",
            is_verified=False,
        ),
    )


def _build_deadline_requirements(
    procedure: str,
    requested_unit: str,
) -> tuple[EvidenceRequirement, ...]:
    """Generate explicit evidence requirements for procedural deadlines."""
    procedure_anchors = _extract_anchors(procedure)
    return (
        EvidenceRequirement(
            requirement_id="req-deadline-procedure",
            description=f"Identify the relevant procedure or action ('{procedure}')",
            intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
            factual_anchors=procedure_anchors,
            expected_predicate="procedural_stage",
            is_verified=False,
        ),
        EvidenceRequirement(
            requirement_id="req-deadline-timeframe",
            description=f"Establish the stipulated deadline or timeframe for '{procedure}'",
            intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
            factual_anchors=("deadline", "within", "time", "period", "limit"),
            expected_predicate="stipulated_deadline",
            is_verified=False,
        ),
        EvidenceRequirement(
            requirement_id="req-deadline-duration-unit",
            description=f"Establish an explicit duration and time unit for '{procedure}' without inventing values",
            intent_type=QuestionIntentType.PROCEDURAL_DEADLINE,
            factual_anchors=("days", "working days", "hours", "weeks", "months"),
            expected_predicate="explicit_duration_and_unit",
            is_verified=False,
        ),
    )


def create_question_plan(
    question: str,
) -> QuestionValidationPlan:
    """Create a deterministic QuestionValidationPlan from a policy query.

    Recognizes restricted intent categories:
    - PROHIBITION_PERMISSIBILITY
    - DISCIPLINARY_AUTHORITY
    - POLICY_APPLICABILITY
    - PROCEDURAL_DEADLINE
    - UNSUPPORTED_OR_UNKNOWN

    Adheres strictly to safety rules:
    - Never invents factual answers, roles, or durations.
    - Never marks requirements as verified.
    - Treats ambiguous or multi-part questions as UNSUPPORTED_OR_UNKNOWN.
    - Preserves student's original question string.
    """
    if isinstance(question, bool) or not isinstance(question, str):
        raise TypeError("question must be a string")

    clean_q = question.strip()
    if not clean_q:
        return QuestionValidationPlan(
            question=question,
            intent_type=QuestionIntentType.UNSUPPORTED_OR_UNKNOWN,
            requirements=(),
        )

    # Check for ambiguous multi-part questions across clauses
    if _is_multipart_or_ambiguous(clean_q):
        return QuestionValidationPlan(
            question=question,
            intent_type=QuestionIntentType.UNSUPPORTED_OR_UNKNOWN,
            requirements=(),
        )

    # Attempt matching for each category
    matches: list[tuple[QuestionIntentType, tuple[EvidenceRequirement, ...]]] = []

    prohibition_match = _match_prohibition(clean_q)
    if prohibition_match:
        action, relation, scope = prohibition_match
        reqs = _build_prohibition_requirements(action, relation, scope)
        matches.append((QuestionIntentType.PROHIBITION_PERMISSIBILITY, reqs))

    authority_match = _match_authority(clean_q)
    if authority_match:
        reqs = _build_authority_requirements(authority_match)
        matches.append((QuestionIntentType.DISCIPLINARY_AUTHORITY, reqs))

    applicability_match = _match_applicability(clean_q)
    if applicability_match:
        policy_scope, target = applicability_match
        reqs = _build_applicability_requirements(policy_scope, target)
        matches.append((QuestionIntentType.POLICY_APPLICABILITY, reqs))

    deadline_match = _match_deadline(clean_q)
    if deadline_match:
        procedure, unit = deadline_match
        reqs = _build_deadline_requirements(procedure, unit)
        matches.append((QuestionIntentType.PROCEDURAL_DEADLINE, reqs))

    # If multiple intents match, the question is ambiguous; fail-closed to UNSUPPORTED_OR_UNKNOWN
    if len(matches) != 1:
        return QuestionValidationPlan(
            question=question,
            intent_type=QuestionIntentType.UNSUPPORTED_OR_UNKNOWN,
            requirements=(),
        )

    intent_type, requirements = matches[0]
    return QuestionValidationPlan(
        question=question,
        intent_type=intent_type,
        requirements=requirements,
    )


__all__ = [
    "create_question_plan",
]
