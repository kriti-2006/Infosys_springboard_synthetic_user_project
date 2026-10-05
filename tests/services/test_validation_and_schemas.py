import pytest
from pydantic import ValidationError

from schemas_m3 import PersonaAnswer, QuestionIn, SurveyCreate, decision_from_score
from services.answer_validation import AnswerFormatError, QuestionSpec, heuristic_checks, normalise_value
from services.segments import classify_segment


def ans(value=None, text="ok fine"):
    return PersonaAnswer(answer=text, value=value, sentiment="neutral", confidence=0.5)


def test_question_schema_rules():
    QuestionIn(questionId="q1", question="Would you use this?", type="yes_no")
    with pytest.raises(ValidationError):
        QuestionIn(questionId="q1", question="Pick one please", type="single_choice", options=["only"])
    with pytest.raises(ValidationError):
        QuestionIn(questionId="q1", question="Open question here", type="open_ended", options=["a", "b"])
    with pytest.raises(ValidationError):
        QuestionIn(questionId="q1", question="Rate this thing", type="rating", scaleMin=5, scaleMax=1)
    with pytest.raises(ValidationError):
        SurveyCreate(experimentId="e", title="t", personaIds=["p"], questions=[
            dict(questionId="a", question="One question", type="yes_no"), dict(questionId="a", question="Two question", type="yes_no")])


@pytest.mark.parametrize("qtype,opts,value,expected", [
    ("yes_no", None, True, True), ("yes_no", None, "No", False),
    ("rating", None, 4, 4), ("likert", None, 2.0, 2), ("numeric", None, "12.5", 12.5),
    ("single_choice", ["A", "B"], "a", "A"), ("multiple_choice", ["A", "B", "C"], ["a", "C", "c"], ["A", "C"]),
    ("open_ended", None, None, None), ("short_answer", None, None, None)])
def test_normalise_ok(qtype, opts, value, expected):
    assert normalise_value(QuestionSpec("q", "t", qtype, opts), ans(value)) == expected


@pytest.mark.parametrize("qtype,opts,value", [
    ("yes_no", None, 3), ("rating", None, 9), ("rating", None, 2.5), ("rating", None, None), ("numeric", None, "abc"),
    ("single_choice", ["A", "B"], "Z"), ("multiple_choice", ["A", "B"], ["A", "Z"]), ("multiple_choice", ["A", "B"], [])])
def test_normalise_rejects(qtype, opts, value):
    with pytest.raises(AnswerFormatError):
        normalise_value(QuestionSpec("q", "t", qtype, opts), ans(value))


def test_heuristics():
    q = QuestionSpec("q", "Tell me", "open_ended")
    assert heuristic_checks(q, ans(text="As an AI language model I cannot"), 30).issues
    assert heuristic_checks(q, ans(text="word " * 200), 30).issues
    # demographic: 22-year-old claiming 25 years of experience
    assert any("implausible" in i for i in heuristic_checks(q, ans(text="I have 25 years of experience in my role"), 22).issues)
    assert not heuristic_checks(q, ans(text="I have 5 years of experience in my role"), 35).issues


def test_decision_bands_and_segments():
    assert [decision_from_score(s) for s in (0, 19, 20, 45, 60, 79, 80, 100)] == [
        "very_unlikely", "very_unlikely", "unlikely", "neutral", "likely", "likely", "very_likely", "very_likely"]
    assert classify_segment("College student") == "students"
    assert classify_segment("Retired bank clerk") == "retired"
    assert classify_segment("Parent of two, homemaker") == "parents"
    assert classify_segment("Freelance designer") == "freelancers"
    assert classify_segment("Software engineer") == "working_professionals"
