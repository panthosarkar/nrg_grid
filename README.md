# NRG Grid / GridWise-AI

BUP CSE Fest hackathon project: a Next.js energy-planning interface and a FastAPI
backend that minimizes 24-hour grid electricity costs under battery and operator
constraints.

The backend now implements the core pipeline from [phases.md](phases.md): input
validation → note interpretation → constraints → optimization → independent
schedule replay → results. It supports all six directive types and the existing
frontend JSON contract. Gemini interprets natural-language notes by default. An explicit offline mode
uses documented note templates without credentials.

## Local development

Requirements: Node.js 20.9+ and Python 3.10+ (3.12 recommended).
Run the backend and frontend in separate terminals, starting from the repo root.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
# Set GEMINI_API_KEY in .env (or NOTE_INTERPRETER=rules for offline use).
uvicorn app.main:app --reload --env-file .env
```

Windows PowerShell activation: `.venv\Scripts\Activate.ps1`.
API docs: http://127.0.0.1:8000/docs. Health: http://127.0.0.1:8000/health.

```bash
cd frontend
npm ci
cp .env.example .env.local
# BACKEND_URL defaults to http://127.0.0.1:8000 in development.
npm run dev
```

Open http://localhost:3000. Restart Next.js after changing `.env.local`.
The Optimize button calls `/api/optimize-energy` on Next.js, which forwards the
JSON body to FastAPI. Set server-side `BACKEND_URL` to your deployed backend in
production. The initial screen shows a labeled baseline preview until you run
optimization; failures are displayed rather than replaced with a preview. Its sample reserve and charging-ban notes work
with Gemini or the explicit offline interpreter (`NOTE_INTERPRETER=rules`).

## Try the API

From the repository root, with the backend running:

```bash
curl http://127.0.0.1:8000/optimize-energy \
  -H 'Content-Type: application/json' \
  --data-binary @backend/examples/tariff-savings.json
```

Expected: a validated 24-hour schedule costing **BDT 5**, with **5 kWh** of grid
energy. Other examples demonstrate operator constraints and infeasibility.

See [backend/README.md](backend/README.md) for both request/response contracts,
energy assumptions, supported notes, error codes, environment variables, and
Docker/Render setup. Set `GEMINI_API_KEY` in `backend/.env`; the default model is
`gemini-2.5-flash` (override with `GEMINI_MODEL`). Credentials belong in backend
environment variables only.

## Checks

```bash
cd backend
python -m pytest -q
```

Tests cover known optimal costs, all directives, overlapping constraints,
infeasibility, invalid inputs, corrupted schedules, frontend compatibility, CORS,
and mocked LLM successes/failures. Live provider calls and public deployment
require separate verification.

From `frontend/`, run `npm run lint` and `npm run build` for frontend changes.
If Turbopack cannot run in your environment, use `npm run build -- --webpack`.

## Project structure

```text
frontend/                  Next.js 16, React 19, TypeScript, Tailwind CSS 4
backend/app/schemas/       Validated API and directive contracts
backend/app/interpreter.py Gemini and offline note interpretation
backend/app/optimizer.py   SciPy HiGHS minimum-cost dispatch
backend/app/validator.py   Independent schedule replay and metrics
backend/app/main.py        FastAPI routes and CORS
backend/tests/             Backend test suite
backend/examples/          Repeatable demo requests
backend/Dockerfile         Backend container definition
phases.md                  Original eight-phase implementation roadmap
```

Phases 1–5 have implementation and automated coverage. Phase 6's existing frontend
is connected through a Next.js API route; browser interaction verification remains. Phase 7 has
backend scenario coverage; live LLM paraphrase evaluation remains. Phase 8 has
container/setup documentation; no public deployment has been performed. The
competition's energy-rule assumptions still need confirmation against its statement.

Production backend command (from `backend/`):
`uvicorn app.main:app --host 0.0.0.0 --port 8000`.
Production frontend commands (from `frontend/`): `npm run build` then `npm start`.

## Database

A database is not required for the current workflow. Scenarios and results live
in browser memory, and FastAPI computes each request without persistence. JSON
export/import can retain scenario inputs. Add a database when you need saved
scenarios, optimization history, user accounts, or shared plans.
