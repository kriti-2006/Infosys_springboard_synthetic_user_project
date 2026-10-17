# Milestone 3 architecture

```
Client -> FastAPI (api/) -> Agent -> Memory (PostgreSQL+pgvector) -> LLM service (llm.py, Groq) -> Pydantic validation -> PostgreSQL -> Insights -> Usage scores
```

```
            Experiment (+ uploaded documents -> extracted text -> context)
                 |                               |
        POST /surveys/:id/run            POST /interviews/:id/messages
                 |                               |
         Survey Agent                     Interview Agent
      (persona-concurrent, capped)      (persisted, windowed + retrieved memory)
                 \                               /
                  `---- Persona Simulation Agent ----'   (one shared answer path)
                                  |
              heuristics (typed value, meta-language, age sanity)
                                  |
                       Consistency Agent (LLM: consistency + realism)
                          fail -> regenerate once with feedback
                                  |
        persist response/message  +  memory update (only if validated)
                                  |
              Insight Extraction Agent  ->  Product Usage Scoring Agent
```

## Request flow: survey
1. `POST /api/surveys` validates questions/personas, stores Survey + SurveyQuestion + SurveyPersona.
2. `POST /api/surveys/:id/run` atomically claims the survey (`UPDATE ... WHERE status IN (draft, partial, failed)`), returns **202** and runs a tracked asyncio job
   (`wait=true` blocks - used by tests). Second concurrent start -> **409**.
3. Personas run concurrently (`PERSONA_CONCURRENCY`), each persona's questions sequentially (later answers see earlier ones). A global semaphore in `llm.py`
   (`LLM_MAX_CONCURRENCY`) caps in-flight LLM calls across *all* work.
4. Each (persona, question): retrieve top-k memory -> generate -> normalise typed value -> validate -> persist -> memory update.
5. Failures are stored as `failed` rows; survey ends `completed` / `partial` / `failed`. Re-calling `/run` resumes and only redoes failed cells.

## Request flow: interview
Persona profile + top-k retrieved memories + last `INTERVIEW_WINDOW_TURNS` turns + experiment context -> answer -> validate (one retry) -> store both messages
(with `relevant_memory` and `validation`) -> write validated stances to memory. `client_message_id` makes retries safe.

## Frontend
`frontend/` is a React + TypeScript + Vite SPA that calls the FastAPI JSON API directly (no server-rendering,
no separate BFF). Structure: `src/api/*` (typed `axios` clients + response types matching the serializers above),
`src/components/ui/*` (design system: Button/Card/Badge/Field/Tabs/Toast/EmptyState/Skeleton), `src/components/charts/*`
(SentimentBar, AdoptionMeter — see `docs/technology-decisions.md` for the chart-color methodology), `src/components/personas/PersonaCard.tsx`,
and `src/pages/*` (Dashboard, sample-scenario gallery, and a nested `experiments/:id/*` layout with tabs for Overview/Surveys/Interviews/Insights/Adoption).
In dev, `vite.config.ts` proxies `/api` to `http://localhost:8000`, so no CORS configuration is needed locally; the
backend's `CORS_ORIGINS` setting (added alongside the frontend) covers calling the API directly in production.
Sample scenarios (`services/scenarios.py`, `api/routers/scenarios.py`) are static metadata only — launching one creates
a real `Experiment` row pre-filled with a product/audience/objective and a suggested survey draft; personas, survey
answers and insights are still produced by the real agents, never fabricated.

## Design decisions
* **Python, not Node/Prisma**: the existing repo is Python; rewriting every agent would not be "extending" it. Equivalents: SQLAlchemy+Alembic (Prisma), Pydantic (Zod).
* **Prompts live next to their agent** (Milestone 2 convention) rather than a separate `prompts/` tree.
* **Hybrid analytics**: all counts/percentages/sentiment are computed in code; the LLM only proposes themes etc. and every id it returns is verified against real participants.
* **No Redis/BullMQ yet**: see technology-decisions.md.
