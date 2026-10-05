"""
Interview Agent (Milestone 3) — persistent, multi-turn interview with ONE persona.
Replaces the in-process `PersonaInterviewSession.history` list (Milestone 2, kept for the Streamlit UI) with database-backed memory.

Context per turn (bounded, never the whole transcript):
  persona profile (L1) + top-k retrieved memories (L2/L3/L5) + last INTERVIEW_WINDOW_TURNS turns (L4) + experiment context.
Older turns stay reachable because validated stances are written to derived/experiment memory after every turn.
Idempotency: optional client_message_id (unique per interview); turn numbers are unique per (interview, role); per-interview lock.
"""
import asyncio

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agents import consistency_agent, persona_simulation_agent
from config import settings
from db.models import Experiment, Interview, InterviewMessage, Persona
from services import experiment_context
from services.answer_validation import AnswerFormatError, QuestionSpec
from services.errors import Conflict, NotFound
from services.memory import memory_service
from utils.logging import get_logger, log_event

log = get_logger("interview_agent")
_locks: dict[str, asyncio.Lock] = {}


async def create_interview(s: AsyncSession, experiment_id: str, persona_id: str) -> Interview:
    persona = await s.get(Persona, persona_id)
    if not await s.get(Experiment, experiment_id):
        raise NotFound("experiment not found")
    if not persona or persona.experiment_id != experiment_id:
        raise NotFound("persona not found in this experiment")
    iv = Interview(experiment_id=experiment_id, persona_id=persona_id)
    s.add(iv)
    await s.commit()
    log_event(log, "interview_started", interview_id=iv.id, persona_id=persona_id)
    return iv


def _msg(m: InterviewMessage) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "turnNumber": m.turn_number,
            "relevantMemory": m.relevant_memory, "validation": m.validation, "timestamp": m.created_at.isoformat()}


async def history(s: AsyncSession, interview_id: str) -> list[dict]:
    if not await s.get(Interview, interview_id):
        raise NotFound("interview not found")
    rows = (await s.scalars(select(InterviewMessage).where(InterviewMessage.interview_id == interview_id)
                            .order_by(InterviewMessage.turn_number, InterviewMessage.role.desc()))).all()
    return [_msg(m) for m in rows]


async def post_message(s: AsyncSession, interview_id: str, content: str, client_message_id: str | None = None) -> dict:
    lock = _locks.setdefault(interview_id, asyncio.Lock())
    async with lock:
        return await _post(s, interview_id, content, client_message_id)


async def _post(s: AsyncSession, interview_id: str, content: str, cmid: str | None) -> dict:
    iv = await s.get(Interview, interview_id)
    if not iv:
        raise NotFound("interview not found")
    if iv.status != "active":
        raise Conflict("interview is closed")

    user_msg = None
    if cmid:
        user_msg = await s.scalar(select(InterviewMessage).where(
            InterviewMessage.interview_id == interview_id, InterviewMessage.client_message_id == cmid))
        if user_msg:
            reply = await s.scalar(select(InterviewMessage).where(
                InterviewMessage.interview_id == interview_id, InterviewMessage.turn_number == user_msg.turn_number,
                InterviewMessage.role == "persona"))
            if reply:  # duplicate request: replay stored result, no new LLM call
                return {"turnNumber": user_msg.turn_number, "user": _msg(user_msg), "persona": _msg(reply), "replayed": True}
    if not user_msg:
        turn = (await s.scalar(select(func.coalesce(func.max(InterviewMessage.turn_number), 0))
                               .where(InterviewMessage.interview_id == interview_id))) + 1
        user_msg = InterviewMessage(interview_id=interview_id, role="user", content=content, turn_number=turn, client_message_id=cmid)
        s.add(user_msg)
        try:
            await s.commit()
        except IntegrityError:
            await s.rollback()
            raise Conflict("a message for this turn is already being processed")
    turn = user_msg.turn_number

    persona = await s.get(Persona, iv.persona_id)
    experiment = await s.get(Experiment, iv.experiment_id)
    context = await experiment_context.build_context(s, experiment)
    persona_text = experiment_context.persona_block(persona)
    memories = await memory_service.retrieve(s, persona.id, content)
    mem_text = memory_service.format_memories(memories)

    window = settings.INTERVIEW_WINDOW_TURNS
    recent = (await s.scalars(select(InterviewMessage).where(
        InterviewMessage.interview_id == interview_id, InterviewMessage.turn_number < turn, InterviewMessage.turn_number >= turn - window)
        .order_by(InterviewMessage.turn_number, InterviewMessage.role.desc()))).all()
    hist = "\n".join(f"{'Interviewer' if m.role == 'user' else 'You'}: {m.content}" for m in recent)

    spec = QuestionSpec(key=f"turn{turn}", text=content, type="open_ended")
    feedback, out = "", None
    for attempt in range(1, settings.MAX_RESPONSE_ATTEMPTS + 1):
        answer = await persona_simulation_agent.generate_answer(
            persona_block=persona_text, context=context, question=spec, memories=mem_text, history=hist, mode="interview", feedback=feedback)
        v = await consistency_agent.validate(persona=persona, persona_text=persona_text, memories=mem_text, history=hist,
                                             question=spec, answer=answer, value=None)
        out = (answer, v)
        if v.ok:
            break
        feedback = v.feedback()
    answer, v = out
    if not v.ok:
        v.accepted = False
    reply = InterviewMessage(interview_id=interview_id, role="persona", content=answer.answer, turn_number=turn,
                             relevant_memory=memories, validation=v.to_dict())
    s.add(reply)
    try:
        await s.commit()
    except IntegrityError:
        await s.rollback()
        raise Conflict("this turn was already answered")
    if v.ok:
        await memory_service.apply_updates(s, persona.id, experiment.id, answer.memory_updates, f"interview:{interview_id}")
    log_event(log, "interview_turn_generated", interview_id=interview_id, turn=turn, accepted=v.ok,
              memories_used=len(memories), consistency=v.consistency_score)
    return {"turnNumber": turn, "user": _msg(user_msg), "persona": _msg(reply), "replayed": False}
