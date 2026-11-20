from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import pytest

from campus_help.answer.models import (
    AnswerStatus,
    EvidenceRequirement,
    QuestionIntentType,
    QuestionValidationPlan,
    SufficiencyEvaluation,
    ValidatedEvidence,
    ValidationIssueCode,
)
from campus_help.answer.question_planning import create_question_plan
from campus_help.answer.sufficiency import evaluate_evidence_sufficiency


# 1. Each supported intent category
def test_each_supported_intent_category():
    # PROHIBITION_PERMISSIBILITY
    plan_proh = create_question_plan("Is gambling prohibited in the hostel?")
    assert plan_proh.intent_type == QuestionIntentType.PROHIBITION_PERMISSIBILITY
    assert len(plan_proh.requirements) >= 2

    # DISCIPLINARY_AUTHORITY
    plan_auth = create_question_plan("Who has authority to impose disciplinary penalties?")
    assert plan_auth.intent_type == QuestionIntentType.DISCIPLINARY_AUTHORITY
    assert len(plan_auth.requirements) == 3

    # POLICY_APPLICABILITY
    plan_appl = create_question_plan("Do the disciplinary rules apply to part-time students?")
    assert plan_appl.intent_type == QuestionIntentType.POLICY_APPLICABILITY
    assert len(plan_appl.requirements) == 3

    # PROCEDURAL_DEADLINE
    plan_dead = create_question_plan("How many days are allowed to appeal a penalty?")
    assert plan_dead.intent_type == QuestionIntentType.PROCEDURAL_DEADLINE
    assert len(plan_dead.requirements) == 3

    # UNSUPPORTED_OR_UNKNOWN
    plan_unkn = create_question_plan("Where can I find the library timetable?")
    assert plan_unkn.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN
    assert plan_unkn.requirements == ()


# 2. Multiple phrasings of the same intent
def test_multiple_phrasings_prohibition():
    phrasings = [
        "Is gambling prohibited in the hostel?",
        "Is gambling or betting prohibited on university premises?",
        "Is cooking with a hot plate allowed in a hostel room?",
        "Is cyberbullying treated as a disciplinary violation?",
        "Is lending a university identity card a violation?",
        "Can students hold a peaceful sit-in without being punished under these rules?",
        "Can a student accommodate an unauthorized guest in a hall of residence?",
    ]
    for q in phrasings:
        plan = create_question_plan(q)
        assert plan.intent_type == QuestionIntentType.PROHIBITION_PERMISSIBILITY, f"Failed for {q}"
        assert len(plan.requirements) >= 2


def test_multiple_phrasings_authority():
    phrasings = [
        "Who has authority over student discipline?",
        "Who has the power to impose disciplinary penalties?",
        "Who is authorized to issue suspension orders?",
        "Which authority has the power to expel a student?",
        "Who imposes disciplinary penalties?",
    ]
    for q in phrasings:
        plan = create_question_plan(q)
        assert plan.intent_type == QuestionIntentType.DISCIPLINARY_AUTHORITY, f"Failed for {q}"
        assert len(plan.requirements) == 3


def test_multiple_phrasings_applicability():
    phrasings = [
        "Do the discipline rules apply if a student commits misconduct outside campus?",
        "Do the disciplinary rules apply to part-time students?",
        "Do these discipline rules cover distance learning students?",
        "Is the discipline policy applicable to exchange students?",
        "Are part-time students covered by the discipline rules?",
    ]
    for q in phrasings:
        plan = create_question_plan(q)
        assert plan.intent_type == QuestionIntentType.POLICY_APPLICABILITY, f"Failed for {q}"
        assert len(plan.requirements) == 3


def test_multiple_phrasings_deadline():
    phrasings = [
        "How many days are allowed to appeal a penalty?",
        "How many days do students have to submit an appeal?",
        "What is the deadline for filing an appeal?",
        "What is the deadline to appeal a penalty?",
        "What deadlines are stated for convening a Proctorial Committee?",
        "Within how many days must an appeal be submitted?",
    ]
    for q in phrasings:
        plan = create_question_plan(q)
        assert plan.intent_type == QuestionIntentType.PROCEDURAL_DEADLINE, f"Failed for {q}"
        assert len(plan.requirements) == 3


# 3. Unknown questions
def test_unknown_questions():
    unknown_queries = [
        "What general behaviour does the student code of conduct expect?",
        "What does the document say about possessing drugs?",
        "Why is a show-cause notice issued in the enquiry process?",
        "How does the committee handle audio evidence?",
        "What is the weather like in Greater Noida?",
        "Who wrote the Bennett University policy document?",
        "Explain the history of the student discipline committee.",
    ]
    for q in unknown_queries:
        plan = create_question_plan(q)
        assert plan.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN, f"Failed for {q}"
        assert plan.requirements == ()


# 4. Ambiguous questions
def test_ambiguous_questions():
    ambiguous_queries = [
        "Can a student be penalized when rules apply?",
        "Is it allowed or who has authority to permit it?",
        "Who can apply for what when?",
    ]
    for q in ambiguous_queries:
        plan = create_question_plan(q)
        assert plan.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN, f"Failed for {q}"
        assert plan.requirements == ()


# 5. Multi-part questions
def test_multipart_questions():
    multipart_queries = [
        "Who has authority to impose penalties and how many days are allowed to appeal?",
        "How soon and to whom must a student submit an appeal against a penalty?",
        "Who reviews major and minor penalties, and what can the Vice-Chancellor decide?",
        "Is alcohol prohibited on campus and who enforces the rule?",
        "Do the rules apply to off-campus events? And what is the appeal deadline?",
        "Can students keep pets in hostels; who can grant an exemption?",
    ]
    for q in multipart_queries:
        plan = create_question_plan(q)
        # Multi-part questions must not be silently reduced to one part
        assert plan.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN, f"Failed for {q}"
        assert plan.requirements == ()


# 6. Questions containing misleading intent keywords
def test_questions_with_misleading_keywords():
    # "apply" in the sense of application, not policy applicability
    plan_app1 = create_question_plan("How do I apply for a Bennett University scholarship?")
    assert plan_app1.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN

    plan_app2 = create_question_plan("How do I apply for a hostel room for next semester?")
    assert plan_app2.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN

    # "can" in the sense of possibility / consequence, not student permission
    plan_can1 = create_question_plan("What can happen if a student leaves campus without permission?")
    assert plan_can1.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN

    plan_can2 = create_question_plan("What can the Proctorial Committee do if the accused student does not appear?")
    assert plan_can2.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN

    # "when" in the sense of circumstances / conditions, not deadline
    plan_when = create_question_plan("When will a serious or off-campus incident generally be handled by the University Proctorial Committee?")
    assert plan_when.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN

    # "whose" in the sense of witness statements, not disciplinary authority
    plan_whose = create_question_plan("Whose statements and evidence are considered during a disciplinary enquiry?")
    assert plan_whose.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN

    # "penalties apply" in the sense of punishments, not policy applicability
    plan_pen = create_question_plan("What penalties can apply when university property is damaged or stolen?")
    assert plan_pen.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN


# 7. Empty or whitespace-only questions
@pytest.mark.parametrize("empty_q", ["", "   ", "\t\n  \t"])
def test_empty_or_whitespace_questions(empty_q):
    plan = create_question_plan(empty_q)
    assert plan.question == empty_q
    assert plan.intent_type == QuestionIntentType.UNSUPPORTED_OR_UNKNOWN
    assert plan.requirements == ()


def test_invalid_type_question():
    with pytest.raises(TypeError):
        create_question_plan(None)  # type: ignore
    with pytest.raises(TypeError):
        create_question_plan(123)  # type: ignore


# 8. Action extraction
def test_action_extraction():
    plan = create_question_plan("Is gambling or betting prohibited on university premises?")
    assert plan.intent_type == QuestionIntentType.PROHIBITION_PERMISSIBILITY

    conduct_req = next(r for r in plan.requirements if r.requirement_id == "req-conduct")
    assert "gambling" in conduct_req.factual_anchors
    assert "betting" in conduct_req.factual_anchors
    assert "gambling or betting" in conduct_req.description


# 9. Scope extraction
def test_scope_extraction():
    # With scope
    plan_with_scope = create_question_plan("Is cooking with a hot plate allowed in a hostel room?")
    scope_req = next((r for r in plan_with_scope.requirements if r.requirement_id == "req-scope"), None)
    assert scope_req is not None
    assert "hostel" in scope_req.factual_anchors
    assert "room" in scope_req.factual_anchors
    assert "hostel room" in scope_req.description

    # Without scope
    plan_no_scope = create_question_plan("Is cyberbullying treated as a disciplinary violation?")
    scope_req_none = next((r for r in plan_no_scope.requirements if r.requirement_id == "req-scope"), None)
    assert scope_req_none is None


# 10. Deadline requirement generation without inventing numbers
def test_deadline_requirement_generation_without_inventing_numbers():
    plan = create_question_plan("How many days are allowed to appeal a penalty?")
    assert plan.intent_type == QuestionIntentType.PROCEDURAL_DEADLINE

    for req in plan.requirements:
        # Must not invent numbers like 5, 10, 15
        for anchor in req.factual_anchors:
            assert not anchor.isdigit(), f"Invented number in anchor: {anchor}"
        assert "5" not in req.description
        assert "15" not in req.description
        assert "10" not in req.description

    # Explicit duration and unit requirement exists
    unit_req = next(r for r in plan.requirements if r.requirement_id == "req-deadline-duration-unit")
    assert unit_req.expected_predicate == "explicit_duration_and_unit"
    assert "days" in unit_req.factual_anchors


# 11. Authority requirement generation without inventing roles
def test_authority_requirement_generation_without_inventing_roles():
    plan = create_question_plan("Who has authority to impose disciplinary penalties?")
    assert plan.intent_type == QuestionIntentType.DISCIPLINARY_AUTHORITY

    # Must not contain Bennett University specific roles like Vice Chancellor or Proctor
    for req in plan.requirements:
        for anchor in req.factual_anchors:
            assert "chancellor" not in anchor.lower()
            assert "proctor" not in anchor.lower()
        assert "vice chancellor" not in req.description.lower()
        assert "proctor" not in req.description.lower()

    role_req = next(r for r in plan.requirements if r.requirement_id == "req-authority-role")
    assert role_req.expected_predicate == "institutional_authority_role"


# 12. No verified requirements
def test_no_verified_requirements():
    questions = [
        "Is gambling prohibited in the hostel?",
        "Who has authority to impose disciplinary penalties?",
        "Do the disciplinary rules apply to part-time students?",
        "How many days are allowed to appeal a penalty?",
    ]
    for q in questions:
        plan = create_question_plan(q)
        assert len(plan.requirements) > 0
        for req in plan.requirements:
            assert req.is_verified is False, f"Requirement {req.requirement_id} was marked verified!"


# 13. Deterministic output
def test_deterministic_output():
    question = "Is cooking with a hot plate allowed in a hostel room?"
    plans = [create_question_plan(question) for _ in range(5)]

    first = plans[0]
    for other in plans[1:]:
        assert other.question == first.question
        assert other.intent_type == first.intent_type
        assert len(other.requirements) == len(first.requirements)
        for r1, r2 in zip(first.requirements, other.requirements):
            assert r1.requirement_id == r2.requirement_id
            assert r1.description == r2.description
            assert r1.intent_type == r2.intent_type
            assert r1.factual_anchors == r2.factual_anchors
            assert r1.expected_predicate == r2.expected_predicate
            assert r1.is_verified == r2.is_verified
        assert other.to_dict() == first.to_dict()


# 14. Immutable models
def test_immutable_models():
    plan = create_question_plan("Is gambling prohibited in the hostel?")
    with pytest.raises(FrozenInstanceError):
        plan.question = "Modified question"  # type: ignore

    with pytest.raises(FrozenInstanceError):
        plan.intent_type = QuestionIntentType.UNSUPPORTED_OR_UNKNOWN  # type: ignore

    with pytest.raises(FrozenInstanceError):
        plan.requirements = ()  # type: ignore

    req = plan.requirements[0]
    with pytest.raises(FrozenInstanceError):
        req.is_verified = True  # type: ignore


# 15. Compatibility with M6.3A
def test_compatibility_with_m63a():
    question = "Is gambling prohibited in the hostel?"
    plan = create_question_plan(question)

    # Pass generated plan into M6.3A evaluate_evidence_sufficiency
    evaluation = evaluate_evidence_sufficiency(
        question=question,
        validated_evidence=(),
        issues=(),
        plan=plan,
    )

    assert isinstance(evaluation, SufficiencyEvaluation)
    assert evaluation.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert evaluation.is_sufficient is False
    assert evaluation.plan == plan
    assert len(evaluation.unverified_requirements) == len(plan.requirements)
    assert evaluation.verified_requirements == ()
    assert any(b.code == ValidationIssueCode.EMPTY_EVIDENCE for b in evaluation.blockers)


# 16. Representative sample of M4.1 questions
def test_representative_sample_m41_questions():
    m41_path = Path(__file__).resolve().parent.parent / "data" / "evaluation" / "m4_1_questions.json"
    assert m41_path.exists(), f"Missing M4.1 questions file at {m41_path}"

    with open(m41_path, encoding="utf-8") as f:
        m41_questions = json.load(f)

    # Sample checks across categories without hardcoding question IDs in production
    known_intents = 0
    unknown_intents = 0

    for item in m41_questions:
        q_text = item["question"]
        plan = create_question_plan(q_text)

        assert plan.question == q_text
        assert all(not r.is_verified for r in plan.requirements)
        assert isinstance(plan.intent_type, QuestionIntentType)

        if plan.intent_type != QuestionIntentType.UNSUPPORTED_OR_UNKNOWN:
            known_intents += 1
            assert len(plan.requirements) >= 2
        else:
            unknown_intents += 1
            assert plan.requirements == ()

    # Conservative recognition: some recognized, others remain fail-closed / unsupported
    assert known_intents >= 8
    assert unknown_intents >= 20
