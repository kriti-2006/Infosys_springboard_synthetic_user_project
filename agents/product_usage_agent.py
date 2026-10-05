"""
Product Usage Scoring Agent — "Would this persona use this product?"
Score = structured LLM evaluation grounded in persona attributes + retrieved memories + the persona's own prior survey
answers/interview stance (evidence), NOT random numbers. Decision label is a deterministic function of the score.
Aggregation (overall + per segment) is computed in code from stored scores.
"""
import asyncio
from collections import defaultdict

from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import llm
from config import settings
from db import session as dbs
from db.models import Experiment, InterviewMessage, Interview, Persona, ProductUsageScore, SurveyQuestion, SurveyResponse
from schemas_m3 import UsageEval, decision_from_score
from services import experiment_context
from services.errors import NotFound
from services.memory import memory_service
from utils.logging import get_logger, log_event

log = get_logger("usage_agent")

SYSTEM = """You estimate whether ONE specific person would actually use a product, as a careful market researcher.
Reason from the person's age, occupation, behavior, psychology, goals and frustrations, their remembered facts, and what they have
already said (evidence). Score 0-100 (0 = definitely never, 50 = undecided, 100 = definitely and regularly). Be calibrated, not flattering:
price sensitivity, habits, trust and effort matter. Give concrete reasoning that cites the person's attributes, 2-5 weighted factors, and a
confidence 0-1 (lower when there is little evidence)."""

USER = """Product context:
{context}

Person:
{persona}

Remembered facts:
{memories}

Evidence from this person's earlier answers (may be empty):
{evidence}"""


async def _evidence(s: AsyncSession, persona_id: str) -> str:
    lines = []
    rows = (await s.execute(select(SurveyResponse, SurveyQuestion.question).join(SurveyQuestion, SurveyQuestion.id == SurveyResponse.question_id)
                            .where(SurveyResponse.persona_id == persona_id, SurveyResponse.status == "completed")
                            .order_by(SurveyResponse.created_at.desc()).limit(8))).all()
    lines += [f"Survey — Q: {q} | A: {r.response[:240]}" for r, q in rows]
    msgs = (await s.scalars(select(InterviewMessage).join(Interview, Interview.id == InterviewMessage.interview_id)
                            .where(Interview.persona_id == persona_id, InterviewMessage.role == "persona")
                            .order_by(InterviewMessage.created_at.desc()).limit(4))).all()
    lines += [f"Interview — {m.content[:240]}" for m in msgs]
    return "\n".join(lines) or "(none)"


async def _score_one(experiment_id: str, persona_id: str, context: str) -> dict:
    async with dbs.session_scope() as s:
        p = await s.get(Persona, persona_id)
        mems = await memory_service.retrieve(s, persona_id, "would use this product price habits trust switch regularly")
        ev = await _evidence(s, persona_id)
        prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("user", USER)])
        res: UsageEval = await llm.ainvoke_structured(
            prompt, UsageEval, {"context": context, "persona": experiment_context.persona_block(p),
                                "memories": memory_service.format_memories(mems), "evidence": ev},
            temperature=0.2, label="product_usage")
        decision = decision_from_score(res.score)
        row = await s.scalar(select(ProductUsageScore).where(ProductUsageScore.experiment_id == experiment_id,
                                                              ProductUsageScore.persona_id == persona_id))
        vals = dict(score=res.score, decision=decision, reasoning=res.reasoning, confidence=res.confidence,
                    factors=[f.model_dump() for f in res.factors])
        if row:
            for k, v in vals.items():
                setattr(row, k, v)
        else:
            s.add(ProductUsageScore(experiment_id=experiment_id, persona_id=persona_id, **vals))
        await s.commit()
        log_event(log, "usage_scored", persona_id=persona_id, score=res.score, decision=decision)
        return {"personaId": persona_id, "status": "ok"}


async def score_experiment(s: AsyncSession, experiment_id: str, persona_ids: list[str] | None = None) -> dict:
    exp = await s.get(Experiment, experiment_id)
    if not exp:
        raise NotFound("experiment not found")
    q = select(Persona.id).where(Persona.experiment_id == experiment_id)
    if persona_ids:
        q = q.where(Persona.id.in_(persona_ids))
    ids = list((await s.scalars(q)).all())
    if not ids:
        raise NotFound("no personas found for this experiment")
    context = await experiment_context.build_context(s, exp)
    sem = asyncio.Semaphore(settings.PERSONA_CONCURRENCY)

    async def run(pid):
        async with sem:
            try:
                return await _score_one(experiment_id, pid, context)
            except Exception as e:  # noqa: BLE001 - one persona failing must not sink the rest
                log_event(log, "usage_score_failed", level=40, persona_id=pid, error=str(e))
                return {"personaId": pid, "status": "failed", "error": str(e)[:300]}

    results = await asyncio.gather(*(run(i) for i in ids))
    return {"scored": sum(r["status"] == "ok" for r in results), "failed": [r for r in results if r["status"] == "failed"]}


async def get_scores(s: AsyncSession, experiment_id: str) -> dict:
    if not await s.get(Experiment, experiment_id):
        raise NotFound("experiment not found")
    rows = (await s.execute(select(ProductUsageScore, Persona).join(Persona, Persona.id == ProductUsageScore.persona_id)
                            .where(ProductUsageScore.experiment_id == experiment_id))).all()
    scores = [{"personaId": p.id, "personaName": p.name, "segment": p.segment, "score": r.score, "decision": r.decision,
               "confidence": r.confidence, "reasoning": r.reasoning, "factors": r.factors} for r, p in rows]
    seg: dict = defaultdict(list)
    for x in scores:
        seg[x["segment"]].append(x["score"])
    return {
        "overallLikelihood": round(sum(x["score"] for x in scores) / len(scores), 1) if scores else None,
        "bySegment": {k: {"likelihood": round(sum(v) / len(v), 1), "personas": len(v)} for k, v in seg.items()},
        "scores": scores,
    }
