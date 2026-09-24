# Plum Claims Pipeline Showcase

An end-to-end health insurance claims adjudication demo for the Plum AI Engineer assignment. The app combines a FastAPI backend, a React/Vite frontend, SQLite persistence, assignment-case eval tooling, and an explainable multi-step claim trace.

## What it does

- Accepts claim submissions through a UI or API.
- Verifies required documents before adjudication and blocks with actionable member-facing messages.
- Extracts structured data from fixture-backed docs or real uploads, with graceful degradation when OCR/LLM support is unavailable.
- Applies policy-driven rules from `policy_terms.json` without hardcoding benefits.
- Produces explainable `APPROVED`, `PARTIAL`, `REJECTED`, `MANUAL_REVIEW`, or pre-decision `BLOCKED` outcomes.
- Runs all 12 assignment scenarios through the same pipeline and generates `docs/eval-report.md`.

## Project layout

```text
app/                  FastAPI app, pipeline services, eval runner, persistence
frontend/             React + Vite reviewer UI
docs/                 Architecture, component contracts, eval report
tests/                Backend and API test suite
policy_terms.json     Policy source of truth
test_cases.json       Assignment scenarios
sample_documents_guide.md
```

## Local setup

### Backend

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to the FastAPI app.

### All-in-one production-style run

```bash
cd frontend
npm run build
cd ..
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

FastAPI serves `frontend/dist` automatically once the frontend has been built.

## Environment variables

- `TURING_API_BASE`
- `TURING_API_KEY`
- `TURING_API_GATEWAY_KEY`
- `TURING_BASIC_AUTH`
- `TURING_PROVIDER`
- `TURING_UPLOAD_MODULE`
- `TURING_MULTIMODAL_MODEL`
- `TURING_TEXT_MODEL`
- `APP_ENV`

The Turing integration uses a two-step flow: upload the image/document to the gateway, then reference the returned file ID in `/api/v2/chat`. If the Turing variables are missing, the pipeline still works for structured fixtures and degrades gracefully for OCR-heavy uploads.

## Tests and verification

```bash
python -m pytest tests -q
cd frontend && npm test
cd frontend && npm run build
```

## Eval suite

Run the full assignment evals through the API or directly in Python:

```bash
curl -X POST http://127.0.0.1:8000/api/evals/run \
  -H "Content-Type: application/json" \
  -d "{}"
```

The backend writes the latest Markdown report to `docs/eval-report.md`.

## Deployment

- `Dockerfile` builds the frontend and serves the full app from one container.

## Docs

- [Architecture](docs/architecture.md)
- [Component contracts](docs/component-contracts.md)
- [Eval report](docs/eval-report.md)
