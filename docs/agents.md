# Agents

| Agent | File | Responsibility | Input | Output | LLM (`GROQ_MODEL`, default `openai/gpt-oss-120b`, via Groq) | Database |
|---|---|---|---|---|---|---|
| Persona Agent *(M2, reused)* | `agents/persona_agent.py` | Generate personas | Experiment | `Persona` | yes | `personas` (persisted by API) |
| Survey Agent | `agents/survey_execution_agent.py` | Run a survey across personas, controlled concurrency, resume, failure tracking | Questions + persona ids | `SurveyResponse` rows | via Persona Simulation | `surveys`, `survey_responses` |
| Persona Simulation Agent | `agents/persona_simulation_agent.py` | Answer one question as one persona (shared by survey + interview) | Persona + memories + context + history + question | `PersonaAnswer` (text, typed value, sentiment, confidence, memory updates) | yes (`PersonaAnswer` schema) | - |
| Consistency Agent | `agents/consistency_agent.py` | Heuristics + LLM consistency & realism validation | Persona + memories + history + answer | `ValidationResult` (`consistent`, `confidence`, `issues[]` + realism) | yes (`ValidationResult`) | stored in `survey_responses.validation` / `interview_messages.validation` |
| Interview Agent | `agents/persistent_interview_agent.py` | Multi-turn persisted interview with layered memory | User question + interview id | Persona reply | via Persona Simulation | `interviews`, `interview_messages`, `persona_memories` |
| Insight Agent | `agents/insight_extraction_agent.py` | Themes, sentiment, agreement, trends, contradictions, outliers (stats in code, discovery by LLM, ids verified) | Responses + persona metadata | `insights.data` JSON | yes (`InsightLLMOut`) | `insights` |
| Usage Agent | `agents/product_usage_agent.py` | Per-persona "would use?" score + reasoning; segment aggregates | Persona + memories + prior answers + product | score 0-100, decision, reasoning, confidence, factors | yes (`UsageEval`) | `product_usage_scores` |
| Insight Agent *(M2, reused)* | `agents/insight_agent.py` | Prose `InsightReport` for the PDF | M2 pipeline state | PDF | yes | - |

Milestone 2 `survey_agent.py` / `response_agent.py` / `interview_agent.py` are unchanged (LangGraph pipeline + Streamlit).

## Consistency rules
`consistency_score = confidence if consistent else 1 - confidence`. An answer is accepted only if: no heuristic issue (empty, meta/AI language, too verbose, years-of-experience impossible for the age), the LLM says consistent, and realism passes (relevant, answers the question, plausible, not verbose, no meta language, score >= 0.5).
On rejection the answer is regenerated once with the validator's feedback. If it is still inconsistent it is stored **flagged** (`validation.accepted=false`) and **not written to memory**. If the typed value is invalid after retries the cell is recorded as `failed`.

## Usage decision bands
0-19 very_unlikely, 20-39 unlikely, 40-59 neutral, 60-79 likely, 80-100 very_likely (deterministic). Segments come from a transparent keyword classifier (`services/segments.py`): students, working_professionals, parents, retired, freelancers, other.
