from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents import insight_extraction_agent as ie
from agents import product_usage_agent as pu
from db.models import Experiment, Insight
from db.session import get_session
from schemas_m3 import InsightRequest
from services.errors import NotFound

router = APIRouter(prefix="/experiments", tags=["analysis"])


@router.post("/{experiment_id}/insights", status_code=201)
async def create_insights(experiment_id: str, body: InsightRequest | None = None, s: AsyncSession = Depends(get_session)):
    body = body or InsightRequest()
    return await ie.extract_insights(s, experiment_id, body.source, body.survey_id)


@router.get("/{experiment_id}/insights")
async def list_insights(experiment_id: str, s: AsyncSession = Depends(get_session)):
    if not await s.get(Experiment, experiment_id):
        raise NotFound("experiment not found")
    rows = (await s.scalars(select(Insight).where(Insight.experiment_id == experiment_id).order_by(Insight.created_at.desc()))).all()
    return [{"id": r.id, "sourceType": r.source_type, "createdAt": r.created_at.isoformat(), "data": r.data} for r in rows]


@router.post("/{experiment_id}/product-usage", status_code=201)
async def score(experiment_id: str, s: AsyncSession = Depends(get_session)):
    summary = await pu.score_experiment(s, experiment_id)
    return {**summary, **(await pu.get_scores(s, experiment_id))}


@router.get("/{experiment_id}/product-usage")
async def get_scores(experiment_id: str, s: AsyncSession = Depends(get_session)):
    return await pu.get_scores(s, experiment_id)
