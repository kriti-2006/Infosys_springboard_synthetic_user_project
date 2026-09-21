"""
AGENT 2 — Survey Generation Agent

Reads the product, research goal, AND the personas already generated
(so questions are tuned to the audience that will actually answer them),
and produces a structured survey: a mix of Likert, open-ended, multiple
choice and yes/no questions.
"""
import logging
from langchain_core.prompts import ChatPromptTemplate
from llm import invoke_structured
from schemas import SurveySet
from state import GraphState

log_ = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Survey Design Agent for product research.

Given a product, a research goal, and a set of target personas, design a survey
that will surface the most decision-relevant insight for the research goal.

Rules:
- Mix question types: some likert_1_5 (quantifiable), some open_ended (qualitative depth),
  a couple multiple_choice or yes_no where a discrete choice matters.
- Every question needs a one-line rationale tying it back to the research goal.
- Avoid leading or double-barreled questions.
- Order questions from broad/warm-up to specific/decision-critical.
"""

USER_TEMPLATE = """Product:
{product_description}

Research goal:
{research_goal}

Target personas who will answer this survey (for calibration only — do not
address them individually, write generic questions they can each answer):
{persona_briefs}

Generate exactly {num_questions} survey questions.
"""


def _brief(p) -> str:
    return (
        f"- {p.name} ({p.occupation}, tech-savviness: {p.tech_savviness}; "
        f"behavioral patterns: {', '.join(p.behavioral_patterns)})"
    )


def survey_agent_node(state: GraphState) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_TEMPLATE),
    ])

    persona_briefs = "\n".join(_brief(p) for p in state["personas"])

    log = state.get("log", [])
    try:
        result: SurveySet = invoke_structured(
            prompt,
            SurveySet,
            {
                "product_description": state["product_description"],
                "research_goal": state.get("research_goal", "general product validation"),
                "persona_briefs": persona_briefs,
                "num_questions": state.get("num_questions", 6),
            },
            temperature=0.5,
            label="survey_agent",
        )
    except Exception as e:
        log.append(f"[survey_agent] LLM call failed on every candidate model: {e}")
        log_.error("survey_agent LLM call failed on every candidate model: %s", e)
        raise RuntimeError("survey_agent: failed to generate survey questions") from e

    log.append(f"[survey_agent] generated {len(result.questions)} questions")

    return {"survey_questions": result.questions, "log": log}
