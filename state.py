"""
This TypedDict is the single object that flows through every node in the
LangGraph graph. Each agent reads what it needs and returns a partial dict
that LangGraph merges into this state. This IS the "memory" that carries
context (product, audience, personas, survey, responses) from one agent
to the next within a run.

Cross-run / cross-session memory (so you can resume a thread later, or run
multiple products without losing history) is handled separately by
LangGraph's checkpointer (see graph.py -> MemorySaver + thread_id).
"""
from typing import TypedDict, List, Optional
from schemas import Persona, SurveyQuestion, PersonaSurveyResponse, InsightReport


class GraphState(TypedDict, total=False):
    # ---- inputs (set once, at the start) ----
    product_description: str
    target_audience: str
    research_goal: str          # what decision this research should inform
    num_personas: int
    num_questions: int

    # ---- produced by agents, in order ----
    personas: List[Persona]
    survey_questions: List[SurveyQuestion]
    survey_responses: List[PersonaSurveyResponse]
    insight_report: InsightReport
    report_pdf_path: str

    # ---- bookkeeping ----
    thread_id: str
    log: List[str]
