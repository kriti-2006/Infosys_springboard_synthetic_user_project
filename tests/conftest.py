import os

import httpx
import pytest
import pytest_asyncio

import llm
from api import deps
from api.app import create_app
from config import settings
from db import session as dbs
from db.models import Base
from tests.fake_llm import FakeLLM
from tests.scenarios import SCENARIOS


@pytest_asyncio.fixture
async def db(tmp_path):
    url = os.getenv("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = dbs.configure(url)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)
    yield engine
    await dbs.dispose()


@pytest.fixture(autouse=True)
def _settings(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 0)
    monkeypatch.setattr(settings, "API_KEY", "")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "")
    deps._hits.clear()


@pytest.fixture
def fake(monkeypatch):
    f = FakeLLM()
    monkeypatch.setattr(llm, "ainvoke_structured", f)
    return f


@pytest_asyncio.fixture
async def client(db, fake):
    app = create_app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        c.app = app
        yield c


async def setup(client, scenario: str, n_personas: int | None = None):
    """Create experiment + personas through the real API. Returns (experiment_id, [persona dicts], scenario)."""
    sc = SCENARIOS[scenario]
    e = (await client.post("/api/experiments", json=sc["experiment"])).json()
    personas = []
    for p in sc["personas"][:n_personas]:
        r = await client.post(f"/api/experiments/{e['id']}/personas", json=p)
        assert r.status_code == 201, r.text
        personas.append(r.json())
    return e["id"], personas, sc


async def make_survey(client, eid, personas, questions, title="Survey"):
    r = await client.post("/api/surveys", json={"experimentId": eid, "title": title, "researchObjective": "test",
                                                "questions": questions, "personaIds": [p["id"] for p in personas]})
    assert r.status_code == 201, r.text
    return r.json()
