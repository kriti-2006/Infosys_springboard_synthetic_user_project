"""
AGENT 4 — Insight Extraction Agent

Analyzes ALL persona responses together, surfaces themes, sentiment
patterns and behavioral trends, and produces a structured InsightReport
that report_generator.py then renders as a PDF.
"""
import logging
from langchain_core.prompts import ChatPromptTemplate
from llm import invoke_structured
from schemas import InsightReport
from state import GraphState

log_ = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an Insight Extraction Agent for synthetic user research.

You will be given a product, the research goal, the personas who participated,
the survey questions, and every persona's answers. Your job:
- Identify cross-cutting themes (patterns that show up across multiple personas)
- Note where personas diverge and why (tie divergence to persona traits when possible)
- Give an honest overall sentiment read — do not inflate positivity
- Call out weak areas / risks the product team (or student, in a placement-prep context) should address
- End with concrete, prioritized recommendations

Ground every claim in the actual responses provided. Do not invent data.
"""

USER_TEMPLATE = """Product:
{product_description}

Research goal:
{research_goal}

Personas:
{persona_block}

Survey questions:
{questions_block}

Full response data (persona_id -> question_id -> answer/sentiment):
{responses_block}

Produce the structured insight report now.
"""


def _persona_block(personas) -> str:
    return "\n".join(
        f"- {p.id}: {p.name}, {p.occupation}, traits: {', '.join(p.personality_traits)}, "
        f"behavioral patterns: {', '.join(p.behavioral_patterns)}, "
        f"psychological profile: {p.psychological_profile}"
        for p in personas
    )


def _questions_block(questions) -> str:
    return "\n".join(f"- {q.id}: {q.text}" for q in questions)


def _responses_block(responses) -> str:
    lines = []
    for r in responses:
        for a in r.answers:
            lines.append(
                f"- persona={r.persona_id} | question={a.question_id} | "
                f"sentiment={a.sentiment} | confidence={a.confidence} | answer=\"{a.answer}\""
            )
    return "\n".join(lines)


def insight_agent_node(state: GraphState) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_TEMPLATE),
    ])

    log = state.get("log", [])
    try:
        result: InsightReport = invoke_structured(
            prompt,
            InsightReport,
            {
                "product_description": state["product_description"],
                "research_goal": state.get("research_goal", "general product validation"),
                "persona_block": _persona_block(state["personas"]),
                "questions_block": _questions_block(state["survey_questions"]),
                "responses_block": _responses_block(state["survey_responses"]),
            },
            temperature=0.3,  # low temp: we want grounded, consistent analysis
            label="insight_agent",
        )
    except Exception as e:
        log.append(f"[insight_agent] LLM call failed on every candidate model: {e}")
        log_.error("insight_agent LLM call failed on every candidate model: %s", e)
        raise RuntimeError("insight_agent: failed to generate insight report") from e

    log.append("[insight_agent] insight report generated")

    return {"insight_report": result, "log": log}
