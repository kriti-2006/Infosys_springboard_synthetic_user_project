from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents import survey_execution_agent as sa
from api import serializers as ser
from db.models import Experiment, Persona, Survey, SurveyPersona, SurveyQuestion, SurveyResponse
from db.session import get_session
from schemas_m3 import SurveyCreate
from services.errors import InvalidInput, NotFound
from workers import survey_worker

router = APIRouter(prefix="/surveys", tags=["surveys"])


@router.post("", status_code=201)
async def create_survey(body: SurveyCreate, s: AsyncSession = Depends(get_session)):
    if not await s.get(Experiment, body.experiment_id):
        raise NotFound("experiment not found")
    pids = list(dict.fromkeys(body.persona_ids))
    found = set((await s.scalars(select(Persona.id).where(Persona.id.in_(pids), Persona.experiment_id == body.experiment_id))).all())
    if missing := [p for p in pids if p not in found]:
        raise NotFound(f"personas not found in this experiment: {missing}")
    survey = Survey(experiment_id=body.experiment_id, title=body.title, research_objective=body.research_objective)
    s.add(survey)
    await s.flush()
    for i, q in enumerate(body.questions):
        s.add(SurveyQuestion(survey_id=survey.id, key=q.question_id, question=q.question, type=q.type, options=q.options,
                             scale_min=q.scale_min, scale_max=q.scale_max, order=i))
    s.add_all(SurveyPersona(survey_id=survey.id, persona_id=p) for p in pids)
    await s.commit()
    return await _detail(s, survey.id)


async def _detail(s: AsyncSession, survey_id: str) -> dict:
    sv = await s.get(Survey, survey_id)
    if not sv:
        raise NotFound("survey not found")
    qs = (await s.scalars(select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id).order_by(SurveyQuestion.order))).all()
    pids = (await s.scalars(select(SurveyPersona.persona_id).where(SurveyPersona.survey_id == survey_id))).all()
    counts = dict((await s.execute(select(SurveyResponse.status, func.count()).where(SurveyResponse.survey_id == survey_id)
                                   .group_by(SurveyResponse.status))).all())
    return {"id": sv.id, "experimentId": sv.experiment_id, "title": sv.title, "researchObjective": sv.research_objective,
            "status": sv.status, "createdAt": sv.created_at.isoformat(),
            "completedAt": sv.completed_at.isoformat() if sv.completed_at else None,
            "questions": [ser.question(q) for q in qs], "personaIds": list(pids),
            "progress": {"expected": len(qs) * len(pids), "completed": counts.get("completed", 0), "failed": counts.get("failed", 0)}}


@router.get("/{survey_id}")
async def get_survey(survey_id: str, s: AsyncSession = Depends(get_session)):
    return await _detail(s, survey_id)


@router.post("/{survey_id}/run", status_code=202)
async def run_survey(survey_id: str, wait: bool = False, s: AsyncSession = Depends(get_session)):
    """Starts (or resumes, if partial/failed) the survey. 409 if already running/completed. wait=true blocks until done."""
    await sa.claim_survey(s, survey_id)
    task = survey_worker.launch(survey_id)
    if wait:
        return {"surveyId": survey_id, **(await task)}
    return {"surveyId": survey_id, "status": "running"}


@router.get("/{survey_id}/results")
async def results(survey_id: str, s: AsyncSession = Depends(get_session)):
    detail = await _detail(s, survey_id)
    qmap = {q["id"]: q for q in detail["questions"]}
    pmap = {p.id: p for p in (await s.scalars(select(Persona).where(Persona.id.in_(detail["personaIds"])))).all()}
    rows = (await s.scalars(select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
                            .order_by(SurveyResponse.persona_id, SurveyResponse.created_at))).all()
    by_persona: dict = {}
    failures = []
    for r in rows:
        q = qmap[r.question_id]
        if r.status == "failed":
            failures.append({"personaId": r.persona_id, "questionId": q["questionId"], "status": "failed", "error": r.error})
            continue
        by_persona.setdefault(r.persona_id, []).append({
            "questionId": q["questionId"], "question": q["question"], "type": q["type"], "response": r.response, "value": r.value,
            "sentiment": r.sentiment, "confidence": r.confidence, "consistencyScore": r.consistency_score,
            "flagged": bool(r.validation and not r.validation.get("accepted", True)), "createdAt": r.created_at.isoformat()})
    return {"survey": {k: detail[k] for k in ("id", "title", "status", "progress")},
            "personas": [{"personaId": pid, "name": pmap[pid].name if pid in pmap else None,
                          "segment": pmap[pid].segment if pid in pmap else None, "responses": by_persona.get(pid, [])}
                         for pid in detail["personaIds"]],
            "failures": failures}
