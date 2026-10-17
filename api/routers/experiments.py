import asyncio
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api import serializers as ser
from db.models import Experiment, ExperimentDocument, Persona, Survey
from db.session import get_session
from schemas import Persona as PersonaSchema
from schemas_m3 import ExperimentCreate, PersonaGenerateRequest
from services.errors import NotFound
from services.files import upload_service
from services.segments import classify_segment

router = APIRouter(prefix="/experiments", tags=["experiments"])


async def _exp(s: AsyncSession, experiment_id: str) -> Experiment:
    e = await s.get(Experiment, experiment_id)
    if not e:
        raise NotFound("experiment not found")
    return e


def _to_row(experiment_id: str, p: PersonaSchema, key: str | None = None) -> Persona:
    return Persona(experiment_id=experiment_id, key=key or p.id, name=p.name, age=p.age, occupation=p.occupation,
                   personality=p.personality_traits, behavioral_patterns=p.behavioral_patterns,
                   psychological_profile=p.psychological_profile, segment=classify_segment(p.occupation, p.background),
                   profile=p.model_dump())


@router.post("", status_code=201)
async def create_experiment(body: ExperimentCreate, s: AsyncSession = Depends(get_session)):
    e = Experiment(name=body.name, product_description=body.product_description, target_audience=body.target_audience,
                   research_objectives=body.research_objectives)
    s.add(e)
    await s.commit()
    return ser.experiment(e)


@router.get("")
async def list_experiments(s: AsyncSession = Depends(get_session)):
    rows = (await s.scalars(select(Experiment).order_by(Experiment.created_at.desc()))).all()
    if not rows:
        return []
    ids = [e.id for e in rows]
    persona_counts = dict((await s.execute(select(Persona.experiment_id, func.count())
                                           .where(Persona.experiment_id.in_(ids)).group_by(Persona.experiment_id))).all())
    survey_counts = dict((await s.execute(select(Survey.experiment_id, func.count())
                                          .where(Survey.experiment_id.in_(ids)).group_by(Survey.experiment_id))).all())
    return [{**ser.experiment(e), "personaCount": persona_counts.get(e.id, 0), "surveyCount": survey_counts.get(e.id, 0)}
            for e in rows]


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str, s: AsyncSession = Depends(get_session)):
    return ser.experiment(await _exp(s, experiment_id))


@router.post("/{experiment_id}/personas/generate", status_code=201)
async def generate_personas(experiment_id: str, body: PersonaGenerateRequest, s: AsyncSession = Depends(get_session)):
    """Reuses the Milestone-2 Persona Generation Agent unchanged, then persists its output."""
    from agents.persona_agent import persona_agent_node
    e = await _exp(s, experiment_id)
    state = {"product_description": e.product_description, "target_audience": e.target_audience,
             "research_goal": e.research_objectives or "general product validation", "num_personas": body.count, "log": []}
    out = await asyncio.to_thread(persona_agent_node, state)  # M2 agent is synchronous
    rows = [_to_row(e.id, p, key=f"{p.id}-{uuid.uuid4().hex[:6]}") for p in out["personas"]]
    s.add_all(rows)
    await s.commit()
    return [ser.persona(r) for r in rows]


@router.post("/{experiment_id}/personas", status_code=201)
async def add_persona(experiment_id: str, body: PersonaSchema, s: AsyncSession = Depends(get_session)):
    """Import/create a persona using the Milestone-2 Persona schema."""
    await _exp(s, experiment_id)
    row = _to_row(experiment_id, body, key=f"{body.id}-{uuid.uuid4().hex[:6]}")
    s.add(row)
    await s.commit()
    return ser.persona(row)


@router.get("/{experiment_id}/personas")
async def list_personas(experiment_id: str, s: AsyncSession = Depends(get_session)):
    await _exp(s, experiment_id)
    rows = (await s.scalars(select(Persona).where(Persona.experiment_id == experiment_id).order_by(Persona.created_at))).all()
    return [ser.persona(r) for r in rows]


@router.post("/{experiment_id}/documents", status_code=201)
async def upload_document(experiment_id: str, file: UploadFile = File(...), s: AsyncSession = Depends(get_session)):
    data = await file.read(upload_service.settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    doc = await upload_service.save_document(s, experiment_id, file.filename or "upload", file.content_type, data)
    return {"id": doc.id, "filename": doc.filename, "sizeBytes": doc.size_bytes, "extractedChars": len(doc.extracted_text)}


@router.get("/{experiment_id}/documents")
async def list_documents(experiment_id: str, s: AsyncSession = Depends(get_session)):
    await _exp(s, experiment_id)
    rows = (await s.scalars(select(ExperimentDocument).where(ExperimentDocument.experiment_id == experiment_id))).all()
    return [{"id": d.id, "filename": d.filename, "sizeBytes": d.size_bytes, "extractedChars": len(d.extracted_text)} for d in rows]
