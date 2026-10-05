"""
The ONE persona-memory system (Surveys and Interviews both use it).

Layers
  1 Persona profile      -> `personas` row (stable; always injected)
  2 Long-term memory     -> persona_memories(layer='long_term')   stable facts learned over time
  3 Experiment memory    -> persona_memories(layer='experiment')  facts tied to this experiment/product
  4 Conversation memory  -> interview_messages / survey_responses (recent window, see agents)
  5 Derived memory       -> persona_memories(layer='derived')     conclusions inferred from interactions

Retrieval: top-k by pgvector cosine distance when EMBEDDING_MODEL is configured (PostgreSQL),
otherwise lexical overlap + importance + recency. Never "send everything".
"""
import hashlib
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

import llm
from config import settings
from db.models import PersonaMemory
from schemas_m3 import MemoryUpdate
from utils.logging import get_logger, log_event

log = get_logger("memory")
_TOKEN = re.compile(r"[a-z0-9]{3,}")
MAX_CONTENT_CHARS = 400
MAX_UPDATES_PER_ANSWER = 3


def _hash(content: str) -> str:
    return hashlib.sha1(" ".join(content.lower().split()).encode()).hexdigest()


def _tokens(s: str) -> set[str]:
    return set(_TOKEN.findall(s.lower()))


async def add_memory(session: AsyncSession, persona_id: str, experiment_id: str | None, layer: str, content: str,
                     importance: float = 0.5, source: str = "", type_: str = "fact") -> PersonaMemory | None:
    """Insert (deduplicated). Returns None if an identical memory already exists."""
    content = " ".join(content.split())[:MAX_CONTENT_CHARS]
    if not content:
        return None
    h = _hash(content)
    exists = await session.scalar(select(PersonaMemory.id).where(
        PersonaMemory.persona_id == persona_id, PersonaMemory.layer == layer, PersonaMemory.content_hash == h))
    if exists:
        return None
    emb = None
    vecs = await llm.aembed([content])
    if vecs:
        emb = vecs[0]
    mem = PersonaMemory(persona_id=persona_id, experiment_id=experiment_id, layer=layer, type=type_, content=content,
                        content_hash=h, importance=max(0.0, min(1.0, importance)), source=source, embedding=emb)
    try:
        async with session.begin_nested():
            session.add(mem)
            await session.flush()
    except IntegrityError:  # concurrent duplicate insert: harmless
        return None
    return mem


async def apply_updates(session: AsyncSession, persona_id: str, experiment_id: str, updates: list[MemoryUpdate], source: str) -> int:
    """Called only AFTER an answer passed consistency validation."""
    n = 0
    for u in sorted(updates, key=lambda x: -x.importance)[:MAX_UPDATES_PER_ANSWER]:
        if await add_memory(session, persona_id, experiment_id, u.layer, u.content, u.importance, source):
            n += 1
    if n:
        await session.commit()
        log_event(log, "memory_updated", persona_id=persona_id, added=n, source=source)
    return n


async def retrieve(session: AsyncSession, persona_id: str, query: str, k: int | None = None,
                   layers: tuple[str, ...] = ("long_term", "experiment", "derived")) -> list[dict]:
    """Return at most k relevant memories as dicts {layer, content, importance}."""
    k = k or settings.MEMORY_TOP_K
    base = select(PersonaMemory).where(PersonaMemory.persona_id == persona_id, PersonaMemory.layer.in_(layers))
    dialect = session.bind.dialect.name if session.bind else ""
    if settings.EMBEDDING_MODEL and dialect == "postgresql":
        vecs = await llm.aembed([query])
        if vecs:
            rows = (await session.scalars(
                base.where(PersonaMemory.embedding.is_not(None))
                .order_by(PersonaMemory.embedding.cosine_distance(vecs[0])).limit(k))).all()
            if rows:
                return [_dump(m) for m in rows]
    rows = (await session.scalars(base.order_by(PersonaMemory.updated_at.desc()).limit(200))).all()
    q = _tokens(query)
    now = datetime.now(timezone.utc)

    def score(m: PersonaMemory) -> float:
        overlap = len(q & _tokens(m.content)) / (len(q) ** 0.5 or 1)
        ts = m.updated_at if m.updated_at.tzinfo else m.updated_at.replace(tzinfo=timezone.utc)
        recency = 1 / (1 + (now - ts).total_seconds() / 86400)
        return overlap + 0.6 * m.importance + 0.2 * recency

    return [_dump(m) for m in sorted(rows, key=score, reverse=True)[:k]]


def _dump(m: PersonaMemory) -> dict:
    return {"layer": m.layer, "content": m.content, "importance": round(m.importance, 2)}


def format_memories(mems: list[dict]) -> str:
    if not mems:
        return "(no relevant memories yet)"
    return "\n".join(f"- [{m['layer']}] {m['content']}" for m in mems)
