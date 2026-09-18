# NRG Grid

BUP CSE Fest hackathon project with a Next.js frontend and a FastAPI backend.

## Tech stack

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, and ESLint.
- **Backend:** FastAPI with Uvicorn and automatic OpenAPI documentation.

## Project structure

```text
nrg_grid/
├── frontend/
│   ├── src/app/          # Next.js App Router pages, layout, and styles
│   ├── public/           # Static assets
│   └── package.json      # Frontend dependencies and scripts
├── backend/
│   ├── app/main.py       # FastAPI application and routes
│   └── requirements.txt # Backend dependencies
└── README.md
```

## Prerequisites

- Node.js 20.9 or newer and npm.
- Python 3.10 or newer with pip and venv support.

## Local development

Run the frontend and backend in separate terminals. Start each set of commands
from the repository root.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).
Edit `frontend/src/app/page.tsx` to update the home page.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
fastapi dev app/main.py
```

On Windows PowerShell, use `python -m venv .venv` and activate it with
`.venv\Scripts\Activate.ps1` instead.

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).
The development server reloads when backend files change.

| Route | Purpose |
| --- | --- |
| `GET /` | Returns the API welcome message |
| `GET /health` | Returns `{"status": "ok"}` |
| `/docs` | Interactive Swagger UI documentation |
| `/redoc` | ReDoc API documentation |
| `/openapi.json` | OpenAPI schema |

## Checks

Run frontend linting and a production build from `frontend/`:

```bash
npm run lint
npm run build
```

If Turbopack cannot run in your environment, use `npm run build -- --webpack`.
The starter uses Google Fonts, which require network access during a build.

With the backend running, check its health from another terminal:

```bash
curl http://127.0.0.1:8000/health
```

Expected response: `{"status":"ok"}`.

## Production commands

From `frontend/`:

```bash
npm run build
npm start
```

From `backend/`, with the virtual environment activated:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
