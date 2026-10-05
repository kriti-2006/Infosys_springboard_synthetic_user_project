"""
Survey Agent (Milestone 3): all selected personas answer the same questions, concurrently but capped.

Flow per (persona, question):  retrieve memory -> generate -> normalise typed value -> heuristics + LLM consistency/realism
validation (one regeneration with feedback) -> persist -> memory update (only if validated).
Personas run concurrently (PERSONA_CONCURRENCY); a persona's questions run in order so later answers see earlier ones.
A failure is recorded as a `failed` response row and never aborts other personas. Re-running resumes: completed rows are skipped.
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agents import consistency_agent, persona_simulation_agent
from config import settings
from db import session as dbs
from db.models import Experiment, Persona, Survey, SurveyPersona, SurveyQuestion, SurveyResponse
from llm import LLMError
from services import experiment_context
from services.answer_validation import AnswerFormatError, QuestionSpec, normalise_value
from services.errors import Conflict, NotFound
from services.memory import memory_service
from utils.logging import get_logger, log_event

log = get_logger("survey_agent")
RUNNABLE = ("draft", "partial", "failed")
MAX_CONSECUTIVE_LLM_ERRORS = 3


def _now():
    return datetime.now(timezone.utc)


def spec_of(q: SurveyQuestion) -> QuestionSpec:
    return QuestionSpec(q.key, q.question, q.type, q.options, q.scale_min, q.scale_max)


async def claim_survey(session: AsyncSession, survey_id: str) -> None:
    """Atomically move a survey to 'running' (guards against duplicate concurrent execution)."""
    exists = await session.scalar(select(Survey.id).where(Survey.id == survey_id))
    if not exists:
        raise NotFound("survey not found")
    res = await session.execute(update(Survey).where(Survey.id == survey_id, Survey.status.in_(RUNNABLE))
                                .values(status="running", started_at=_now(), completed_at=None))
    await session.commit()
    if res.rowcount == 0:
        cur = await session.scalar(select(Survey.status).where(Survey.id == survey_id))
        raise Conflict(f"survey is already {cur}; it cannot be started again")


async def execute_survey(survey_id: str) -> dict:
    """Long-running part. Opens its own sessions (call after claim_survey)."""
    async with dbs.session_scope() as s:
        survey = await s.get(Survey, survey_id)
        experiment = await s.get(Experiment, survey.experiment_id)
        questions = list((await s.scalars(select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)
                                          .order_by(SurveyQuestion.order))).all())
        persona_ids = list((await s.scalars(select(SurveyPersona.persona_id).where(SurveyPersona.survey_id == survey_id))).all())
        context = await experiment_context.build_context(s, experiment, survey.research_objective)
        exp_id = experiment.id
    log_event(log, "survey_started", survey_id=survey_id, personas=len(persona_ids), questions=len(questions))

    sem = asyncio.Semaphore(settings.PERSONA_CONCURRENCY)

    async def run_persona(pid: str):
        async with sem:
            async with dbs.session_scope() as s:
                await _run_persona(s, survey_id, exp_id, pid, questions, context)

    results = await asyncio.gather(*(run_persona(p) for p in persona_ids), return_exceptions=True)
    for pid, r in zip(persona_ids, results):
        if isinstance(r, Exception):  # unexpected (e.g. DB) failure for this persona only
            log_event(log, "persona_run_crashed", level=40, survey_id=survey_id, persona_id=pid, error=str(r))

    return await finalize(survey_id, len(persona_ids) * len(questions))


async def finalize(survey_id: str, expected: int) -> dict:
    async with dbs.session_scope() as s:
        rows = (await s.execute(select(SurveyResponse.status, func.count()).where(SurveyResponse.survey_id == survey_id)
                                .group_by(SurveyResponse.status))).all()
        counts = {st: n for st, n in rows}
        done, failed = counts.get("completed", 0), counts.get("failed", 0)
        status = "completed" if done == expected else ("partial" if done > 0 else "failed")
        await s.execute(update(Survey).where(Survey.id == survey_id).values(
            status=status, completed_at=_now() if status == "completed" else None))
        await s.commit()
    log_event(log, "survey_completed", survey_id=survey_id, status=status, completed=done, failed=failed, expected=expected)
    return {"status": status, "expected": expected, "completed": done, "failed": failed}


async def _history_block(s: AsyncSession, survey_id: str, persona_id: str, qmap: dict) -> str:
    rows = (await s.scalars(select(SurveyResponse).where(
        SurveyResponse.survey_id == survey_id, SurveyResponse.persona_id == persona_id, SurveyResponse.status == "completed")
        .order_by(SurveyResponse.created_at))).all()
    return "\n".join(f"Q: {qmap[r.question_id].question}\nYour answer: {r.response}" for r in rows if r.question_id in qmap)


async def _run_persona(s: AsyncSession, survey_id, exp_id, persona_id, questions, context):
    persona = await s.get(Persona, persona_id)
    persona_text = experiment_context.persona_block(persona)
    qmap = {q.id: q for q in questions}
    existing = {r.question_id: r for r in (await s.scalars(select(SurveyResponse).where(
        SurveyResponse.survey_id == survey_id, SurveyResponse.persona_id == persona_id))).all()}
    consecutive = 0
    for q in questions:
        prior = existing.get(q.id)
        if prior and prior.status == "completed":
            continue  # idempotent resume
        if consecutive >= MAX_CONSECUTIVE_LLM_ERRORS:
            await _save(s, survey_id, q, persona_id, prior, status="failed", error="aborted after repeated LLM errors")
            continue
        try:
            memories = await memory_service.retrieve(s, persona_id, q.question)
            history = await _history_block(s, survey_id, persona_id, qmap)
            out = await _answer_with_validation(persona, persona_text, context, spec_of(q), memories, history)
            await _save(s, survey_id, q, persona_id, prior, status="completed", out=out)
            if out["validation"]["ok"]:
                await memory_service.apply_updates(s, persona_id, exp_id, out["answer"].memory_updates, f"survey:{survey_id}")
            consecutive = 0
            log_event(log, "persona_response_generated", survey_id=survey_id, persona_id=persona_id, question=q.key,
                      consistency=out["validation"].get("consistencyScore"), accepted=out["validation"]["ok"])
        except (LLMError, AnswerFormatError) as e:
            consecutive = consecutive + 1 if isinstance(e, LLMError) else 0
            log_event(log, "persona_response_failed", level=40, survey_id=survey_id, persona_id=persona_id, question=q.key,
                      error=str(e), kind=getattr(e, "kind", "format"))
            await _save(s, survey_id, q, persona_id, prior, status="failed", error=f"{getattr(e, 'kind', 'invalid_output')}: {e}"[:500])


async def _answer_with_validation(persona, persona_text, context, spec, memories, history) -> dict:
    """Generate -> normalise -> validate, with up to MAX_RESPONSE_ATTEMPTS. Last attempt is kept (flagged) if only consistency fails."""
    feedback, last = "", None
    mem_text = memory_service.format_memories(memories)
    for attempt in range(1, settings.MAX_RESPONSE_ATTEMPTS + 1):
        answer = await persona_simulation_agent.generate_answer(
            persona_block=persona_text, context=context, question=spec, memories=mem_text, history=history, feedback=feedback)
        try:
            value = normalise_value(spec, answer)
        except AnswerFormatError as e:
            feedback = str(e)
            if attempt == settings.MAX_RESPONSE_ATTEMPTS:
                raise
            continue
        v = await consistency_agent.validate(persona=persona, persona_text=persona_text, memories=mem_text, history=history,
                                             question=spec, answer=answer, value=value)
        last = {"answer": answer, "value": value, "validation": v.to_dict(), "attempts": attempt}
        if v.ok:
            return last
        feedback = v.feedback()
    last["validation"]["accepted"] = False  # kept but flagged; memory is NOT updated from it
    return last


async def _save(s: AsyncSession, survey_id, q, persona_id, prior, *, status, out=None, error=None):
    fields = dict(status=status, error=error)
    if out:
        a, v = out["answer"], out["validation"]
        fields.update(response=a.answer, value=out["value"], sentiment=a.sentiment, confidence=a.confidence,
                      consistency_score=v.get("consistencyScore"), validation=v, attempts=out["attempts"], error=None)
    try:
        if prior:
            for k, val in fields.items():
                setattr(prior, k, val)
        else:
            s.add(SurveyResponse(survey_id=survey_id, question_id=q.id, persona_id=persona_id, **fields))
        await s.commit()
    except IntegrityError:  # duplicate retry/concurrent run: the unique constraint protects us
        await s.rollback()
        log_event(log, "duplicate_response_ignored", survey_id=survey_id, persona_id=persona_id, question=q.key)
