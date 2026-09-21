# RAG-Tailored Resumes

A retrieval-augmented layer on top of the tailoring engine in `../backend`. Where
`app.tailoring.tailor` stuffs the whole master resume into the prompt, this adds two retrieval
steps before calling Claude:

- **Resume bullet library** — every bullet from a user's resume history (across versions) is
  chunked and embedded, so tailoring can retrieve the bullets most relevant to a given job
  posting instead of relying on the model to skim everything itself.
- **Job market examples** — a corpus of example job postings is embedded too, so tailoring can
  pull realistic phrasing/keywords for the target role (used for terminology only — the
  fabrication guard in `app.tailoring.validate` still applies unchanged).

It's wired into the live API: `POST /tailoring` with `"use_rag": true` calls
`tailor_resume_rag` instead of the plain `tailor_resume`.

This project has no server of its own — it's a library, installed editable into `../backend`'s
own virtualenv (see `../backend/requirements.txt`), that imports `../backend`'s `app` package
directly (DB session, models, config, Anthropic client) and adds its own tables to backend's
database.

## Architecture

```
rag/
  _pathlink.py    # adds ../backend to sys.path so `import app...` works
  embeddings.py   # Voyage AI embedding client (+ deterministic offline fallback)
  models.py       # ResumeBulletChunk, JobExampleChunk — SQLAlchemy models on backend's Base
  ingest.py       # chunk + embed a master resume / job posting into the vector store
  retriever.py    # cosine similarity search (pgvector on Postgres, Python fallback on sqlite)
  tailor_rag.py   # tailor_resume_rag() — retrieval + the existing tailoring prompt/validation
scripts/
  init_db.py               # creates the two new tables (+ pgvector extension) in backend's DB
  ingest_job_examples.py   # bulk-loads a JSONL corpus of example postings
data/
  job_examples.sample.jsonl
tests/
```

## Setup

1. **Use backend's virtualenv** (don't create a new one) — `../backend/requirements.txt` already
   has an editable install of this project (`-e ../newProjectRAG`), so a normal backend setup
   picks it up automatically:
   ```bash
   cd ../backend
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Vector store**: Postgres with the [pgvector](https://github.com/pgvector/pgvector)
   extension installed (`brew install pgvector` on macOS). Uses the same `DATABASE_URL` as
   `backend/.env` — the extension and the two RAG tables are created automatically at backend
   startup (see `app/main.py`), or on demand via `scripts/init_db.py`.

3. **Embeddings**: add the vars from `.env.example` to `backend/.env` and set `VOYAGE_API_KEY`
   from https://dash.voyageai.com. Without it, set `RAG_FAKE_EMBEDDINGS=1` to use a deterministic
   offline fallback — good enough to develop against, not for real retrieval quality.

   Without a payment method on file, Voyage caps new accounts at **3 requests/minute and 10K
   tokens/minute** — each ingest/retrieval call is one request, so this is easy to hit while
   testing (e.g. bulk-ingesting `data/job_examples.sample.jsonl`, or a couple of tailoring calls
   in quick succession). Add a payment method at https://dashboard.voyageai.com/ to raise it —
   the free monthly token grant still applies either way.

4. **(Optional) seed some job market examples**:
   ```bash
   cd ../newProjectRAG
   python scripts/ingest_job_examples.py data/job_examples.sample.jsonl
   ```

## Usage

```python
from app.core.db import SessionLocal
from rag.ingest import ingest_master_resume
from rag.tailor_rag import tailor_resume_rag

db = SessionLocal()
ingest_master_resume(db, master_resume_id, resume)  # re-run whenever the master resume changes
result = tailor_resume_rag(db, resume, master_resume_id, job_description)
```

## Tests

```bash
pytest
```

Tests run against an in-memory sqlite DB with `RAG_FAKE_EMBEDDINGS=1` (set automatically in
`tests/conftest.py`), so they need neither Postgres/pgvector nor a Voyage API key.

## Known limitations

- `ingest_master_resume` re-embeds the current master resume synchronously, inline in the
  request that calls `tailor_resume_rag` (see `app/api/tailoring.py`) — fine at prototype scale,
  but a real embedding-provider round trip on every tailoring call. Moving ingestion to resume
  upload time (so tailoring only re-embeds when the resume actually changed) is the natural next
  step.
- The job-example corpus is only as good as what's been ingested — `scripts/ingest_job_examples.py`
  loads the 3-posting sample in `data/`; there's no scheduled/bulk ingestion pipeline yet.
