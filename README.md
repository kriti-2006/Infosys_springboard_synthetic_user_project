# Synthetic Persona Research Platform (LangGraph + LangChain)

Implements the agent architecture for **"Generation of AI Powered Synthetic
Users for Product Research"**, applied to **Placement Prep AI /
Campus-to-Corporate Readiness Platform** as the running example.

## Architecture

```
                     ┌────────────────────┐
 product +           │  Agent 1            │
 target audience ───▶│  Persona Agent      │──▶ diverse synthetic personas
                     └────────────────────┘
                               │
                               ▼
                     ┌────────────────────┐
                     │  Agent 2            │
                     │  Survey Agent       │──▶ tailored survey questions
                     └────────────────────┘
                               │
                               ▼
                     ┌────────────────────┐
                     │  Agent 3            │
                     │  Response Agent     │──▶ each persona answers, in character
                     └────────────────────┘
                               │
                               ▼
                     ┌────────────────────┐
                     │  Agent 4            │
                     │  Insight Agent      │──▶ themes, sentiment, recommendations
                     └────────────────────┘
                               │
                               ▼
                        report_generator.py ──▶ PDF report

BONUS (Placement Prep specific — "Interview Mode"):
   agents/interview_agent.py
     - generate_interview_persona(company, round_type)
     - InterviewSession: turn-by-turn mock interview with real conversational
       memory, ending in structured weak-area feedback
```

All four core agents are plain Python functions (`*_node`) wired together with
**LangGraph's `StateGraph`**. Each one reads/writes a shared `GraphState`
(`state.py`) — that shared state passed node-to-node is the "memory" the
project spec asks for at the pipeline level. A `MemorySaver` checkpointer
(`graph.py`) additionally persists that state across calls, keyed by
`thread_id`, so a run can be resumed or inspected later.

Interview Mode has a *different* kind of memory: full conversational history
per persona per session, held in `InterviewSession.history` and replayed into
the prompt every turn so the interviewer persona stays consistent.

Every agent uses `llm.with_structured_output(PydanticModel)` (`schemas.py`)
instead of free-text parsing — this is what makes multi-agent pipelines like
this reliable instead of brittle regex/JSON parsing.

## Files

| File | Role |
|---|---|
| `schemas.py` | Pydantic models for personas, survey, responses, insights |
| `state.py` | Shared `GraphState` that flows through the graph |
| `llm.py` | Single place to configure the model/provider |
| `agents/persona_agent.py` | Agent 1 |
| `agents/survey_agent.py` | Agent 2 |
| `agents/response_agent.py` | Agent 3 (personas simulate answering — "Survey Mode") |
| `agents/insight_agent.py` | Agent 4 |
| `agents/interview_agent.py` | Bonus — "Interview Mode" for Placement Prep AI |
| `report_generator.py` | Renders `InsightReport` to PDF via reportlab |
| `graph.py` | LangGraph `StateGraph` + `MemorySaver` wiring |
| `main.py` | Runnable end-to-end demo using your project as the example |

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env      # add your ANTHROPIC_API_KEY
python main.py
```

This will:
1. Generate 5 synthetic student/T&P-cell personas for Placement Prep AI
2. Generate a 6-question feature-prioritization survey
3. Have every persona answer in character
4. Extract themes/sentiment/recommendations
5. Write `synthetic_research_report.pdf`
6. Run a short Interview Mode demo (Infosys HR persona, one turn, then feedback)

## Extending this

- **Different product**: just change `PRODUCT_DESCRIPTION` / `TARGET_AUDIENCE`
  / `RESEARCH_GOAL` in `main.py` — nothing else changes, because the agents
  are generic.
- **More personas/questions**: change `num_personas` / `num_questions` in
  `run_pipeline(...)`.
- **Swap LLM provider**: edit `llm.py` only.
- **Web/API wrapper**: `run_pipeline()` and `InterviewSession` are already
  plain Python functions/classes — drop them behind FastAPI endpoints as-is.
- **Resume a run**: `graph.get_run_history(thread_id)` reads back a
  previously checkpointed `GraphState` for that thread.


---

# Milestone 3 (backend: database, surveys, interviews, insights, scoring)

**Database: PostgreSQL 16 + pgvector** (SQLAlchemy async + Alembic). Start it with `docker compose up -d`.
See `docs/milestone-3.md` (quick start + API), `docs/database.md`, `docs/agents.md`, `docs/architecture.md`,
`docs/technology-decisions.md`, `docs/environment.md`, `docs/milestone-2-analysis.md`.
The Milestone 2 pipeline (`python main.py`, `streamlit run streamlit_app.py`) is unchanged.

# Frontend (React + TypeScript + Vite)

The Milestone 3 API is fronted by a dashboard in `frontend/`: experiments, persona generation, survey creation and a
side-by-side comparison dashboard, persistent-memory interviews, insight extraction (themes/sentiment/contradictions),
transparent "would they use this?" adoption scoring, and a gallery of ready-made sample scenarios.

## Setup

```bash
# 1. Backend (from the repo root)
docker compose up -d                  # Postgres + pgvector on localhost:5433
cp .env.example .env                  # add GROQ_API_KEY
pip install -r requirements.txt
alembic upgrade head
uvicorn api.app:app --reload          # http://localhost:8000 (docs at /docs)

# 2. Frontend (in a second terminal)
cd frontend
npm install
npm run dev                           # http://localhost:5173 - proxies /api to :8000, no CORS setup needed
```

Open http://localhost:5173, create an experiment (or launch a sample scenario from the sidebar), generate personas,
then run a survey, start an interview, extract insights, or score adoption likelihood.

## Architecture

```
React/Vite SPA (frontend/, :5173) --/api proxy--> FastAPI (api/, :8000) --> agents/ --> PostgreSQL+pgvector (:5433)
```

The frontend never calls the LLM or database directly - every request goes through the same `/api/*` endpoints
documented in `docs/milestone-3.md`. Frontend source layout and the chart-color methodology are documented in
`docs/architecture.md` ("Frontend" section) and `docs/technology-decisions.md`.

## Testing

```bash
# Backend: unit + integration tests, LLM mocked, no API key needed
pytest

# Frontend: type-check + production build (no component test suite yet)
cd frontend && npm run build
```

## LLM provider

Uses Groq (`GROQ_API_KEY`, api.groq.com) - an OpenAI-compatible endpoint with a working free tier. If the key is
missing/invalid or the account is rate-limited, persona generation, survey runs, interviews, insight extraction and
adoption scoring fail with a clear error (the backend returns a typed `llm_unavailable`/`llm_timeout` error, and the
frontend surfaces it as a toast) instead of silently returning fake data. Everything that doesn't require an LLM
call - creating experiments, importing personas, building surveys, browsing sample scenarios, and the full
error/empty/loading UI - works regardless. To switch provider again, edit `_api_key()`/`_build_llm()` in `llm.py` only.
