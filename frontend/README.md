# NRG Grid frontend

Next.js interface connected to the FastAPI optimizer through a server route.

```bash
npm ci
cp .env.example .env.local
npm run dev
```

Start the backend separately using [its setup instructions](../backend/README.md).
Open http://localhost:3000, edit the scenario, and click Optimize.

The browser sends the complete scenario JSON to `POST /api/optimize-energy`.
Next.js forwards it to FastAPI at `BACKEND_URL/optimize-energy` and preserves
backend status codes and error messages. A successful response must include
`validation.valid=true` before it is displayed as a validated plan.

`BACKEND_URL` defaults to `http://127.0.0.1:8000` in development. Set it explicitly
in production to the URL reachable from the Next.js server (in Docker, use the
backend service hostname). The old `NEXT_PUBLIC_API_URL` setting is accepted as a
server-side fallback. Gemini API keys belong only in the backend environment.

The initial baseline preview is labeled and does not apply notes. Optimize always
calls the backend; network or interpretation failures produce an error. Editing
inputs marks existing results as outdated until the next successful run.

No database is needed for this flow. State is held in the browser, and scenario
inputs can be exported/imported as JSON. Saved runs and accounts would require
persistent storage.

Checks: `npm run lint`, `npm run build -- --webpack`.
Production: `npm run build` then `npm start` (requires a Next.js server, not static export).
