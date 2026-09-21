# Job Application Assistant

Takes a master resume, tailors it (and a cover letter) to a specific job posting via Claude, and
tracks applications — with a Stripe-backed free/pro subscription layer. Currently a FastAPI
backend plus a minimal HTML/JS demo UI; the cross-platform client (`client/`) hasn't been built
yet.

## Prerequisites

- Python 3.9+
- PostgreSQL (running locally)
- An [Anthropic API key](https://console.anthropic.com) with credits (separate from any
  claude.ai/Claude Code subscription — see note below)
- A [Stripe](https://dashboard.stripe.com) account in **test mode** (free), only needed if you
  want to exercise the subscription/billing endpoints
- The [Stripe CLI](https://stripe.com/docs/stripe-cli) (`brew install stripe/stripe-cli/stripe`),
  only needed to receive webhooks locally

## Setup

1. **Install dependencies**
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create the database**
   ```bash
   createdb job_apply_assistant
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Then edit `backend/.env` directly in your editor (never commit it — it's gitignored) and fill in:
   - `ANTHROPIC_API_KEY` — from console.anthropic.com → API Keys. This is a *separate* account/
     billing surface from a claude.ai or Claude Code subscription — it needs its own credits
     (Plans & Billing) even if you already pay for Claude elsewhere.
   - `STRIPE_SECRET_KEY` — from the Stripe Dashboard → Developers → API keys (test mode), starts
     with `sk_test_...`. Skip this (and the two below) if you don't need billing right now.
   - `STRIPE_PRO_PRICE_ID` — create a recurring monthly Product/Price in the Stripe Dashboard
     (Product catalog → Add product), or via the CLI:
     ```bash
     stripe products create --name "Pro Plan"
     stripe prices create --product <prod_id> --unit-amount 999 --currency usd -d "recurring[interval]=month"
     ```
   - `STRIPE_WEBHOOK_SECRET` — only resolves once you run `stripe listen` (see below); leave
     blank until then.
   - `JWT_SECRET` — any random string for signing auth tokens.
   - `VOYAGE_API_KEY` — only needed for `POST /tailoring` with `"use_rag": true` (see
     `../newProjectRAG`), which retrieves relevant resume bullets and job-posting phrasing before
     tailoring. From https://dash.voyageai.com. Without it, set `RAG_FAKE_EMBEDDINGS=1` to use a
     deterministic offline fallback instead. Without a payment method on the Voyage account,
     expect a 3 requests/minute cap — see `newProjectRAG/README.md` for details.
   - `TYPESAFE_API_KEY` — only needed for `GET /tailoring/fit-score`, which uses TypeSafe's Jev
     model to give a fast, free fit rating (poor/weak/moderate/strong/excellent) between a
     candidate's resume and a job posting before they spend a full (billed) tailoring run on it.
     From https://dash.typesafe.ai. Called directly over HTTP rather than via the `typesafe-sdk`
     package, since that package requires Python >= 3.10 and this backend targets 3.9.

## Running the app

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- **API docs (Swagger UI)**: http://127.0.0.1:8000/docs
- **Minimal demo UI**: http://127.0.0.1:8000/ui/ — walks through the real flow (sign up → check
  plan → upload a resume → add a job posting → tailor it) against the live backend
- **Health check**: http://127.0.0.1:8000/health

### Receiving Stripe webhooks locally (optional)

Billing state (subscription upgrades/downgrades) is driven by Stripe webhooks. Since this only
runs on `localhost`, forward events with the Stripe CLI instead of registering a public endpoint:

```bash
stripe login                                            # one-time, links the CLI to your account
stripe listen --forward-to localhost:8000/billing/webhook
```

This prints a `whsec_...` signing secret — put that in `STRIPE_WEBHOOK_SECRET` in `.env` and
restart the server. Keep `stripe listen` running in its own terminal while testing checkout.

### Testing without Anthropic credits

Resume parsing and tailoring call Claude directly, so they need real API credits. To exercise the
rest of the app (or the demo UI) without them, run the server with a stubbed Claude client instead
of `uvicorn` directly — see `run_with_fake_llm.py` pattern: monkeypatch
`app.resume_parser.parse.get_anthropic_client` and `app.tailoring.tailor.get_anthropic_client`
before starting the app, then run it with `uvicorn.run(app, ...)` in the same process.

## Running tests

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

All tests mock the Anthropic and Stripe SDKs and job-board HTTP calls — no credentials or network
access needed.

## Project structure

```
backend/
  app/
    api/            # FastAPI routers: auth, resumes, jobs, tailoring, billing
    billing/        # Stripe integration, tier limits, usage metering
    core/           # config, db session, JWT auth, Anthropic client
    job_sources/    # Greenhouse / Lever / Ashby adapters
    models/         # SQLAlchemy models
    resume_parser/  # docx/pdf/markdown -> JSON Resume via Claude
    tailoring/      # resume + job posting -> tailored resume, cover letter, diff
  static/           # minimal demo UI (served at /ui)
  tests/
client/             # cross-platform app (not yet built)
```

## What's not built yet

PDF rendering of the tailored resume, the apply/auto-submit integrations, the application
tracking dashboard, and the `client/` cross-platform app itself.
