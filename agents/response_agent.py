"""
AGENT 3 — Survey Response Simulation Agent ("Survey Mode")

This is the agent that makes personas actually act: each persona answers
every survey question in character, consistent with its own traits,
goals and pain points. This implements "Survey Mode" from the project
spec — all personas answer the same questions for side-by-side comparison.

Each persona is answered via its own LLM call so responses don't bleed
into each other's voice/context.
"""
import logging
from langchain_core.prompts import ChatPromptTemplate
from llm import invoke_structured
from schemas import PersonaSurveyResponse
from state import GraphState

log_ = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are role-playing as ONE specific synthetic persona answering a survey.

Stay strictly in character:
- Name: {name}
- Occupation: {occupation}
- Background: {background}
- Personality traits: {personality_traits}
- Behavioral patterns: {behavioral_patterns}
- Psychological profile: {psychological_profile}
- Goals: {goals}
- Pain points: {pain_points}
- Tech savviness: {tech_savviness}
- Communication style: {communication_style}

Answer every question as this person genuinely would — their real opinion,
their real sentiment, in their own communication style. Do not be
artificially positive. If something in the product/survey wouldn't matter
to this persona, say so plainly.
"""

USER_TEMPLATE = """Product being researched:
{product_description}

Answer each of these survey questions:
{questions_block}

For each, give: the answer in your voice, your sentiment
(positive/neutral/negative/mixed), and a confidence 0-1 for how strongly you feel.
"""


def _questions_block(questions) -> str:
    lines = []
    for q in questions:
        opts = f" Options: {q.options}" if q.options else ""
        lines.append(f"[{q.id}] ({q.question_type}) {q.text}{opts}")
    return "\n".join(lines)


def response_agent_node(state: GraphState) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_TEMPLATE),
    ])

    questions_block = _questions_block(state["survey_questions"])
    responses = []

    log = state.get("log", [])

    for persona in state["personas"]:
        try:
            result: PersonaSurveyResponse = invoke_structured(
                prompt,
                PersonaSurveyResponse,
                {
                    "name": persona.name,
                    "occupation": persona.occupation,
                    "background": persona.background,
                    "personality_traits": ", ".join(persona.personality_traits),
                    "behavioral_patterns": ", ".join(persona.behavioral_patterns),
                    "psychological_profile": persona.psychological_profile,
                    "goals": ", ".join(persona.goals),
                    "pain_points": ", ".join(persona.pain_points),
                    "tech_savviness": persona.tech_savviness,
                    "communication_style": persona.communication_style,
                    "product_description": state["product_description"],
                    "questions_block": questions_block,
                },
                temperature=0.8,
                label=f"response_agent(persona={persona.id})",
            )
        except Exception as e:
            log.append(f"[response_agent] LLM call failed for persona {persona.id} on every candidate model: {e}")
            log_.error("response_agent LLM call failed for persona %s on every candidate model: %s", persona.id, e)
            raise RuntimeError(f"response_agent: failed to get survey response for persona {persona.id}") from e

        # force correct persona_id regardless of what the model echoed back
        result.persona_id = persona.id
        responses.append(result)

    log.append(f"[response_agent] collected responses from {len(responses)} personas")

    return {"survey_responses": responses, "log": log}
