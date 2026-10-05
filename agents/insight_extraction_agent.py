"""
Insight Extraction Agent — machine-readable insights from survey and/or interview data.

Hybrid by design so numbers are trustworthy:
  * sentiment distribution, theme frequency/percentage, segment stats  -> computed in CODE from the database
  * theme discovery, agreement patterns, trends, contradictions, outliers -> LLM (structured, Zod-style Pydantic validated)
  * every persona_id the LLM returns is checked against real participants; hallucinated ids are dropped;
    evidence excerpts are copied from the DB (by reference), never taken from LLM-written quotes.
"""
from collections import Counter, defaultdict

from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import llm
from db.models import Experiment, Insight, InterviewMessage, Interview, Persona, Survey, SurveyQuestion, SurveyResponse
from schemas_m3 import InsightLLMOut
from services.errors import InvalidInput, NotFound
from utils.logging import get_logger, log_event

log = get_logger("insight_agent")
MAX_ITEMS = 300
EXCERPT = 280

SYSTEM = """You are an Insight Extraction Agent for synthetic user research. You receive persona metadata and their answers.
Identify, grounded ONLY in the data given (never invent):
- themes: recurring topics (e.g. price sensitivity, ease of use, trust, performance, customer support) with the persona_ids that raise them,
  a sentiment toward that topic (positive/neutral/negative/mixed) and up to 3 evidence refs (persona_id + question_key if a survey answer)
- agreement_patterns: statements most personas share
- behavioral_trends: differences by segment/age/occupation (name the segments)
- contradictions: topics where personas hold opposing stances (list each stance with its persona_ids)
- outliers: personas whose answers are unusual versus the rest, with a reason
Use persona ids exactly as given. Prefer 3-8 themes. Do not inflate positivity."""

USER = """Product: {product}
Research objective: {objective}

Personas (id | segment | age | occupation):
{personas}

Responses (persona_id | question_key | sentiment | answer):
{items}"""


def _excerpt(t: str) -> str:
    t = " ".join(t.split())
    return t if len(t) <= EXCERPT else t[: EXCERPT - 1] + "…"


async def _gather(s: AsyncSession, exp: Experiment, source: str, survey_id: str | None) -> list[dict]:
    items: list[dict] = []
    if source in ("survey", "combined"):
        q = select(SurveyResponse, SurveyQuestion.key).join(SurveyQuestion, SurveyQuestion.id == SurveyResponse.question_id) \
            .join(Survey, Survey.id == SurveyResponse.survey_id).where(Survey.experiment_id == exp.id, SurveyResponse.status == "completed")
        if survey_id:
            q = q.where(SurveyResponse.survey_id == survey_id)
        for r, key in (await s.execute(q)).all():
            items.append({"persona_id": r.persona_id, "key": key, "sentiment": r.sentiment or "neutral", "text": r.response})
    if source in ("interview", "combined"):
        q = select(InterviewMessage, Interview.persona_id).join(Interview, Interview.id == InterviewMessage.interview_id) \
            .where(Interview.experiment_id == exp.id, InterviewMessage.role == "persona")
        for m, pid in (await s.execute(q)).all():
            # interviews carry no per-message sentiment column; neutral unless validation says otherwise
            items.append({"persona_id": pid, "key": f"interview:{m.turn_number}", "sentiment": "neutral", "text": m.content})
    return items


async def extract_insights(s: AsyncSession, experiment_id: str, source: str = "combined", survey_id: str | None = None) -> dict:
    exp = await s.get(Experiment, experiment_id)
    if not exp:
        raise NotFound("experiment not found")
    log_event(log, "insight_extraction_started", experiment_id=experiment_id, source=source)
    items = await _gather(s, exp, source, survey_id)
    if not items:
        raise InvalidInput("no completed responses to analyse yet")
    pids = sorted({i["persona_id"] for i in items})
    personas = {p.id: p for p in (await s.scalars(select(Persona).where(Persona.id.in_(pids)))).all()}
    n = len(pids)

    # ---- deterministic statistics ----
    sc = Counter(i["sentiment"] for i in items)
    total = len(items)
    sentiment = {k: round(100 * sc.get(k, 0) / total, 1) for k in ("positive", "neutral", "negative", "mixed")}
    by_segment: dict = defaultdict(Counter)
    for i in items:
        by_segment[personas[i["persona_id"]].segment][i["sentiment"]] += 1
    segment_sentiment = {seg: {k: round(100 * c.get(k, 0) / sum(c.values()), 1) for k in ("positive", "neutral", "negative", "mixed")}
                         for seg, c in by_segment.items()}

    # ---- LLM analysis (bounded prompt) ----
    sample = items if len(items) <= MAX_ITEMS else items[:: -(-len(items) // MAX_ITEMS)]
    plist = "\n".join(f"{p.id} | {p.segment} | {p.age} | {p.occupation}" for p in personas.values())
    ilist = "\n".join(f"{i['persona_id']} | {i['key']} | {i['sentiment']} | {_excerpt(i['text'])}" for i in sample)
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("user", USER)])
    raw: InsightLLMOut = await llm.ainvoke_structured(
        prompt, InsightLLMOut,
        {"product": exp.product_description, "objective": exp.research_objectives, "personas": plist, "items": ilist},
        temperature=0.2, label="insight_extraction")

    valid = set(pids)
    lookup = {(i["persona_id"], i["key"]): i["text"] for i in items}

    def ids(xs):
        return sorted({x for x in xs if x in valid})

    themes = []
    for t in raw.themes:
        tp = ids(t.persona_ids)
        if not tp:
            continue
        ev = []
        for e in t.evidence[:3]:
            if e.persona_id in valid:
                text = lookup.get((e.persona_id, e.question_key)) or next((i["text"] for i in items if i["persona_id"] == e.persona_id), "")
                ev.append({"personaId": e.persona_id, "questionKey": e.question_key, "excerpt": _excerpt(text)})
        themes.append({"name": t.name, "description": t.description, "frequency": len(tp), "percentage": round(100 * len(tp) / n, 1),
                       "sentiment": t.sentiment, "personaIds": tp, "evidence": ev})
    themes.sort(key=lambda x: -x["frequency"])

    data = {
        "participants": n, "responsesAnalysed": total, "responsesInPrompt": len(sample),
        "themes": themes,
        "sentiment": sentiment, "segmentSentiment": segment_sentiment,
        "agreementPatterns": [{"statement": a.statement, "count": len(ids(a.persona_ids)), "of": n,
                               "summary": f"{len(ids(a.persona_ids))} of {n} personas: {a.statement}", "personaIds": ids(a.persona_ids)}
                              for a in raw.agreement_patterns if ids(a.persona_ids)],
        "behavioralTrends": [{"trend": t.trend, "segments": t.segments, "personaIds": ids(t.persona_ids)} for t in raw.behavioral_trends],
        "contradictions": [{"topic": c.topic, "positions": [{"stance": p.stance, "personaIds": ids(p.persona_ids)} for p in c.positions
                                                           if ids(p.persona_ids)]} for c in raw.contradictions],
        "outliers": [{"personaId": o.persona_id, "reason": o.reason} for o in raw.outliers if o.persona_id in valid],
    }
    row = Insight(experiment_id=experiment_id, source_type=source, data=data)
    s.add(row)
    await s.commit()
    log_event(log, "insight_extraction_completed", experiment_id=experiment_id, insight_id=row.id, themes=len(themes))
    return {"id": row.id, "experimentId": experiment_id, "sourceType": source, "createdAt": row.created_at.isoformat(), "data": data}
