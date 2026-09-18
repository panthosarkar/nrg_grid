# NRG_Grid backend

FastAPI API for minimum-cost, 24-hour electricity dispatch. The pipeline validates
inputs, interprets operator notes, solves a linear program, and independently
replays every decision before returning a successful response. No database is
required; results are not persisted.

## Run locally

From `backend/`, with Python 3.10+ (3.12 recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
# Set GEMINI_API_KEY in .env (or NOTE_INTERPRETER=rules for offline use).
uvicorn app.main:app --reload --env-file .env
```

Windows PowerShell: activate with `.venv\Scripts\Activate.ps1`.
Swagger: http://127.0.0.1:8000/docs. Health: `GET /health`.
The `.env` file is loaded by the `--env-file` option, not implicitly by the app.

```bash
python -m pytest -q
curl -s http://127.0.0.1:8000/optimize-energy \
  -H 'Content-Type: application/json' \
  --data-binary @examples/tariff-savings.json
```

The tariff example consumes 5 kWh during an expensive hour and charges at the
cheap hour: expected cost **BDT 5**, grid energy **5 kWh** (versus BDT 50 without
battery dispatch). `operator-constraints.json` prohibits discharge during the
load hour and costs **BDT 50**. `infeasible.json` returns **409** because all grid
imports are prohibited and there is no solar or initial battery energy.

## API contract

`POST /optimize-energy` accepts either of two complete request shapes. Do not mix
fields between them. `/openapi.json` and `/docs` expose both schemas.

Canonical request: see the complete JSON files in `examples/`.

- `scenario_id`: nonblank string.
- `hours`: exactly 24 records in ascending order, each with `hour` (0–23),
  `demand_kwh`, `solar_kwh`, `tariff_bdt_per_kwh` (finite, nonnegative numbers).
- `battery`: `capacity_kwh` (>0), `initial_energy_kwh`, `minimum_energy_kwh`,
  `max_charge_kwh_per_hour`, `max_discharge_kwh_per_hour`.
  Minimum ≤ initial ≤ capacity; action limits are nonnegative.
- `operator_notes`: 0–3 `{ "note_index": 0, "text": "..." }` objects, sequential
  indexes beginning at zero; each text is 1–1,000 characters.

Canonical response contains `scenario_id`, `directive_interpretation`,
`hourly_plan`, `total_grid_kwh`, `total_cost_bdt`, `peak_grid_kwh`, `plan_summary`,
and `validation`. Each hourly plan includes `hour`, `grid_kwh`, `solar_used_kwh`,
`battery_action` (`charge`, `discharge`, `idle`), `battery_kwh` (action magnitude),
and `battery_energy_after_kwh`. The validation object reports `valid`,
`energy_balance`, `battery_constraints`, `solar_constraints`,
`directive_constraints`, and `battery_neutrality`.

The existing frontend contract is also supported directly: `name`, `hours`,
`battery`, and `notes` (strings). Battery action limits are named `max_charge_kwh`
and `max_discharge_kwh`. Hours can arrive unordered and are sorted before
validation. This shape returns `schedule`, `summary`, and `interpretations`,
plus aggregate metrics and `validation`. Schedule rows include the original
hourly inputs, `grid_kwh`, `solar_used_kwh`, `charge_kwh`, `discharge_kwh`,
`battery_energy_kwh`, and `cost_bdt`.

Set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` in `frontend/.env.local` and restart
Next.js. Without this variable, the UI deliberately uses its solar-first preview.

## Energy rules and directive semantics

These are implementation assumptions pending confirmation against the competition
statement referenced in `../phases.md`:

- One-hour intervals; all energy quantities are kWh, costs are BDT.
- Battery efficiency is 100%; grid charging is permitted. No grid export.
- Solar can be curtailed. Grid + used solar + discharge = demand + charge.
- A signed battery flow prevents simultaneous charging and discharging.
- Battery bounds hold at the initial state and every hour end. Final energy equals
  initial energy. Reserve directives apply at the **end** of each named hour.
- Window endpoints are inclusive. `18 to 22` means hours 18, 19, 20, 21, 22.
  Overnight windows wrap midnight. Fractional-hour windows are unsupported.
- Overlapping reserves use the maximum; grid caps use the minimum; bans accumulate;
  solar reduction factors multiply. `factor=0.7` means 70% of forecast remains.
- `applies=true` for an enforceable directive; only `no_op` has `applies=false`.
  Ambiguous or unsupported constraints fail rather than becoming `no_op`.
- Cost is minimized; equal-cost schedules may differ. There is no secondary peak
  or cycling objective. Replay uses an absolute tolerance of `1e-6` kWh, and
  aggregates are recalculated from returned decisions without rounding them.

The solver uses [SciPy HiGHS linear programming](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html).
The independent validator does not reuse solver constraint arrays.

## Note interpretation

`NOTE_INTERPRETER=gemini` is the default. Set `GEMINI_API_KEY` in the backend
environment to enable it. The default model is `gemini-2.5-flash`, configurable
through `GEMINI_MODEL`.

For offline demos, explicitly set `NOTE_INTERPRETER=rules`; it requires no credentials. It accepts
only these complete templates (case insensitive; final period optional):

```text
Keep at least 8 kWh in the battery from 18:00 to 22:00.
Do not charge the battery between 17:00 and 20:00.
Do not discharge the battery from 18 to 22.
Limit grid to 10 kWh from 17 to 21.
Reduce solar by 30% from 10 to 14.
No additional constraints
```

Both `from H to H` and `between H and H` work for each window. Hours may use
`:00`. Supply one constraint per note. Use hours `0 to 23` for all-day constraints.
This parser is intentionally limited; it does not claim general natural-language
understanding.

For natural-language paraphrases, use `NOTE_INTERPRETER=gemini`, `GEMINI_API_KEY`,
and optionally `GEMINI_MODEL` on the backend. Obtain a key from
[Google AI Studio](https://aistudio.google.com/apikey). Gemini is called through its
[structured-output API](https://ai.google.dev/gemini-api/docs/structured-output)
using a JSON schema. Only operator note text is sent to the provider;
local validation checks note association, types, hours, ranges, and applicability
before optimization. Unsupported or ambiguous notes cause 422. Provider errors
never fall back silently to rules or unconstrained optimization. Semantic accuracy
still depends on the model; inspect the returned interpretations.

Each provider attempt has a 10-second HTTP timeout per network operation, with at
most one retry after 0.5 seconds for transport failures, HTTP 429, or transient
server errors (500, 502, 503, 504). Authentication errors and malformed, blocked,
or truncated responses are not retried.
The solver has a 5-second time limit. Live provider behavior needs a credentialed
smoke test; automated tests mock successful responses, refusals, and failures.

| Variable | Default | Purpose |
| --- | --- | --- |
| `NOTE_INTERPRETER` | `gemini` | `gemini` or explicit offline `rules` |
| `GEMINI_API_KEY` | unset | Backend-only Google AI Studio credential |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini structured-output model name |
| `CORS_ORIGINS` | localhost and 127.0.0.1 on port 3000 | Comma-separated frontend origins |
| `PORT` | 8000 in Docker | Container listening port |

## Errors

Errors use `{"error":{"code":"...","message":"..."}}`. Request validation
also includes `details` with locations, messages, and validation types.

| HTTP | Meaning |
| --- | --- |
| 409 | `infeasible`: constraints cannot all be met |
| 422 | `invalid_request`, `unsupported_note`, or invalid offline interpretation |
| 500 | `schedule_validation_failed`: an invalid solver result was blocked |
| 502 | `interpreter_failed` or `invalid_interpretation` |
| 503 | `interpreter_not_configured` or `solver_failed` |
| 504 | `interpreter_timeout` |

`GET /health` reports process liveness, not provider readiness.

## Deployment

From `backend/`:

```bash
docker build -t gridwise-api .
docker run --rm -p 8000:8000 --env-file .env gridwise-api
```

For Render, set root directory to `backend`, build command to
`pip install -r requirements.txt`, start command to
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and health path to `/health`.
Set `CORS_ORIGINS` to the deployed frontend origin. Set the frontend API URL before
its build. Docker and public deployment have not been exercised by the unit suite.

## Layout

```text
app/main.py            Routes, errors, CORS, and pipeline orchestration
app/schemas/           Canonical, directive, response, and frontend contracts
app/interpreter.py     Offline parser and optional structured LLM interpretation
app/optimizer.py       Constraint construction and cost optimization
app/validator.py       Independent replay and metric calculation
examples/              Repeatable savings, constraints, and infeasibility demos
tests/                 API, optimizer, replay, and interpretation tests
```
