"""Pydantic schemas for Milestone 3: API payloads AND structured-LLM-output targets (validated before any DB write)."""
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

QuestionType = Literal["open_ended", "yes_no", "single_choice", "multiple_choice", "rating", "likert", "numeric", "short_answer"]
Sentiment = Literal["positive", "neutral", "negative", "mixed"]
Decision = Literal["very_unlikely", "unlikely", "neutral", "likely", "very_likely"]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------------- API: experiments / personas ----------------
class ExperimentCreate(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    product_description: str = Field(min_length=1, max_length=5000)
    target_audience: str = Field(default="", max_length=3000)
    research_objectives: str = Field(default="", max_length=3000)


class PersonaGenerateRequest(CamelModel):
    count: int = Field(default=5, ge=1, le=20)


# ---------------- API: surveys ----------------
class QuestionIn(CamelModel):
    question_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_\-]+$")
    question: str = Field(min_length=3, max_length=1000)
    type: QuestionType
    options: Optional[List[str]] = None
    scale_min: int = 1
    scale_max: int = 5

    @model_validator(mode="after")
    def _check(self):
        if self.type in ("single_choice", "multiple_choice"):
            if not self.options or len(set(self.options)) < 2:
                raise ValueError(f"{self.type} questions need at least 2 distinct options")
        elif self.options:
            raise ValueError(f"options are only allowed for choice questions, not {self.type}")
        if self.type in ("rating", "likert") and self.scale_min >= self.scale_max:
            raise ValueError("scale_min must be < scale_max")
        if self.type in ("rating", "likert") and self.scale_max - self.scale_min > 10:
            raise ValueError("scale too wide (max 11 points)")
        return self


class SurveyCreate(CamelModel):
    experiment_id: str
    title: str = Field(min_length=1, max_length=300)
    research_objective: str = Field(default="", max_length=3000)
    questions: List[QuestionIn] = Field(min_length=1, max_length=50)
    persona_ids: List[str] = Field(min_length=1, max_length=100)

    @field_validator("questions")
    @classmethod
    def _unique(cls, qs):
        ids = [q.question_id for q in qs]
        if len(ids) != len(set(ids)):
            raise ValueError("questionId values must be unique within a survey")
        return qs


class InterviewCreate(CamelModel):
    experiment_id: str
    persona_id: str


class InterviewMessageIn(CamelModel):
    content: str = Field(min_length=1, max_length=2000)
    client_message_id: Optional[str] = Field(default=None, max_length=100, description="idempotency key")


# ---------------- LLM output: persona answer ----------------
class MemoryUpdate(BaseModel):
    layer: Literal["long_term", "experiment", "derived"]
    content: str = Field(description="one short first-person-neutral fact/stance, e.g. 'Is very price sensitive; always compares delivery fees'")
    importance: float = Field(ge=0, le=1)


class PersonaAnswer(BaseModel):
    answer: str = Field(description="the persona's answer in their own voice (text form of their answer)")
    value: Optional[Union[bool, int, float, str, List[str]]] = Field(
        default=None,
        description="typed answer: yes_no -> true/false; rating/likert/numeric -> number; single_choice -> one option string; "
                    "multiple_choice -> list of option strings; null for open_ended/short_answer",
    )
    sentiment: Sentiment
    confidence: float = Field(ge=0, le=1)
    memory_updates: List[MemoryUpdate] = Field(default_factory=list, description="0-3 NEW stable facts/stances revealed by this answer")


# ---------------- LLM output: validation ----------------
IssueType = Literal["demographic_contradiction", "behavioral_contradiction", "preference_contradiction",
                    "personality_contradiction", "previous_answer_contradiction", "other"]


class ConsistencyIssue(BaseModel):
    type: IssueType
    description: str


class ConsistencyResult(BaseModel):
    consistent: bool
    confidence: float = Field(ge=0, le=1)
    issues: List[ConsistencyIssue] = Field(default_factory=list)


class RealismResult(BaseModel):
    relevant: bool = Field(description="is the answer relevant to the question")
    answers_the_question: bool
    grounded_in_persona: bool
    too_generic: bool
    plausible_human: bool
    too_verbose: bool
    meta_language: bool = Field(description="mentions being an AI/model/persona/simulation")
    score: float = Field(ge=0, le=1, description="overall realism 0-1")
    issues: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    consistency: ConsistencyResult
    realism: RealismResult


# ---------------- LLM output: insights ----------------
class EvidenceRef(BaseModel):
    persona_id: str
    question_key: Optional[str] = Field(default=None, description="question id, if the evidence is a survey answer")


class ThemeOut(BaseModel):
    name: str
    description: str = ""
    sentiment: Sentiment
    persona_ids: List[str]
    evidence: List[EvidenceRef] = Field(default_factory=list, description="up to 3 supporting answers")


class AgreementOut(BaseModel):
    statement: str
    persona_ids: List[str]


class TrendOut(BaseModel):
    trend: str
    segments: List[str] = Field(default_factory=list)
    persona_ids: List[str] = Field(default_factory=list)


class StanceOut(BaseModel):
    stance: str
    persona_ids: List[str]


class ContradictionOut(BaseModel):
    topic: str
    positions: List[StanceOut]


class OutlierOut(BaseModel):
    persona_id: str
    reason: str


class InsightLLMOut(BaseModel):
    themes: List[ThemeOut]
    agreement_patterns: List[AgreementOut] = Field(default_factory=list)
    behavioral_trends: List[TrendOut] = Field(default_factory=list)
    contradictions: List[ContradictionOut] = Field(default_factory=list)
    outliers: List[OutlierOut] = Field(default_factory=list)


class InsightRequest(CamelModel):
    source: Literal["survey", "interview", "combined"] = "combined"
    survey_id: Optional[str] = None


# ---------------- LLM output: product usage ----------------
class UsageFactor(BaseModel):
    factor: str
    impact: Literal["positive", "negative"]
    weight: float = Field(ge=0, le=1)


class UsageEval(BaseModel):
    score: int = Field(ge=0, le=100, description="0-100 likelihood this persona would use the product")
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    factors: List[UsageFactor] = Field(default_factory=list)


def decision_from_score(score: int) -> Decision:
    """Deterministic score->label mapping (bands of 20)."""
    if score < 20:
        return "very_unlikely"
    if score < 40:
        return "unlikely"
    if score < 60:
        return "neutral"
    if score < 80:
        return "likely"
    return "very_likely"


def any_to_jsonable(v: Any) -> Any:
    return v
