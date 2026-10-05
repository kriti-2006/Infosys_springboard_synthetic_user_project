"""Builds the experiment context string given to the LLM: product + objectives + (truncated) uploaded-document text."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import Experiment, ExperimentDocument


async def build_context(session: AsyncSession, experiment: Experiment, extra_objective: str = "") -> str:
    parts = [f"Product: {experiment.product_description}"]
    if experiment.target_audience:
        parts.append(f"Target audience: {experiment.target_audience}")
    obj = extra_objective or experiment.research_objectives
    if obj:
        parts.append(f"Research objective: {obj}")
    docs = (await session.scalars(select(ExperimentDocument).where(ExperimentDocument.experiment_id == experiment.id)
                                  .order_by(ExperimentDocument.created_at))).all()
    budget = settings.MAX_DOC_CONTEXT_CHARS
    for d in docs:
        if budget <= 0:
            break
        snippet = d.extracted_text[: min(budget, 1500)]
        if snippet:
            parts.append(f"Supplied research material ({d.filename}): {snippet}")
            budget -= len(snippet)
    return "\n".join(parts)


def persona_block(p) -> str:
    prof = p.profile or {}
    return (
        f"Name: {p.name}\nAge: {p.age}\nOccupation: {p.occupation}\nSegment: {p.segment}\n"
        f"Background: {prof.get('background', '')}\nPersonality: {', '.join(p.personality or [])}\n"
        f"Behavioral patterns: {'; '.join(p.behavioral_patterns or [])}\nPsychological profile: {p.psychological_profile}\n"
        f"Goals: {'; '.join(prof.get('goals', []))}\nFrustrations/pain points: {'; '.join(prof.get('pain_points', []))}\n"
        f"Tech savviness: {prof.get('tech_savviness', 'n/a')}\nCommunication style: {prof.get('communication_style', 'n/a')}"
    )
