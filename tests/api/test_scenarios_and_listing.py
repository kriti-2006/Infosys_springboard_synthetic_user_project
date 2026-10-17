from tests.conftest import setup


async def test_scenarios_list_has_no_fabricated_data_fields(client):
    r = await client.get("/api/scenarios")
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 5
    for s in body:
        assert set(s) == {"slug", "domain", "title", "description", "productDescription", "targetAudience", "researchObjectives"}


async def test_scenario_launch_creates_a_real_experiment(client):
    slug = (await client.get("/api/scenarios")).json()[0]["slug"]
    r = await client.post(f"/api/scenarios/{slug}/launch")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["experiment"]["id"]
    assert len(body["suggestedQuestions"]) >= 1
    got = await client.get(f"/api/experiments/{body['experiment']['id']}")
    assert got.status_code == 200
    assert got.json()["productDescription"] == body["experiment"]["productDescription"]


async def test_scenario_launch_unknown_slug_404s(client):
    r = await client.post("/api/scenarios/not-a-real-slug/launch")
    assert r.status_code == 404


async def test_experiments_list_includes_persona_and_survey_counts(client):
    eid, personas, _ = await setup(client, "ecommerce", n_personas=2)
    r = await client.get("/api/experiments")
    assert r.status_code == 200
    row = next(e for e in r.json() if e["id"] == eid)
    assert row["personaCount"] == 2
    assert row["surveyCount"] == 0


async def test_surveys_list_by_experiment(client):
    from tests.conftest import make_survey

    eid, personas, _ = await setup(client, "ecommerce", n_personas=2)
    await make_survey(client, eid, personas, [{"questionId": "q1", "question": "How do you feel?", "type": "open_ended"}])
    r = await client.get("/api/surveys", params={"experimentId": eid})
    assert r.status_code == 200
    assert len(r.json()) == 1

    missing = await client.get("/api/surveys", params={"experimentId": "does-not-exist"})
    assert missing.status_code == 404


async def test_interviews_list_by_experiment(client):
    eid, personas, _ = await setup(client, "ecommerce", n_personas=1)
    created = await client.post("/api/interviews", json={"experimentId": eid, "personaId": personas[0]["id"]})
    assert created.status_code == 201
    r = await client.get("/api/interviews", params={"experimentId": eid})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["personaName"] == personas[0]["name"]
