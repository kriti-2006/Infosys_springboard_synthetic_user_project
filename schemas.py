"""
Pydantic models used as structured-output targets for the LLM.
Forcing the model to fill these schemas (via `with_structured_output`)
is what keeps persona/survey/insight generation reliable instead of
hoping the LLM formats free text correctly.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ---------- PERSONA ----------

class Persona(BaseModel):
    id: str = Field(description="short unique slug, e.g. 'p1_riya_tier3_cse'")
    name: str
    age: int
    occupation: str = Field(description="e.g. 'Final-year B.Tech CSE student, Tier-3 college'")
    background: str = Field(description="2-3 sentences of relevant life/education/career context")
    personality_traits: List[str] = Field(description="4-6 adjectives, e.g. ['anxious', 'diligent']")
    behavioral_patterns: List[str] = Field(
        description="3-5 concrete, observable habits/behaviors relevant to the product domain, "
                     "e.g. ['checks reviews before buying', 'abandons forms longer than 2 minutes']"
    )
    psychological_profile: str = Field(
        description="1-2 sentences on this persona's underlying motivations, fears, decision-making "
                     "style and emotional relationship to the product domain (deeper than personality_traits)"
    )
    goals: List[str] = Field(description="what this persona wants from the product")
    pain_points: List[str] = Field(description="frustrations relevant to the product domain")
    tech_savviness: Literal["low", "medium", "high"]
    communication_style: str = Field(description="how they talk/write, e.g. 'formal, hesitant, over-explains'")
    persona_summary: str = Field(description="one-paragraph natural-language summary an interviewer could read aloud")


class PersonaSet(BaseModel):
    personas: List[Persona]


# ---------- SURVEY ----------

class SurveyQuestion(BaseModel):
    id: str
    text: str
    question_type: Literal["likert_1_5", "open_ended", "multiple_choice", "yes_no"]
    options: Optional[List[str]] = Field(
        default=None, description="only for multiple_choice; null otherwise"
    )
    rationale: str = Field(description="why this question matters for the product decision at hand")


class SurveySet(BaseModel):
    questions: List[SurveyQuestion]


# ---------- SURVEY RESPONSES ----------

class SurveyAnswer(BaseModel):
    question_id: str
    answer: str = Field(description="the persona's answer, in their own voice/style")
    sentiment: Literal["positive", "neutral", "negative", "mixed"]
    confidence: float = Field(ge=0, le=1, description="how strongly the persona feels about this answer")


class PersonaSurveyResponse(BaseModel):
    persona_id: str
    answers: List[SurveyAnswer]


# ---------- INSIGHTS ----------

class Theme(BaseModel):
    title: str
    description: str
    supporting_persona_ids: List[str]
    prevalence: Literal["low", "medium", "high"]


class InsightReport(BaseModel):
    executive_summary: str
    overall_sentiment: Literal["positive", "neutral", "negative", "mixed"]
    key_themes: List[Theme]
    notable_quotes: List[str] = Field(description="short paraphrased/attributed quotes, persona_id in brackets")
    weak_areas_or_risks: List[str] = Field(description="risks for the product, or in placement-prep context, common weak areas surfaced")
    recommendations: List[str]


# ---------- INTERVIEW MODE (bonus, for the Placement Prep use case) ----------

class InterviewPersona(BaseModel):
    id: str
    name: str
    role: str = Field(description="e.g. 'Strict Infosys HR Round Interviewer'")
    company_style: str = Field(description="company-specific interview style notes")
    tone: str = Field(description="e.g. 'formal, terse, probing follow-ups'")
    focus_areas: List[str] = Field(description="e.g. ['communication', 'attitude fit', 'basic CS fundamentals']")
    sample_opening_line: str


class InterviewFeedback(BaseModel):
    strengths: List[str]
    weak_areas: List[str]
    communication_score: int = Field(ge=1, le=10)
    technical_score: int = Field(ge=1, le=10)
    confidence_score: int = Field(ge=1, le=10)
    actionable_next_steps: List[str]
