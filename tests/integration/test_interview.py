import asyncio

from sqlalchemy import func, select

from config import settings
from db import session as dbs
from db.models import InterviewMessage, PersonaMemory
from tests.conftest import setup


async def start(client, scenario="food_delivery", idx=0):
    eid, personas, _ = await setup(client, scenario)
    r = await client.post("/api/interviews", json={"experimentId": eid, "personaId": personas[idx]["id"]})
    assert r.status_code == 201
    return r.json()["id"], eid, personas


async def say(client, iid, text, cmid=None):
    r = await client.post(f"/api/interviews/{iid}/messages", json={"content": text, "clientMessageId": cmid})
    assert r.status_code == 200, r.text
    return r.json()


async def test_memory_carries_across_turns(client, fake):
    iid, _, _ = await start(client)
    t1 = await say(client, iid, "Do you care about price?")
    assert "price" in t1["persona"]["content"].lower() and t1["turnNumber"] == 1
    t2 = await say(client, iid, "What would make you switch products?")
    assert t2["turnNumber"] == 2
    assert "price" in t2["persona"]["content"].lower()                      # remembered price sensitivity
    assert any("price" in m["content"].lower() for m in t2["persona"]["relevantMemory"])   # retrieved memory stored with the turn
    hist = (await client.get(f"/api/interviews/{iid}/history")).json()["messages"]
    assert [(m["turnNumber"], m["role"]) for m in hist] == [(1, "user"), (1, "persona"), (2, "user"), (2, "persona")]
    assert hist[1]["validation"]["ok"] is True and hist[1]["timestamp"]


async def test_context_is_bounded_but_old_facts_survive_via_memory(client, fake, monkeypatch):
    monkeypatch.setattr(settings, "INTERVIEW_WINDOW_TURNS", 2)
    iid, _, _ = await start(client)
    await say(client, iid, "Do you care about price?")
    for i in range(5):
        await say(client, iid, f"Tell me about your weekend number {i}")
    await say(client, iid, "What would make you switch products?")
    last = [c[1] for c in fake.calls if c[0] == "PersonaAnswer"][-1]
    assert "Do you care about price" not in last["history"]                 # old turn left the window (no unbounded history)
    assert last["history"].count("Interviewer:") <= 2
    assert "price" in last["memories"].lower()                              # ...but the stance is still retrieved from memory
    assert "price" in (await client.get(f"/api/interviews/{iid}/history")).json()["messages"][-1]["content"].lower()


async def test_idempotent_message_replay(client, fake):
    iid, _, _ = await start(client)
    a = await say(client, iid, "Do you care about price?", cmid="m-1")
    calls = fake.count("PersonaAnswer")
    b = await say(client, iid, "Do you care about price?", cmid="m-1")
    assert b["replayed"] is True and b["persona"]["id"] == a["persona"]["id"] and fake.count("PersonaAnswer") == calls
    async with dbs.session_scope() as s:
        assert await s.scalar(select(func.count()).select_from(InterviewMessage)) == 2


async def test_concurrent_duplicates_do_not_duplicate_turns(client, fake):
    iid, _, _ = await start(client)
    rs = await asyncio.gather(*[client.post(f"/api/interviews/{iid}/messages", json={"content": "Hello there", "clientMessageId": "same"}) for _ in range(3)])
    assert all(r.status_code == 200 for r in rs)
    async with dbs.session_scope() as s:
        assert await s.scalar(select(func.count()).select_from(InterviewMessage)) == 2


async def test_failed_turn_can_be_retried(client, fake):
    from tests.fake_llm import timeout
    iid, _, _ = await start(client)
    fake.fail_if = lambda n, i: timeout() if n == "PersonaAnswer" else None
    r = await client.post(f"/api/interviews/{iid}/messages", json={"content": "Hi", "clientMessageId": "x"})
    assert r.status_code == 504 and r.json()["error"]["code"] == "llm_timeout"
    fake.fail_if = None
    r = await client.post(f"/api/interviews/{iid}/messages", json={"content": "Hi", "clientMessageId": "x"})
    assert r.status_code == 200 and r.json()["turnNumber"] == 1
    async with dbs.session_scope() as s:
        assert await s.scalar(select(func.count()).select_from(InterviewMessage)) == 2


async def test_invalid_interview_and_persona_isolation(client):
    assert (await client.post("/api/interviews/ghost/messages", json={"content": "hi"})).status_code == 404
    assert (await client.get("/api/interviews/ghost/history")).status_code == 404
    eid, personas, _ = await setup(client, "food_delivery", 1)
    eid2, _, _ = await setup(client, "fitness", 1)
    r = await client.post("/api/interviews", json={"experimentId": eid2, "personaId": personas[0]["id"]})   # persona from other experiment
    assert r.status_code == 404
    assert (await client.post("/api/interviews", json={"experimentId": eid, "personaId": personas[0]["id"]})).status_code == 201
    iid = (await client.post("/api/interviews", json={"experimentId": eid, "personaId": personas[0]["id"]})).json()["id"]
    assert (await client.post(f"/api/interviews/{iid}/messages", json={"content": ""})).status_code == 422


async def test_survey_and_interview_share_one_memory_system(client, fake):
    from tests.conftest import make_survey
    eid, personas, sc = await setup(client, "food_delivery", 1)
    sv = await make_survey(client, eid, personas, [sc["questions"][1]])
    await client.post(f"/api/surveys/{sv['id']}/run?wait=true")
    iid = (await client.post("/api/interviews", json={"experimentId": eid, "personaId": personas[0]["id"]})).json()["id"]
    t = await say(client, iid, "What would make you switch products?")
    assert any("price" in m["content"].lower() for m in t["persona"]["relevantMemory"])     # memory written by the SURVEY is used by the INTERVIEW
