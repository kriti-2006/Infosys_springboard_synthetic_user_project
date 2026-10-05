"""
AGENT 1 — Persona Generation Agent

Takes the product description + target audience and "acts" by producing
a diverse set of synthetic personas with consistent demographic,
behavioral and psychological attributes. This is the action LangGraph
records into shared state for every downstream agent to consume.

Personas are generated ONE AT A TIME (rather than one big batched call for
all of them) -- asking a model to fill out every rich field (traits,
behavioral patterns, psychological profile, goals, pain points, a full
summary paragraph) for several personas in a single response produces a
large output that smaller/free models frequently truncate mid-way,
leaving later personas with missing required fields. Generating one
persona per call keeps each response small and far more reliable, at the
cost of one extra call per persona -- each previously generated persona is
summarized back into the prompt so the model keeps this one distinct
rather than a near-duplicate.
"""
import logging
from langchain_core.prompts import ChatPromptTemplate
from llm import invoke_structured
from schemas import Persona
from state import GraphState

log_ = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Synthetic Persona Generation Agent.

Given a product description, a target audience description, and a research goal,
generate ONE realistic synthetic persona representing a sub-segment of that
target audience.

Rules:
- Ground the persona in specifics plausible for the stated audience (do not invent
  an audience that wasn't asked for).
- The persona must be internally consistent (a "low tech-savviness" persona shouldn't
  have a pain point about advanced API rate limits).
- `behavioral_patterns` must be concrete, observable habits (not adjectives) —
  things this persona actually does, relevant to the product domain.
- `psychological_profile` must go deeper than `personality_traits`: cover underlying
  motivations, fears, and decision-making style relevant to this product domain.
- `persona_summary` should read like a natural paragraph a researcher could
  read aloud to introduce this person.
- If personas already generated in this batch are shown below, make this persona
  clearly DISTINCT from them: vary demographics, tech-savviness, motivation level,
  and pain points. Do not create a near-duplicate of an existing one.
"""

USER_TEMPLATE = """Product:
{product_description}

Target audience:
{target_audience}

Research goal (what this research should help decide):
{research_goal}

Personas already generated in this batch (avoid duplicating these):
{existing_personas_block}

Generate persona {index} of {total} now. Give it id "{persona_id}".
"""


def _existing_block(personas) -> str:
    if not personas:
        return "(none yet — this is the first persona)"
    return "\n".join(
        f"- {p.name}: {p.occupation}, tech-savviness={p.tech_savviness}, "
        f"traits={', '.join(p.personality_traits)}"
        for p in personas
    )


def persona_agent_node(state: GraphState) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_TEMPLATE),
    ])

    num_personas = state.get("num_personas", 5)
    log = state.get("log", [])
    personas: list[Persona] = []

    for i in range(1, num_personas + 1):
        persona_id = f"p{i}"
        try:
            persona: Persona = invoke_structured(
                prompt,
                Persona,
                {
                    "product_description": state["product_description"],
                    "target_audience": state["target_audience"],
                    "research_goal": state.get("research_goal", "general product validation"),
                    "existing_personas_block": _existing_block(personas),
                    "index": i,
                    "total": num_personas,
                    "persona_id": persona_id,
                },
                temperature=0.9,  # higher temp -> more persona diversity
                label=f"persona_agent(persona={i}/{num_personas})",
            )
        except Exception as e:
            log.append(f"[persona_agent] LLM call failed for persona {i}/{num_personas} on every candidate model: {e}")
            log_.error("persona_agent LLM call failed for persona %d/%d on every candidate model: %s", i, num_personas, e)
            raise RuntimeError(f"persona_agent: failed to generate persona {i}/{num_personas}") from e

        # force a stable, predictable id regardless of what the model echoed back
        persona.id = persona_id
        personas.append(persona)

    log.append(f"[persona_agent] generated {len(personas)} personas")

    return {"personas": personas, "log": log}
