from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agents import persistent_interview_agent as ia
from db.models import Interview
from db.session import get_session
from schemas_m3 import InterviewCreate, InterviewMessageIn
from services.errors import NotFound

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _iv(i: Interview) -> dict:
    return {"id": i.id, "experimentId": i.experiment_id, "personaId": i.persona_id, "status": i.status, "createdAt": i.created_at.isoformat()}


@router.post("", status_code=201)
async def create(body: InterviewCreate, s: AsyncSession = Depends(get_session)):
    return _iv(await ia.create_interview(s, body.experiment_id, body.persona_id))


@router.get("/{interview_id}")
async def get(interview_id: str, s: AsyncSession = Depends(get_session)):
    i = await s.get(Interview, interview_id)
    if not i:
        raise NotFound("interview not found")
    return _iv(i)


@router.post("/{interview_id}/messages")
async def post_message(interview_id: str, body: InterviewMessageIn, s: AsyncSession = Depends(get_session)):
    return await ia.post_message(s, interview_id, body.content, body.client_message_id)


@router.get("/{interview_id}/history")
async def get_history(interview_id: str, s: AsyncSession = Depends(get_session)):
    return {"interviewId": interview_id, "messages": await ia.history(s, interview_id)}
