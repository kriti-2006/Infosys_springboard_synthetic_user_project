"""
Interview-related functionality for the platform.

This module has two distinct pieces:

1. PersonaInterviewSession / start_persona_interview() — the REQUIRED
   "Interview Mode": the user converses directly with a SELECTED audience
   Persona (the same object type produced by persona_agent.py). The persona
   stays consistent with its identity, personality, behavioral patterns,
   psychological profile, goals and pain points, keeps a stable opinion of
   the product, and maintains its own isolated conversation history across
   turns (a new PersonaInterviewSession instance per persona/session, so
   histories never leak between personas).

2. generate_interview_persona() / InterviewSession — the pre-existing mock
   PLACEMENT interview simulator, where a synthetic *interviewer* persona
   (InterviewPersona, a separate schema from Persona) interviews the user
   and produces feedback. This is kept because it doesn't interfere with
   anything above, but it is NOT the required Interview Mode — it's a
   Placement-Prep-AI-specific bonus feature.

Memory in both cases is literal conversational memory per persona per
session, kept via LangChain's message history classes, separate from the
LangGraph state/checkpointer used for the survey pipeline.
"""
import logging
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from llm import invoke_structured, invoke_chat
from schemas import InterviewPersona, InterviewFeedback, Persona

log_ = logging.getLogger(__name__)


# ---------- REQUIRED INTERVIEW MODE: user <-> selected audience Persona ----------

class PersonaInterviewSession:
    """
    A stateful, memory-carrying conversation between the user and ONE
    selected audience `Persona` (from persona_agent.py). The persona answers
    the user's questions in character, staying consistent with its identity,
    personality traits, behavioral patterns, psychological profile, goals
    and pain points, and keeping a stable opinion of the product across the
    whole conversation.

    Each instance owns its own `history` list, so two sessions (even for the
    same persona) never share conversation state — create a new session per
    persona per interview to keep histories isolated.
    """

    def __init__(self, persona: Persona, product_description: str = "", temperature: float = 0.6):
        self.persona = persona
        self.product_description = product_description
        self.history: List[BaseMessage] = []
        self._temperature = temperature

        self._system_prompt = (
            f"You are {persona.name}, a real person being interviewed about a product. "
            f"Age: {persona.age}. Occupation: {persona.occupation}. "
            f"Background: {persona.background} "
            f"Personality traits: {', '.join(persona.personality_traits)}. "
            f"Behavioral patterns: {', '.join(persona.behavioral_patterns)}. "
            f"Psychological profile: {persona.psychological_profile}. "
            f"Goals: {', '.join(persona.goals)}. "
            f"Pain points: {', '.join(persona.pain_points)}. "
            f"Tech savviness: {persona.tech_savviness}. "
            f"Communication style: {persona.communication_style}. "
            + (f"The product being discussed: {product_description} " if product_description else "")
            + "Stay fully and consistently in character for the entire interview: never break "
              "character, never mention you are an AI, and never contradict opinions about the "
              "product you have already expressed earlier in this same conversation. Answer the "
              "interviewer's questions the way this specific person genuinely would, in their own "
              "communication style — do not be artificially positive."
        )

    def respond(self, user_message: str) -> str:
        """Answer one interviewer turn, appending to and reading from history."""
        self.history.append(HumanMessage(content=user_message))

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._system_prompt),
            MessagesPlaceholder("history"),
        ])
        try:
            ai_message = invoke_chat(
                prompt,
                {"history": self.history},
                temperature=self._temperature,
                label=f"persona_interview(persona={self.persona.id})",
            )
        except Exception as e:
            log_.error(
                "PersonaInterviewSession LLM call failed for persona %s on every candidate model: %s",
                self.persona.id, e,
            )
            raise RuntimeError(
                f"persona_interview: failed to get a response from persona {self.persona.id}"
            ) from e

        self.history.append(AIMessage(content=ai_message.content))
        return ai_message.content


def start_persona_interview(persona: Persona, product_description: str = "") -> PersonaInterviewSession:
    """
    Start (and return) a new, isolated interview session with a selected
    audience persona. Call `.respond(user_message)` on the returned session
    for each turn; its `.history` carries the full conversation.
    """
    return PersonaInterviewSession(persona, product_description=product_description)


INTERVIEW_PERSONA_SYSTEM_PROMPT = """You design synthetic interviewer personas for a
campus placement prep platform. Given a company name and round type
(HR / Technical / Coding / Managerial), create a realistic interviewer persona
students would actually meet, including a distinctive tone and 2-3 sample
opening lines worth of style, plus what this interviewer actually screens for.
"""


def generate_interview_persona(company: str, round_type: str) -> InterviewPersona:
    prompt = ChatPromptTemplate.from_messages([
        ("system", INTERVIEW_PERSONA_SYSTEM_PROMPT),
        ("user", "Company: {company}\nRound type: {round_type}\nGenerate the interviewer persona."),
    ])
    try:
        return invoke_structured(
            prompt,
            InterviewPersona,
            {"company": company, "round_type": round_type},
            temperature=0.8,
            label="generate_interview_persona",
        )
    except Exception as e:
        log_.error("generate_interview_persona LLM call failed on every candidate model: %s", e)
        raise RuntimeError("generate_interview_persona: failed to generate interviewer persona") from e


class InterviewSession:
    """
    Holds the running conversation (memory) for one mock interview with one
    persona. Call .respond(student_message) each turn; call .get_feedback()
    at the end to run the weak-area detection agent over the transcript.
    """

    def __init__(self, persona: InterviewPersona):
        self.persona = persona
        self.history: List[BaseMessage] = []
        self._temperature = 0.6

        self._system_prompt = (
            f"You are {persona.name}, {persona.role} at a company using the "
            f"style: {persona.company_style}. Tone: {persona.tone}. "
            f"Your focus areas when evaluating the candidate: {', '.join(persona.focus_areas)}. "
            "Stay fully in character for the entire interview. Ask one question "
            "at a time, react naturally to the candidate's answers (follow-ups, "
            "mild pushback if an answer is vague), and keep the pacing of a real interview."
        )

    def respond(self, student_message: str) -> str:
        self.history.append(HumanMessage(content=student_message))

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._system_prompt),
            MessagesPlaceholder("history"),
        ])
        try:
            ai_message = invoke_chat(
                prompt,
                {"history": self.history},
                temperature=self._temperature,
                label=f"interview_session(persona={self.persona.id})",
            )
        except Exception as e:
            log_.error(
                "InterviewSession LLM call failed for persona %s on every candidate model: %s",
                self.persona.id, e,
            )
            raise RuntimeError(
                f"interview_session: failed to get a response from interviewer {self.persona.id}"
            ) from e

        self.history.append(AIMessage(content=ai_message.content))
        return ai_message.content

    def opening_line(self) -> str:
        line = self.persona.sample_opening_line
        self.history.append(AIMessage(content=line))
        return line

    def get_feedback(self) -> InterviewFeedback:
        transcript = "\n".join(
            f"{'Interviewer' if isinstance(m, AIMessage) else 'Candidate'}: {m.content}"
            for m in self.history
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a placement-readiness evaluator. Read the mock interview transcript "
             "and produce honest, specific, actionable feedback for the candidate. "
             "Score conservatively — this is meant to help them improve, not flatter them."),
            ("user", "Transcript:\n{transcript}\n\nProduce the structured feedback now."),
        ])
        try:
            return invoke_structured(
                prompt,
                InterviewFeedback,
                {"transcript": transcript},
                temperature=0.2,
                label=f"interview_session_feedback(persona={self.persona.id})",
            )
        except Exception as e:
            log_.error(
                "InterviewSession.get_feedback LLM call failed for persona %s on every candidate model: %s",
                self.persona.id, e,
            )
            raise RuntimeError(
                f"interview_session: failed to generate feedback for persona {self.persona.id}"
            ) from e
