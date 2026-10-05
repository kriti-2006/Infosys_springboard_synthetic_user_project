"""
Persona Consistency Agent — heuristic checks + LLM validation (consistency AND realism).

consistency_score = confidence if consistent else (1 - confidence)  -> 0..1, higher = more consistent.
`ok` is False when: any hard heuristic issue, OR LLM says inconsistent, OR realism problems (not relevant / doesn't answer /
meta language / implausible / too verbose) or realism score < 0.5.
"""
from dataclasses import dataclass, field

from langchain_core.prompts import ChatPromptTemplate

import llm
from config import settings
from schemas_m3 import PersonaAnswer, ValidationResult
from services.answer_validation import QuestionSpec, heuristic_checks

SYSTEM = """You are a strict QA reviewer for synthetic user research. Decide whether ONE answer from a simulated person is
(A) CONSISTENT with that person and (B) REALISTIC.

A) Consistency — flag only REAL contradictions (nuance is fine), using these issue types:
 - demographic_contradiction: conflicts with age/occupation/life stage (e.g. age 22 claiming 25 years in an executive role)
 - behavioral_contradiction: conflicts with behavioral patterns (e.g. "very price sensitive" saying "I never consider price")
 - preference_contradiction: conflicts with stated preferences (e.g. prefers Android, says iPhone is always preferred)
 - personality_contradiction: conflicts with personality (e.g. risk averse, enjoys significant financial risks)
 - previous_answer_contradiction: conflicts with earlier answers/turns or remembered facts (e.g. said No to using it, later says uses it daily)
 - other
B) Realism: relevant to the question? answers the actual question? grounded in this persona (not generic)? plausible human wording?
   excessively verbose? contains AI/meta language?
Return confidence 0-1 for your consistency verdict."""

USER = """Persona:
{persona}

Remembered facts:
{memories}

Earlier answers / turns:
{history}

Question ({qtype}): {question}

Answer to review:
{answer}
(typed value: {value})"""


@dataclass
class ValidationOutcome:
    ok: bool
    consistency_score: float | None
    issues: list[dict] = field(default_factory=list)
    heuristic_issues: list[str] = field(default_factory=list)
    llm_result: dict | None = None
    accepted: bool = True

    def feedback(self) -> str:
        msgs = list(self.heuristic_issues) + [i["description"] for i in self.issues]
        if self.llm_result:
            msgs += self.llm_result.get("realism", {}).get("issues", [])
        return "; ".join(dict.fromkeys(m for m in msgs if m)) or "response failed validation"

    def to_dict(self) -> dict:
        return {"ok": self.ok, "accepted": self.accepted, "consistencyScore": self.consistency_score,
                "issues": self.issues, "heuristicIssues": self.heuristic_issues, "llm": self.llm_result}


async def validate(*, persona, persona_text: str, memories: str, history: str, question: QuestionSpec,
                   answer: PersonaAnswer, value) -> ValidationOutcome:
    h = heuristic_checks(question, answer, persona.age)
    if h.issues:  # cheap rejection, no LLM call
        return ValidationOutcome(ok=False, consistency_score=None, heuristic_issues=h.issues)
    if not settings.SURVEY_LLM_VALIDATION:
        return ValidationOutcome(ok=True, consistency_score=None)
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("user", USER)])
    res: ValidationResult = await llm.ainvoke_structured(
        prompt, ValidationResult,
        {"persona": persona_text, "memories": memories, "history": history or "(none)", "qtype": question.type,
         "question": question.text, "answer": answer.answer, "value": value},
        temperature=0.0, label="consistency_validation",
    )
    c, r = res.consistency, res.realism
    score = round(c.confidence if c.consistent else 1 - c.confidence, 3)
    realism_ok = (r.relevant and r.answers_the_question and r.plausible_human and not r.meta_language
                  and not r.too_verbose and r.score >= 0.5)
    ok = c.consistent and realism_ok
    return ValidationOutcome(ok=ok, consistency_score=score, issues=[i.model_dump() for i in c.issues],
                             llm_result=res.model_dump())
