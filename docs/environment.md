# Environment variables (`.env.example`)

| Variable | Default | Meaning |
|---|---|---|
| `OPENROUTER_API_KEY` | - (required) | OpenRouter key. Never commit `.env`. |
| `OPENROUTER_MODEL` | `openrouter/free` | Model tried first, then fallback (M2 behaviour). |
| `LLM_TIMEOUT_SECONDS` | 90 | Per-call timeout (async path). |
| `LLM_MAX_CONCURRENCY` | 5 | Max in-flight LLM calls across the whole process. |
| `DATABASE_URL` | `postgresql://persona:persona@localhost:5432/persona_platform` | Postgres URL (auto-converted to asyncpg). |
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
