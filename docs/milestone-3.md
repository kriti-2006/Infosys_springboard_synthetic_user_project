# Milestone 3 - summary & API

Quick start
```bash
docker compose up -d && cp .env.example .env   # add OPENROUTER_API_KEY
pip install -r requirements.txt
alembic upgrade head
uvicorn api.app:app --reload                   # docs at http://localhost:8000/docs
pytest                                         # fast, no API key needed (LLM is mocked)
```

| Method & path | Purpose |
|---|---|
| `POST /api/experiments`, `GET /api/experiments/:id` | experiment workspace |
| `POST /api/experiments/:id/personas/generate` | runs the Milestone-2 Persona Agent and stores the personas |
| `POST/GET /api/experiments/:id/personas` | import / list personas |
| `POST/GET /api/experiments/:id/documents` | upload (pdf, docx, txt, csv) / list |
| `POST /api/surveys`, `GET /api/surveys/:id` | create / inspect (with progress) |
| `POST /api/surveys/:id/run[?wait=true]` | 202 start, resume partial/failed; 409 if running/completed |
| `GET /api/surveys/:id/results` | per-persona answers, scores, `failures[]` |
| `POST /api/interviews`, `GET /api/interviews/:id` | start / get |
| `POST /api/interviews/:id/messages` | one turn (`{content, clientMessageId?}`) |
| `GET /api/interviews/:id/history` | full transcript with memory + validation |
| `POST/GET /api/experiments/:id/insights` | extract / list structured insights |
| `POST/GET /api/experiments/:id/product-usage` | score personas / scores + overall + by segment |

## Upload pipeline
validate (extension allow-list, MIME match, size, magic bytes, DOCX zip structure + zip-bomb check, UTF-8 for text) -> store as `<sha256>.<ext>` (user filename never used in a path) -> extract (pypdf <=200 pages, python-docx, csv <=500 rows) -> normalise -> `experiment_documents.extracted_text` -> first ~4000 chars injected into every persona prompt. Raw files never reach the LLM. XLSX and OCR are not supported.

## Known limitations
* LLM behaviour is verified with a deterministic fake, **not** against a live OpenRouter model (no key in the build environment). Real answer quality / validator strictness needs tuning with a key.
* Embedding retrieval has not been run with a real embedding model.
* Jobs are in-process: a restart kills running jobs. On startup, surveys left `running` are marked `partial` so `POST /run` resumes them (single-instance assumption).
* Insight prompt is capped at 300 responses (evenly sampled) - no map-reduce for larger surveys.
* Interview insights use neutral sentiment (no per-turn sentiment stored).
* Rate limiter and per-interview locks are per-process.
* Auth is only an optional shared API key (Milestone 2 had none).
