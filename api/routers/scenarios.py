from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api import serializers as ser
from db.models import Experiment
from db.session import get_session
from services.errors import NotFound
from services.scenarios import get_scenario, list_scenarios

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
async def list_all():
    return [{k: v for k, v in s.items() if k != "suggestedQuestions"} for s in list_scenarios()]


@router.post("/{slug}/launch", status_code=201)
async def launch(slug: str, s: AsyncSession = Depends(get_session)):
    scenario = get_scenario(slug)
    if not scenario:
        raise NotFound("scenario not found")
    e = Experiment(name=scenario["title"], product_description=scenario["productDescription"],
                   target_audience=scenario["targetAudience"], research_objectives=scenario["researchObjectives"])
    s.add(e)
    await s.commit()
    return {"experiment": ser.experiment(e), "suggestedQuestions": scenario["suggestedQuestions"]}
