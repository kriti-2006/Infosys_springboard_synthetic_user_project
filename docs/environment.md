# Environment variables (`.env.example`)

## Backend (`.env`, read by `config.py` / `llm.py`)

| Variable | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` | - (required) | Groq API key (api.groq.com). Never commit `.env`. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Model used for every LLM call (persona/survey/interview/insight/scoring). |
| `LLM_TIMEOUT_SECONDS` | 90 | Per-call timeout (async path). |
| `LLM_MAX_CONCURRENCY` | 5 | Max in-flight LLM calls across the whole process. |
| `DATABASE_URL` | `postgresql://persona:persona@localhost:5433/persona_platform` | Postgres URL (auto-converted to asyncpg). Port 5433 by default so it doesn't collide with a native Postgres install on 5432 — change both this and `docker-compose.yml`'s port mapping together if you free up 5432. |
| `TEST_DATABASE_URL` | temp SQLite | DB for tests; use the `persona_platform_test` Postgres DB to also test pgvector. |
| `EMBEDDING_MODEL` | empty | Set to enable pgvector semantic retrieval. Empty = lexical retrieval. |
| `EMBEDDING_DIM` | 1536 | Vector size; must match the model **and the migrated column** (changing it needs a migration). |
| `PERSONA_CONCURRENCY` | 4 | Personas processed in parallel per survey / scoring run. |
| `SURVEY_LLM_VALIDATION` | true | Run the LLM consistency/realism validator (heuristics always run). Set false to halve LLM cost. |
| `MAX_RESPONSE_ATTEMPTS` | 2 | Generate attempts per answer (1 retry with validator feedback). |
| `MEMORY_TOP_K` | 6 | Max memories injected per answer. |
| `INTERVIEW_WINDOW_TURNS` | 4 | Recent interview turns sent to the LLM. |
| `API_KEY` | empty | If set, all `/api` calls need `X-API-Key`. |
| `RATE_LIMIT_PER_MINUTE` | 120 | Per-IP limit (0 disables). |
| `UPLOAD_DIR` / `MAX_UPLOAD_MB` | `./uploads` / 10 | Upload storage and size cap. |
| `MAX_DOC_CONTEXT_CHARS` | 4000 | Max uploaded-document text added to the LLM context. |
| `LOG_LEVEL` | INFO | Logging level. |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of origins allowed to call `/api` directly (the Vite dev server proxies `/api` itself, so this mainly matters for a production frontend served from a different origin). |

## Frontend (`frontend/.env`, read by Vite — see `frontend/.env.example`)

| Variable | Default | Meaning |
|---|---|---|
| `VITE_API_BASE_URL` | `/api` (dev proxy) | Base URL the frontend calls. Leave unset in dev — `vite.config.ts` proxies `/api` to `http://localhost:8000`. Set to the deployed API's `/api` URL in production. |
| `VITE_API_KEY` | empty | Sent as `X-API-Key` on every request; only needed if the backend's `API_KEY` is set. |
