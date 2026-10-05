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
