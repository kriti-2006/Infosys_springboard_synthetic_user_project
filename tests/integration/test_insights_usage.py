import pytest
from sqlalchemy import func, select

from db import session as dbs
from db.models import Insight, ProductUsageScore
from tests.conftest import make_survey, setup
from tests.integration.test_interview import say


async def run_survey(client, scenario="food_delivery"):
    eid, personas, sc = await setup(client, scenario)
    qs = [dict(questionId="q1", question="What do you think about the price?", type="open_ended"),
          dict(questionId="q2", question="Would you use this product regularly?", type="yes_no")]
    sv = await make_survey(client, eid, personas, qs)
    await client.post(f"/api/surveys/{sv['id']}/run?wait=true")
    return eid, personas, sv


async def test_insights_structure_and_grounding(client):
    eid, personas, sv = await run_survey(client)
    r = await client.post(f"/api/experiments/{eid}/insights", json={"source": "survey", "surveyId": sv["id"]})
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert set(d) >= {"themes", "sentiment", "agreementPatterns", "behavioralTrends", "contradictions", "outliers"}
    theme = next(t for t in d["themes"] if t["name"] == "Price sensitivity")
    ids = {p["id"] for p in personas}
    assert set(theme["personaIds"]) <= ids and "ghost-persona" not in theme["personaIds"]        # hallucinated id dropped
    assert theme["frequency"] == len(theme["personaIds"]) and theme["percentage"] == round(100 * theme["frequency"] / 4, 1)
    assert theme["frequency"] >= 2 and theme["evidence"] and theme["evidence"][0]["excerpt"]      # evidence copied from DB
    assert abs(sum(d["sentiment"].values()) - 100) < 0.5 and set(d["segmentSentiment"]) >= {"students", "retired"}
    assert d["agreementPatterns"][0]["summary"].startswith(f"{theme['frequency']} of 4 personas")
    assert d["contradictions"] and d["outliers"]
    listed = (await client.get(f"/api/experiments/{eid}/insights")).json()
    assert len(listed) == 1 and listed[0]["data"]["themes"] == d["themes"]                         # persisted as JSON, machine-readable


async def test_insights_include_interviews_and_reject_empty(client):
    eid, personas, _ = await setup(client, "food_delivery", 2)
    assert (await client.post(f"/api/experiments/{eid}/insights", json={"source": "combined"})).status_code == 422   # nothing to analyse
    iid = (await client.post("/api/interviews", json={"experimentId": eid, "personaId": personas[0]["id"]})).json()["id"]
    await say(client, iid, "Do you care about price?")
    r = await client.post(f"/api/experiments/{eid}/insights", json={"source": "interview"})
    assert r.status_code == 201 and r.json()["data"]["participants"] == 1
    assert (await client.post("/api/experiments/ghost/insights")).status_code == 404


async def test_product_usage_scores_reasoning_segments(client):
    eid, personas, _ = await run_survey(client)
    r = await client.post(f"/api/experiments/{eid}/product-usage")
    assert r.status_code == 201, r.text
    body = (await client.get(f"/api/experiments/{eid}/product-usage")).json()
    by = {s["personaName"]: s for s in body["scores"]}
    assert len(by) == 4 and all(s["reasoning"] and 0 <= s["score"] <= 100 and 0 < s["confidence"] <= 1 for s in by.values())
    assert by["Meera"]["decision"] == "very_likely" and by["Mr. Sharma"]["decision"] in ("unlikely", "very_unlikely")
    assert by["Meera"]["score"] > by["Aarav"]["score"] > 0                                          # derived from persona, not random
    assert "Software engineer" in by["Meera"]["reasoning"]
    assert body["bySegment"]["retired"]["likelihood"] < body["bySegment"]["working_professionals"]["likelihood"]
    assert body["overallLikelihood"] == round(sum(s["score"] for s in by.values()) / 4, 1)
    again = await client.post(f"/api/experiments/{eid}/product-usage")                              # re-run upserts, no duplicates
    async with dbs.session_scope() as s:
        assert await s.scalar(select(func.count()).select_from(ProductUsageScore)) == 4


async def test_usage_partial_failure(client, fake):
    from tests.fake_llm import timeout
    eid, _, _ = await setup(client, "ecommerce")
    fake.fail_if = lambda n, i: timeout() if n == "UsageEval" and "Premium" in i["persona"] else None
    r = (await client.post(f"/api/experiments/{eid}/product-usage")).json()
    assert r["scored"] == 3 and len(r["failed"]) == 1 and len(r["scores"]) == 3
