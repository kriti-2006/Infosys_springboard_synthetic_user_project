import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from agents import survey_execution_agent as sa
from db import session as dbs
from db.models import PersonaMemory, SurveyResponse
from services.errors import Conflict
from tests.conftest import make_survey, setup
from tests.fake_llm import timeout
from tests.scenarios import SCENARIOS


@pytest.mark.parametrize("scenario", list(SCENARIOS))
async def test_all_personas_answer_all_questions(client, scenario):
    eid, personas, sc = await setup(client, scenario)
    sv = await make_survey(client, eid, personas, sc["questions"])
    r = await client.post(f"/api/surveys/{sv['id']}/run?wait=true")
    assert r.status_code == 202 and r.json()["status"] == "completed", r.text
    res = (await client.get(f"/api/surveys/{sv['id']}/results")).json()
    assert res["failures"] == []
    expected_qs = [q["questionId"] for q in sc["questions"]]
    for p in res["personas"]:
        assert [x["questionId"] for x in p["responses"]] == expected_qs          # everyone answered everything, in order
        assert all(x["consistencyScore"] is not None and x["sentiment"] for x in p["responses"])
    # personas must differ from each other on the same question
    first = {p["personaId"]: p["responses"][0]["response"] for p in res["personas"]}
    assert len(set(first.values())) >= 2


async def test_food_delivery_persona_differences_and_types(client):
    eid, personas, sc = await setup(client, "food_delivery")
    sv = await make_survey(client, eid, personas, sc["questions"])
    await client.post(f"/api/surveys/{sv['id']}/run?wait=true")
    res = (await client.get(f"/api/surveys/{sv['id']}/results")).json()
    by = {p["name"]: {x["questionId"]: x for x in p["responses"]} for p in res["personas"]}
    assert by["Meera"]["q2"]["value"] is True and by["Mr. Sharma"]["q2"]["value"] is False   # yes/no differs by persona
    assert by["Meera"]["q3"]["value"] > by["Mr. Sharma"]["q3"]["value"]                     # numeric: pays more
    assert "price" in by["Aarav"]["q1"]["response"].lower()                                 # price-sensitive persona talks about price


async def test_every_question_type(client):
    eid, personas, _ = await setup(client, "food_delivery", 2)
    qs = [dict(questionId="a", question="Tell us about it", type="open_ended"), dict(questionId="b", question="Would you use it?", type="yes_no"),
          dict(questionId="c", question="Pick the one you like most", type="single_choice", options=["Speed", "Price"]),
          dict(questionId="d", question="Pick all that apply here", type="multiple_choice", options=["Speed", "Price", "Menu"]),
          dict(questionId="e", question="Rate the idea overall", type="rating"),
          dict(questionId="f", question="I would recommend this app", type="likert"),
          dict(questionId="g", question="Monthly spend you expect", type="numeric"),
          dict(questionId="h", question="One word impression", type="short_answer")]
    sv = await make_survey(client, eid, personas, qs)
    assert (await client.post(f"/api/surveys/{sv['id']}/run?wait=true")).json()["status"] == "completed"
    res = (await client.get(f"/api/surveys/{sv['id']}/results")).json()
    r = {x["questionId"]: x for x in res["personas"][0]["responses"]}
    assert isinstance(r["b"]["value"], bool) and r["c"]["value"] in ("Speed", "Price") and isinstance(r["d"]["value"], list)
    assert 1 <= r["e"]["value"] <= 5 and 1 <= r["f"]["value"] <= 5 and isinstance(r["g"]["value"], (int, float))
    assert r["a"]["value"] is None and r["h"]["value"] is None


async def test_partial_failure_then_resume_is_idempotent(client, fake):
    eid, personas, sc = await setup(client, "food_delivery")
    sv = await make_survey(client, eid, personas, sc["questions"])
    fake.fail_if = lambda name, i: timeout() if name == "PersonaAnswer" and "Retired" in i["persona"] else None
    r = (await client.post(f"/api/surveys/{sv['id']}/run?wait=true")).json()
    assert r["status"] == "partial" and r["failed"] == 4 and r["completed"] == 12
    res = (await client.get(f"/api/surveys/{sv['id']}/results")).json()
    assert len(res["failures"]) == 4 and "timeout" in res["failures"][0]["error"]
    n_calls = fake.count("PersonaAnswer")
    fake.fail_if = None
    r2 = (await client.post(f"/api/surveys/{sv['id']}/run?wait=true")).json()          # resume
    assert r2["status"] == "completed"
    assert fake.count("PersonaAnswer") - n_calls == 4                                    # only the failed ones were redone
    async with dbs.session_scope() as s:
        assert await s.scalar(select(func.count()).select_from(SurveyResponse).where(SurveyResponse.survey_id == sv["id"])) == 16
    assert (await client.post(f"/api/surveys/{sv['id']}/run")).status_code == 409        # completed -> no duplicate execution


async def test_invalid_llm_value_records_failure_not_corruption(client, fake):
    eid, personas, _ = await setup(client, "fitness")
    qs = [dict(questionId="q1", question="Rate how motivating this feels", type="rating")]
    sv = await make_survey(client, eid, personas, qs)
    fake.bad_value_for = "Beginner Bela"
    r = (await client.post(f"/api/surveys/{sv['id']}/run?wait=true")).json()
    assert r["status"] == "partial" and r["failed"] == 1 and r["completed"] == 3
    res = (await client.get(f"/api/surveys/{sv['id']}/results")).json()
    assert "invalid_output" in res["failures"][0]["error"]
    async with dbs.session_scope() as s:  # nothing bad persisted as a completed answer
        done = (await s.scalars(select(SurveyResponse).where(SurveyResponse.status == "completed"))).all()
        assert done and all(r.value != 99 for r in done)


async def test_inconsistent_answer_is_flagged_and_not_remembered(client, fake):
    eid, personas, sc = await setup(client, "food_delivery", 1)       # Aarav: price-sensitive -> would write a memory
    sv = await make_survey(client, eid, personas, [sc["questions"][1]])
    fake.inconsistent_for = "Aarav"
    await client.post(f"/api/surveys/{sv['id']}/run?wait=true")
    res = (await client.get(f"/api/surveys/{sv['id']}/results")).json()
    r = res["personas"][0]["responses"][0]
    assert r["flagged"] is True and r["consistencyScore"] < 0.2
    assert fake.count("PersonaAnswer") == 2                            # regenerated once with validator feedback
    assert any("feedback" in k or "rejected" in v.get("feedback", "") for k, v in [("feedback", c[1]) for c in fake.calls if c[0] == "PersonaAnswer"][1:])
    async with dbs.session_scope() as s:
        assert await s.scalar(select(func.count()).select_from(PersonaMemory)) == 0


async def test_memory_is_written_and_reused_across_survey_answers(client, fake):
    eid, personas, sc = await setup(client, "food_delivery", 1)
    qs = [dict(questionId="q1", question="Would you use this product?", type="yes_no"),
          dict(questionId="q2", question="What do you think about the price?", type="open_ended")]
    sv = await make_survey(client, eid, personas, qs)
    await client.post(f"/api/surveys/{sv['id']}/run?wait=true")
    answers = [c[1] for c in fake.calls if c[0] == "PersonaAnswer"]
    assert "price" in answers[1]["memories"].lower()                  # learned in q1, retrieved for q2
    assert "Would you use" in answers[1]["history"]                   # previous answers fed back


async def test_duplicate_run_and_db_constraint(client):
    eid, personas, sc = await setup(client, "food_delivery", 2)
    sv = await make_survey(client, eid, personas, sc["questions"][:2])
    async with dbs.session_scope() as a, dbs.session_scope() as b:     # two concurrent claims: exactly one wins
        results = await asyncio.gather(sa.claim_survey(a, sv["id"]), sa.claim_survey(b, sv["id"]), return_exceptions=True)
    assert sum(isinstance(r, Conflict) for r in results) == 1
    await sa.execute_survey(sv["id"])
    async with dbs.session_scope() as s:                               # unique(survey, question, persona)
        row = (await s.scalars(select(SurveyResponse))).first()
        s.add(SurveyResponse(survey_id=row.survey_id, question_id=row.question_id, persona_id=row.persona_id))
        with pytest.raises(IntegrityError):
            await s.commit()


async def test_bounded_concurrency(client, fake, monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "LLM_MAX_CONCURRENCY", 3)
    eid, personas, sc = await setup(client, "food_delivery")
    sv = await make_survey(client, eid, personas, sc["questions"][:1])
    active = peak = 0
    orig = fake.__class__.__call__

    async def slow(self, *a, **k):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        try:
            return await orig(self, *a, **k)
        finally:
            active -= 1
    # the real concurrency cap lives in llm._ainvoke_with_fallback; emulate it around the fake via llm's semaphore
    import llm
    async def capped(prompt, schema, inputs, temperature=0.7, label="x"):
        async with llm._llm_semaphore():
            return await slow(fake, prompt, schema, inputs, temperature, label)
    monkeypatch.setattr(llm, "ainvoke_structured", capped)
    await client.post(f"/api/surveys/{sv['id']}/run?wait=true")
    assert 1 < peak <= 3                                              # concurrent, but never above the cap


async def test_missing_and_invalid_inputs(client):
    eid, personas, sc = await setup(client, "food_delivery", 1)
    base = {"experimentId": eid, "title": "t", "questions": sc["questions"][:1], "personaIds": [personas[0]["id"]]}
    assert (await client.post("/api/surveys", json={**base, "experimentId": "nope"})).status_code == 404
    assert (await client.post("/api/surveys", json={**base, "personaIds": ["ghost"]})).status_code == 404
    assert (await client.post("/api/surveys", json={**base, "questions": []})).status_code == 422
    assert (await client.post("/api/surveys", json={**base, "questions": [dict(questionId="q", question="Pick one", type="single_choice")]})).status_code == 422
    assert (await client.post("/api/surveys/ghost/run")).status_code == 404
    assert (await client.get("/api/surveys/ghost")).status_code == 404
