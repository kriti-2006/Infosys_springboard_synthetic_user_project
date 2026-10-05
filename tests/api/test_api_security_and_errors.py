import pytest
from sqlalchemy.exc import OperationalError

from api import deps
from config import settings
from db.session import get_session
from tests.conftest import setup


async def test_api_key_enforced_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "s3cret")
    body = dict(name="e", productDescription="p")
    assert (await client.post("/api/experiments", json=body)).status_code == 401
    assert (await client.post("/api/experiments", json=body, headers={"X-API-Key": "wrong"})).status_code == 401
    assert (await client.post("/api/experiments", json=body, headers={"X-API-Key": "s3cret"})).status_code == 201
    assert (await client.get("/health")).status_code == 200


async def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 3)
    codes = [(await client.get("/api/experiments/x")).status_code for _ in range(5)]
    assert codes[:3] == [404] * 3 and codes[3:] == [429, 429]


async def test_database_failure_is_a_controlled_503(client):
    async def broken():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        yield
    client.app.dependency_overrides[get_session] = broken
    r = await client.get("/api/experiments/x")
    assert r.status_code == 503 and r.json()["error"]["code"] == "database_error"
    assert "connection refused" not in r.text and "Traceback" not in r.text


async def test_unhandled_error_does_not_leak_internals(client, monkeypatch):
    from api.routers import experiments

    async def boom(*a, **k):
        raise RuntimeError("secret internal path /srv/app key=sk-abcdefgh12345678")
    monkeypatch.setattr(experiments, "_exp", boom)
    r = await client.get("/api/experiments/x")
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error"
    assert "sk-" not in r.text and "/srv" not in r.text


async def test_logger_redacts_secrets():
    import json, logging
    from utils.logging import JsonFormatter
    rec = logging.LogRecord("t", 20, "", 0, "key sk-abcdefgh12345678 used", (), None)
    rec.api_key = "sk-abcdefgh12345678"
    out = json.loads(JsonFormatter().format(rec))
    assert "sk-abc" not in json.dumps(out) and out["api_key"] == "[REDACTED]"


async def test_persona_generation_reuses_milestone2_agent(client, monkeypatch):
    from agents import persona_agent
    from schemas import Persona
    from tests.scenarios import SCENARIOS

    def fake_structured(prompt, schema, inputs, temperature=0.7, label=""):
        return Persona(**SCENARIOS["food_delivery"]["personas"][0])
    monkeypatch.setattr(persona_agent, "invoke_structured", fake_structured)
    e = (await client.post("/api/experiments", json=dict(name="e", productDescription="p"))).json()
    r = await client.post(f"/api/experiments/{e['id']}/personas/generate", json={"count": 2})
    assert r.status_code == 201 and len(r.json()) == 2 and r.json()[0]["segment"] == "students"
    r2 = await client.post(f"/api/experiments/{e['id']}/personas/generate", json={"count": 1})      # keys don't collide on re-generation
    assert r2.status_code == 201
    assert len((await client.get(f"/api/experiments/{e['id']}/personas")).json()) == 3


async def test_restart_recovers_interrupted_survey(client):
    from sqlalchemy import update
    from api.app import recover_interrupted_surveys
    from db import session as dbs
    from db.models import Survey
    from tests.conftest import make_survey
    eid, personas, sc = await setup(client, "food_delivery", 1)
    sv = await make_survey(client, eid, personas, sc["questions"][:1])
    async with dbs.session_scope() as s:                       # simulate a crash mid-run
        await s.execute(update(Survey).where(Survey.id == sv["id"]).values(status="running"))
        await s.commit()
    assert (await client.post(f"/api/surveys/{sv['id']}/run")).status_code == 409
    assert await recover_interrupted_surveys() == 1
    assert (await client.post(f"/api/surveys/{sv['id']}/run?wait=true")).json()["status"] == "completed"
