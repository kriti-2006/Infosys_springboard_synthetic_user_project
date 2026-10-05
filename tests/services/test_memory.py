import pytest

import llm
from config import settings
from db import session as dbs
from db.models import Experiment, Persona, PersonaMemory
from schemas_m3 import MemoryUpdate
from services.memory import memory_service as ms
from sqlalchemy import func, select


async def _persona(s):
    e = Experiment(name="e", product_description="p")
    s.add(e)
    await s.flush()
    p = Persona(experiment_id=e.id, key="p1", name="N", age=30, occupation="x")
    s.add(p)
    await s.commit()
    return e, p


async def test_dedupe_cap_and_lexical_retrieval(db):
    async with dbs.session_scope() as s:
        e, p = await _persona(s)
        assert await ms.add_memory(s, p.id, e.id, "derived", "Cares deeply about delivery price", 0.9)
        assert await ms.add_memory(s, p.id, e.id, "derived", "  cares deeply about DELIVERY price ", 0.9) is None  # dedupe
        await ms.add_memory(s, p.id, e.id, "long_term", "Has a dog named Bruno", 0.3)
        await ms.add_memory(s, p.id, e.id, "experiment", "Skeptical of subscriptions", 0.5)
        await s.commit()
        top = await ms.retrieve(s, p.id, "what do you think about price?", k=1)
        assert len(top) == 1 and "price" in top[0]["content"]
        n = await ms.apply_updates(s, p.id, e.id, [MemoryUpdate(layer="derived", content=f"fact {i}", importance=0.5) for i in range(6)], "t")
        assert n == 3  # MAX_UPDATES_PER_ANSWER
        assert await s.scalar(select(func.count()).select_from(PersonaMemory)) == 6


async def test_pgvector_semantic_retrieval(db, monkeypatch):
    if db.dialect.name != "postgresql":
        pytest.skip("pgvector needs PostgreSQL")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "fake-embed")

    async def fake_embed(texts):  # bag-of-words hashing -> deterministic vectors in the real 1536-dim column
        out = []
        for t in texts:
            v = [0.0] * settings.EMBEDDING_DIM
            for w in t.lower().split():
                v[sum(map(ord, w)) % settings.EMBEDDING_DIM] += 1.0
            out.append(v)
        return out

    monkeypatch.setattr(llm, "aembed", fake_embed)
    async with dbs.session_scope() as s:
        e, p = await _persona(s)
        await ms.add_memory(s, p.id, e.id, "derived", "loves cheap discounts coupons", 0.5)
        await ms.add_memory(s, p.id, e.id, "derived", "enjoys hiking mountains", 0.5)
        await s.commit()
        top = await ms.retrieve(s, p.id, "coupons discounts cheap", k=1)
        assert "coupons" in top[0]["content"]
