"""
Persona Simulation Agent — answers ONE question as ONE persona.
Shared by Survey Mode and Interview Mode (so there is a single answer-generation path).
Inputs are layered: persona profile + retrieved memories + experiment context + previous answers/turns + question.
"""
from langchain_core.prompts import ChatPromptTemplate

import llm
from schemas_m3 import PersonaAnswer
from services.answer_validation import QuestionSpec, format_instructions

SYSTEM = """You are role-playing ONE specific real person. You are NOT an assistant.

Rules:
- Answer exactly as this person would, using their age, occupation, personality, behavioral patterns, psychological profile, goals and frustrations.
- Stay CONSISTENT with the person's remembered facts and with everything they already said earlier in this survey/interview. Never contradict them.
- Different people answer differently: lean on this person's specifics, not on generic product-review language.
- Never mention being an AI, a model, a persona, or a simulation. No marketing language. Be concise and natural, in the person's communication style.
- Do not be artificially positive. If something doesn't matter to this person, say so plainly.
- `memory_updates`: only genuinely NEW, stable facts or stances this answer reveals that are not already in memory (0-3 items). Skip trivia.
"""

USER = """=== Experiment context ===
{context}

=== The person ===
{persona}

=== Relevant memories (things already established about this person) ===
{memories}

=== {history_title} ===
{history}

=== Question ({qtype}) ===
{question}

Format: {format_instructions}
{feedback}"""


async def generate_answer(*, persona_block: str, context: str, question: QuestionSpec, memories: str, history: str,
                          mode: str = "survey", feedback: str = "") -> PersonaAnswer:
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("user", USER)])
    return await llm.ainvoke_structured(
        prompt, PersonaAnswer,
        {
            "context": context, "persona": persona_block, "memories": memories,
            "history_title": "Earlier in this survey (your own answers)" if mode == "survey" else "Recent interview turns",
            "history": history or "(nothing yet)", "qtype": question.type, "question": question.text,
            "format_instructions": format_instructions(question),
            "feedback": f"\nYour previous attempt was rejected: {feedback}\nFix this in your new answer." if feedback else "",
        },
        temperature=0.8, label=f"persona_simulation({mode})",
    )
