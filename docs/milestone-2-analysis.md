# Milestone 2 analysis (what existed before Milestone 3)

Inspected from `synthetic_persona_platform_fixed.zip`. Git history was not included in the zip, so the zip contents were committed as the
baseline (`milestone-2` tag) and Milestone 3 lives on branch `milestone-3-backend`.

```
User -> Streamlit form (streamlit_app.py) or main.py
      -> graph.run_pipeline()  (LangGraph StateGraph, MemorySaver checkpointer)
          persona_agent -> survey_agent -> response_agent -> insight_agent -> PDF (report_generator.py)
      -> Streamlit persona cards -> PersonaInterviewSession (in-process message list)
```

| Area | Milestone 2 reality |
|---|---|
| Language / stack | Python, LangGraph, LangChain, Pydantic, Streamlit, reportlab |
| Agents | Persona (1 LLM call per persona), Survey (LLM designs questions), Response (1 call per persona, all questions at once), Insight (1 free-text-heavy report) |
| LLM | Qwen3-8B via `langchain_openai.ChatOpenAI`; `llm.py` adds retry + model fallback + structured output (`function_calling`) |
| Persona model | `schemas.Persona` (name, age, occupation, traits, behavioral_patterns, psychological_profile, goals, pain_points, ...) |
| "Memory" | (a) LangGraph `GraphState` + in-RAM `MemorySaver`; (b) `PersonaInterviewSession.history` list. Both are lost on restart. There was **no** persistent persona-memory/consistency module. |
| Database | none |
| HTTP API | none (function calls only) |
| File upload | none |
| Auth | none |
| Tests | none |

## Where Milestone 3 plugs in
* `schemas.Persona` and `agents/persona_agent.persona_agent_node` are **reused unchanged** (API `POST /experiments/{id}/personas/generate` calls it, then persists).
* `llm.py` stays the single LLM gateway; async/timeout/concurrency/embedding functions were **appended** (sync functions untouched).
* Old Streamlit UI, LangGraph pipeline, PDF report and `PersonaInterviewSession` still work (covered by `tests/integration/test_milestone2_regression.py`).
* Because no memory module existed, `services/memory/memory_service.py` is the first and only persona-memory system; Survey and Interview both use it.
