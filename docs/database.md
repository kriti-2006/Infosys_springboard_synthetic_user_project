# Database

**Database used: PostgreSQL 16 with the `pgvector` extension** (access via SQLAlchemy 2.0 async + asyncpg; migrations via Alembic).

## Getting it running (no PostgreSQL installed)
Option 1 - Docker (recommended; nothing to install except Docker):
```bash
docker compose up -d            # starts pgvector/pgvector:pg16, creates DBs persona_platform + persona_platform_test, enables pgvector
cp .env.example .env            # DATABASE_URL already points at it
alembic upgrade head            # creates all tables
```
Option 2 - native install: install PostgreSQL 16 + pgvector (Ubuntu: `sudo apt install postgresql postgresql-16-pgvector`; Windows/macOS: official PostgreSQL
installer or Homebrew + `brew install pgvector`), then run `scripts/setup_db_local.sh` (or run its SQL by hand), then `alembic upgrade head`.

Run tests against Postgres: `TEST_DATABASE_URL=postgresql://persona:persona@localhost:5433/persona_platform_test pytest`
(without it, tests use a temp SQLite file and the pgvector test is skipped).

## Why PostgreSQL
Relational data with real foreign keys, unique constraints (idempotency), transactions, JSONB for flexible LLM output, and pgvector for semantic memory - all in one engine.

## Why SQLAlchemy + Alembic (instead of Prisma)
Project is Python. SQLAlchemy parameterises all queries (SQL-injection safe); Alembic gives versioned migrations (`alembic/versions/0001_*`). Async engine + connection pool (10 + 10 overflow).

## pgvector decision
Used, **optionally**. `persona_memories.embedding` is a `vector(EMBEDDING_DIM)` column. If `EMBEDDING_MODEL` is set (an embedding model served via Qwen3-8B), new memories are embedded and
retrieval is `ORDER BY embedding <=> query LIMIT k` inside Postgres. If unset (default), retrieval falls back to lexical overlap + importance + recency, so the system works without an embedding provider.
No separate vector DB: the data volume (hundreds-thousands of short memories per experiment) does not justify one.
(Embedding retrieval is tested with deterministic fake vectors on real pgvector; it has not been exercised with a real embedding model.)

## Schema
`experiments` 1-* `personas` 1-* `persona_memories` | `experiments` 1-* `surveys` 1-* `survey_questions`; `surveys` *-* `personas` via `survey_personas`;
`survey_responses` (survey, question, persona) | `interviews` (experiment, persona) 1-* `interview_messages` | `insights` | `product_usage_scores` | `experiment_documents`.
All FKs `ON DELETE CASCADE`.

| Table | Unique constraints | Notable indexes |
|---|---|---|
| personas | (experiment_id, key) | experiment_id |
| persona_memories | (persona_id, layer, content_hash) dedupe | (persona_id, layer) |
| survey_questions | (survey_id, key) | survey_id |
| survey_responses | **(survey_id, question_id, persona_id)** idempotency | (survey_id, status), persona_id |
| interview_messages | (interview_id, turn_number, role); (interview_id, client_message_id) | interview_id |
| product_usage_scores | (experiment_id, persona_id) | experiment_id |
| experiment_documents | (experiment_id, sha256) | experiment_id |
| insights | - | (experiment_id, created_at) |

## How things are stored
* **Persona memory**: layers 2/3/5 as rows (`long_term` / `experiment` / `derived`) with `importance`, `source` (`survey:<id>` / `interview:<id>`), optional embedding. Layer 1 is the `personas` row; layer 4 is `interview_messages` / `survey_responses`.
* **Survey responses**: one row per persona x question: text, normalised typed `value` (JSONB), sentiment, confidence, `consistency_score`, full `validation` JSON, `status` (`completed`/`failed`), `error`, `attempts`.
* **Interview history**: `interview_messages` rows (user + persona per turn) with `turn_number`, `relevant_memory` (what was retrieved), `validation`, timestamps.
* **Insights**: `insights.data` JSONB (themes, sentiment, agreement, trends, contradictions, outliers).

## Migrations
`alembic revision --autogenerate -m "msg"` then `alembic upgrade head` / `alembic downgrade -1`. The first migration needs the `vector` extension; the docker/local scripts install it as superuser, and the migration fails with an actionable message if it is missing.
