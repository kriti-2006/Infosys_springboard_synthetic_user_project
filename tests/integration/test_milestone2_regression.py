"""Milestone-2 behaviour must be untouched by Milestone 3."""
from langchain_core.messages import AIMessage

from schemas import InsightReport, Persona, PersonaSurveyResponse, SurveyAnswer, SurveySet, SurveyQuestion, Theme
from tests.scenarios import SCENARIOS


def test_m2_graph_compiles_and_pipeline_runs(monkeypatch):
    from agents import insight_agent, persona_agent, response_agent, survey_agent
    import graph
    persona = Persona(**SCENARIOS["food_delivery"]["personas"][0])
    monkeypatch.setattr(persona_agent, "invoke_structured", lambda *a, **k: persona.model_copy())
    monkeypatch.setattr(survey_agent, "invoke_structured", lambda *a, **k: SurveySet(questions=[
        SurveyQuestion(id="q1", text="Like it?", question_type="yes_no", rationale="r")]))
    monkeypatch.setattr(response_agent, "invoke_structured", lambda *a, **k: PersonaSurveyResponse(
        persona_id="x", answers=[SurveyAnswer(question_id="q1", answer="yes", sentiment="positive", confidence=0.9)]))
    monkeypatch.setattr(insight_agent, "invoke_structured", lambda *a, **k: InsightReport(
        executive_summary="s", overall_sentiment="positive", key_themes=[Theme(title="t", description="d", supporting_persona_ids=["p1"], prevalence="high")],
        notable_quotes=[], weak_areas_or_risks=[], recommendations=["r"]))
    state = graph.run_pipeline("prod", "aud", "goal", num_personas=2, num_questions=1, thread_id="t1")
    assert len(state["personas"]) == 2 and len(state["survey_responses"]) == 2 and state["insight_report"].overall_sentiment == "positive"


def test_m2_interview_session_still_works(monkeypatch):
    from agents import interview_agent
    monkeypatch.setattr(interview_agent, "invoke_chat", lambda *a, **k: AIMessage(content="I care about price."))
    s = interview_agent.start_persona_interview(Persona(**SCENARIOS["food_delivery"]["personas"][0]), "app")
    assert s.respond("Do you care about price?") == "I care about price." and len(s.history) == 2
    assert s.respond("again?") and len(s.history) == 4


def test_m2_sync_llm_api_unchanged():
    import llm
    assert callable(llm.invoke_structured) and callable(llm.invoke_chat) and llm.FALLBACK_MODELS
