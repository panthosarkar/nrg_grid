# GridWise backend

FastAPI service that finds a minimum-cost electricity schedule for 24 hours.
Gemini interprets operator notes; a deterministic optimizer calculates the schedule;
an independent validator checks every hour before results are returned.

**Public sample-pack status:** the supplied **GridWise Public LLM-Assisted Sample
Case Pack v2.0** reveals interpretation differences that still need fixing.
The API now accepts the pack’s string-based operator notes.
The optimizer matches all ten reference costs when given the reference directives,
but the complete API is **not yet compatible with the pack unchanged**. See
[Compatibility gaps](#compatibility-gaps) before using it for competition checks.

## Start the backend

Run these commands from `backend/`, using Python 3.10+ (3.12 recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

If `.env` already exists, edit it rather than overwriting it. On Windows PowerShell,
activate the environment with `.venv\Scripts\Activate.ps1`.

Set the following in your local `backend/.env`:

```dotenv
NOTE_INTERPRETER=gemini
GEMINI_API_KEY=your_local_key
GEMINI_MODEL=gemini-3.6-flash
```

Keep real keys only in the ignored `.env` or deployment environment. Leave
`GEMINI_API_KEY` empty in the tracked `.env.example`.

```bash
uvicorn app.main:app --reload --env-file .env
```

The `--env-file` option loads `.env`; the application does not load it implicitly.
Use `NOTE_INTERPRETER=rules` for limited offline demos without Gemini credentials.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Process health; does not check Gemini credentials |
| `POST /optimize-energy` | Interpret notes and optimize one scenario |
| `/docs` | Interactive API documentation |
| `/openapi.json` | Machine-readable request and response schemas |

Open http://127.0.0.1:8000/docs or try this complete local example:

```bash
curl http://127.0.0.1:8000/optimize-energy \
  -H 'Content-Type: application/json' \
  --data-binary @examples/tariff-savings.json
```

It has no notes, so no Gemini call is needed. Expected results: **BDT 5** cost and
**5 kWh** grid energy. Sending a POST without a JSON body produces `422`, with
`location: ["body"]` and `message: "Field required"`.

## What the supplied sample pack means

The supplied JSON is a collection of **ten public test cases**, not one API request
and not a database. Its metadata names the BUP CSE Fest 2026 online preliminary,
version 2.0, and the separate problem statement and participant guide. Those
separate documents still need to be consulted; this README describes the supplied
pack and the current implementation.

```text
_meta                     Instructions, schemas, interpretation rules, tolerance
cases[]
  id                      Public test identifier, such as SAMPLE-01
  label                   Short description of the test
  input                   The scenario the API is supposed to receive
  expected_output         One valid optimal reference answer
  rationale               What interpretation or constraint the case tests
```

For competition-style evaluation, send **only `cases[i].input`** to the endpoint.
Do not send `_meta`, the whole `cases` array, `expected_output`, or `rationale`.
The reference answer is for checking results, not information to feed to Gemini.
The API accepts this input shape. Interpretation still has the semantic gaps
listed below.

### Inputs

| Field | Meaning in the public pack |
| --- | --- |
| `scenario_id` | Identifier echoed in the result |
| `operator_notes` | 1–3 nonempty natural-language strings |
| `hours` | 24 records, one for each hour 0–23 |
| `demand_kwh` | Energy the campus needs during that hour |
| `solar_kwh` | Forecast solar energy before note-based reductions |
| `tariff_bdt_per_kwh` | Cost of each kWh imported from the grid |
| `capacity_kwh` | Maximum battery energy |
| `initial_energy_kwh` | Battery energy before hour 0 |
| `minimum_energy_kwh` | Baseline battery reserve |
| `max_charge_kwh_per_hour` | Maximum energy charged during one hour |
| `max_discharge_kwh_per_hour` | Maximum energy discharged during one hour |

### Directives

Each note produces exactly one entry in `directive_interpretation`, in original
note order. `note_index` starts at zero. The explanation may use different wording
from the reference, but the machine-checkable meaning must agree.

| Directive | Adjustment | Meaning |
| --- | --- | --- |
| `solar_reduction` | `hours`, `factor` | Multiply forecast solar by the remaining usable fraction |
| `minimum_battery_reserve` | `hours`, `minimum_energy_kwh` | Require that reserve at the end of each listed hour |
| `no_charge_window` | `hours` | Prohibit charging in those hours |
| `no_discharge_window` | `hours` | Prohibit discharging in those hours |
| `max_grid_window` | `hours`, `max_grid_kwh` | Cap grid imports separately in every listed hour |
| `no_op` | `null` | Note does not affect today's energy schedule |

The pack uses **start-inclusive, end-exclusive windows**: 1 PM to 3 PM means
`[13, 14]`, not `[13, 14, 15]`. An 80% solar reduction leaves `factor=0.2`.
A 50% reserve for a 200 kWh battery means `minimum_energy_kwh=100`.
Only `no_op` has `applies=false`; every actual constraint has `applies=true`.
Unrelated notes still need an entry; they must not disappear from the response.

### Worked example: SAMPLE-01

The first note says solar panel cleaning leaves 25% usable solar from noon to
2 PM. Its directive is `solar_reduction`, with `hours=[12,13]` and `factor=0.25`.
The registration-deadline note is unrelated and becomes `no_op`.

At hour 12, forecast solar is 180 kWh, so effective solar is:

```text
180 × 0.25 = 45 kWh
```

The reference schedule supplies 185 kWh of demand with 90 kWh from the grid,
45 kWh from solar, and 50 kWh discharged from the battery:

```text
90 + 45 + 50 = 185 kWh
```

The battery moves from 155 to 105 kWh that hour. Across the full day, the reference
uses **2,692.5 kWh** of grid energy, costs **BDT 38,365**, and has a peak hourly grid
import of **175 kWh**. It finishes with the initial **110 kWh** in the battery.

### What each case checks

| Case | Main requirement | Reference cost (BDT) |
| --- | --- | ---: |
| SAMPLE-01 | 25% solar remains at hours 12–13; unrelated note becomes `no_op` | 38,365 |
| SAMPLE-02 | No charging at hours 2, 3, 4 | 42,885 |
| SAMPLE-03 | 50% of 200 kWh capacity becomes a 100 kWh reserve at hours 18–20 | 35,480 |
| SAMPLE-04 | No discharging at hours 18, 19 | 40,495 |
| SAMPLE-05 | Grid import ≤155 kWh per hour at hours 18–20 | 33,950 |
| SAMPLE-06 | 50% solar remains at hours 10–11; no charging at 14–15; distractor | 34,090 |
| SAMPLE-07 | 90 kWh reserve at hours 18–21 and grid cap of 180 kWh at 19–20 | 38,550 |
| SAMPLE-08 | No charging at 11–12; no discharging at 17–18 | 37,665 |
| SAMPLE-09 | 80% solar reduction becomes factor 0.2 at 11–13; distractor | 34,873 |
| SAMPLE-10 | 80 kWh reserve at 18–21 and grid cap of 190 kWh at 19–21; distractor | 41,620 |

### How to judge a returned schedule

A different hourly action sequence can still be correct. Compare directive
semantics, feasibility, and optimal cost rather than demanding identical JSON.

For each hour, replay:

```text
grid + solar_used + discharge = demand + charge
battery_energy_after = battery_energy_before + charge - discharge
hourly_cost = grid × tariff
```

Check solar availability, battery capacity and reserve, hourly action limits, all
directives, and zero battery action when `idle`. Hour 23 must end at the initial
battery energy. Then recompute:

```text
total_grid_kwh = sum(hourly grid imports)
total_cost_bdt = sum(hourly grid import × hourly tariff)
peak_grid_kwh = max(hourly grid imports)
```

The pack allows absolute differences up to **0.01 kWh or 0.01 BDT**, unless the
judge specifies something stricter. Grid totals and peaks must agree with the
returned schedule; do not require the reference peak for every alternative
optimal schedule. Cost is the optimization objective, not peak reduction.
Do not hard-code public note wording, scenario IDs, or reference schedules;
hidden cases may paraphrase the same requirements.

## Compatibility gaps

These are current implementation facts, not rules to copy into a competition solution.

| Area | Public pack requires | Current backend | Required follow-up |
| --- | --- | --- | --- |
| Note input | Array of strings, 1–3 notes | Accepts strings and assigns indexes internally; also allows zero notes for baseline runs | Input format aligned |
| Time windows | Exclude the ending hour | Gemini prompt and offline parser include it | Align interpretation and tests with end-exclusive windows |
| Unrelated notes | `no_op` for distractors | Prompt only permits `no_op` for an explicit request for no constraints; offline parser rejects distractors | Teach relevance classification without ignoring meaningful constraints |
| Percentage reserves | Convert percentage using capacity | Gemini receives notes only, without battery capacity | Supply needed scenario context and validate conversion |

Send `operator_notes` as strings; do not wrap them in `note_index` / `text`
objects. Indexes are assigned internally and returned in `directive_interpretation`.
For example:

```json
"operator_notes": [
  "Solar output will drop to about 20% from 1 PM to 3 PM.",
  "Do not charge the battery between 2 PM and 4 PM."
]
```

This is a field excerpt; include `scenario_id`, `hours`, and `battery` in the full
request. Natural-language notes require Gemini mode; offline mode still accepts
only its documented templates.

During the earlier sample-pack review (before the string-note update):

- All ten unchanged `case.input` objects failed the current canonical schema.
- After adapting note objects and supplying the pack's expected directives
  directly, all ten reference schedules passed independent replay, and their
  reported metrics matched recomputation.
- Solving those same scenarios with the supplied directives produced all ten
  reference optimal costs, with valid schedules.

This verifies the deterministic optimizer against the pack's ground truth. It
**does not** verify Gemini interpretation or demonstrate an end-to-end API pass.
No live Gemini calls were made for this review. The subsequent string-note update fixes the request format only; it does not
resolve the remaining interpretation gaps.

## Current API contracts

Until the compatibility changes are implemented, use the repository's existing
examples and the schemas at `/docs`.

| Field | Canonical backend request | Frontend request |
| --- | --- | --- |
| Scenario name/ID | `scenario_id` | `name` |
| Operator notes | `operator_notes: ["..."]` | `notes: ["..."]` |
| Charge limit | `battery.max_charge_kwh_per_hour` | `battery.max_charge_kwh` |
| Discharge limit | `battery.max_discharge_kwh_per_hour` | `battery.max_discharge_kwh` |
| Hours | Exactly 0–23, ascending | Exactly 0–23; sorted by adapter |

Both accept `hours` with the same demand, solar, and tariff fields, and the same
battery capacity, initial energy, and minimum energy fields. Numeric inputs must
be finite and nonnegative; capacity must be positive; minimum ≤ initial ≤ capacity.
Notes must be nonblank and at most 1,000 characters. Unknown fields are rejected.

The canonical response contains `scenario_id`, `directive_interpretation`,
`hourly_plan`, `total_grid_kwh`, `total_cost_bdt`, `peak_grid_kwh`, `plan_summary`,
and an extra `validation` object. Each hourly plan includes `hour`, `grid_kwh`,
`solar_used_kwh`, `battery_action`, `battery_kwh`, and `battery_energy_after_kwh`.
`battery_kwh` is the action magnitude, not the stored energy.

The frontend response uses `schedule`, `summary`, and `interpretations`, plus
metrics and `validation`. Schedule rows contain the input hour fields and
`grid_kwh`, `solar_used_kwh`, `charge_kwh`, `discharge_kwh`, `battery_energy_kwh`,
and `cost_bdt`.

The validator reports `valid`, `energy_balance`, `battery_constraints`,
`solar_constraints`, `directive_constraints`, and `battery_neutrality`.
An invalid schedule cannot be returned as a successful optimization.

## Implementation and configuration

The optimizer uses SciPy HiGHS linear programming with lossless battery storage,
no grid export, optional solar curtailment, and equal initial/final battery energy.
Signed battery flow prevents simultaneous charge and discharge. Reserves apply
to end-of-hour energy. Overlapping reserves take the maximum, grid caps the minimum,
bans accumulate, and solar factors multiply. These overlap conventions are current
implementation choices; the supplied public pack does not establish every possible
overlap or overnight edge case. Replay tolerance is `1e-6` kWh.

Gemini returns structured data validated with Pydantic before optimization. The
backend currently sends only notes to Gemini. Model output is not trusted to
calculate schedules or certify feasibility. Each HTTP operation has a 10-second
timeout; transport failures and HTTP 429/500/502/503/504 get at most one retry after
0.5 seconds. Invalid, blocked, or truncated output is rejected. The solver has a
5-second limit. Failures do not silently switch to offline or unconstrained results.

| Variable | Default | Purpose |
| --- | --- | --- |
| `NOTE_INTERPRETER` | `gemini` | Gemini interpretation or explicit offline `rules` |
| `GEMINI_API_KEY` | Unset | Backend-only credential |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Configurable model identifier |
| `CORS_ORIGINS` | localhost and 127.0.0.1 on port 3000 | Comma-separated browser origins |
| `PORT` | 8000 in Docker | Container port |

Offline mode accepts complete templates such as:

```text
Keep at least 8 kWh in the battery from 18:00 to 22:00.
Do not charge the battery between 17:00 and 20:00.
Do not discharge the battery from 18 to 22.
Limit grid to 10 kWh from 17 to 21.
Reduce solar by 30% from 10 to 14.
No additional constraints
```

It is case insensitive, accepts an optional final period, and supports `from H to H`
or `between H and H`, with optional `:00`. Its current endpoints are inclusive.
It is a local demo tool, **not a substitute for LLM interpretation of the public pack**.

## Frontend connection and storage

The browser posts scenario JSON to the Next.js route `/api/optimize-energy`, which
forwards it to FastAPI. Set `BACKEND_URL=http://127.0.0.1:8000` in
`frontend/.env.local`; that URL is also the development default. Production needs
an explicit backend URL reachable from the Next.js server. `NEXT_PUBLIC_API_URL`
remains a legacy fallback. Gemini credentials stay in the backend.

The UI starts with a labeled baseline preview. Optimize calls the backend and
requires `validation.valid=true`; errors are displayed instead of silently
returning a preview. Browser CORS is not needed for the same-origin proxy path.

**No database is required for this workflow.** FastAPI processes requests without
saving them. The frontend holds state in memory and can export/import scenario
JSON. Persistent scenarios, run history, accounts, and shared plans would need
storage. The public sample pack is test data, not a database requirement.

## Errors and checks

Errors use `{"error":{"code":"...","message":"..."}}`. Request validation also
includes `details` with field locations and validation messages.

| Status | Meaning |
| --- | --- |
| 409 | Constraints are infeasible |
| 422 | Missing/invalid input, unsupported note, or invalid offline interpretation |
| 500 | Computed schedule failed independent validation |
| 502 | Gemini request failed or returned invalid interpretation |
| 503 | Interpreter is not configured or solver failed |
| 504 | Interpreter request timed out |

```bash
python -m pytest -q
```

The automated suite covers API shapes, optimal costs, all directive types,
infeasibility, replay corruption, invalid inputs, CORS, and mocked Gemini responses.
Mocked responses do not prove natural-language accuracy on public or hidden cases.

Repository demo files are separate from the public pack:

| File | Expected result |
| --- | --- |
| `examples/tariff-savings.json` | BDT 5, 5 kWh grid energy; no notes |
| `examples/operator-constraints.json` | BDT 50 with discharge prohibited during demand |
| `examples/infeasible.json` | HTTP 409 with all grid imports prohibited |

Use offline mode for deterministic results with the two note-containing demos.

## Deployment and code map

From `backend/`:

```bash
docker build -t gridwise-api .
docker run --rm -p 8000:8000 --env-file .env gridwise-api
```

For Render, use root directory `backend`, build command
`pip install -r requirements.txt`, start command
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and health path `/health`.
Set environment variables in the hosting service and `BACKEND_URL` on the frontend
server. Docker and public deployment are not verified by the unit suite.

| File | Responsibility |
| --- | --- |
| `app/main.py` | Routes, CORS, errors, pipeline orchestration |
| `app/schemas/` | Request, directive, response, and frontend contracts |
| `app/interpreter.py` | Gemini request, offline parser, directive validation |
| `app/optimizer.py` | Constraint construction and minimum-cost dispatch |
| `app/validator.py` | Independent replay and metric calculation |
| `tests/` | Automated backend checks |
| `examples/` | Small local demo requests |

## Troubleshooting Gemini on Render

The deployed service reads Render environment variables, not your local `.env`.
Set `NOTE_INTERPRETER=gemini`, `GEMINI_API_KEY` to a valid replacement key, and
`GEMINI_MODEL=gemini-3.6-flash`, then redeploy. Never put the key in the frontend or
tracked example files.

Provider HTTP failures return 502 with a diagnostic code:

| Code | Next step |
| --- | --- |
| `gemini_key_blocked` | Revoke the exposed key, create a replacement, update Render and redeploy |
| `gemini_access_denied` | Check the key and its permissions/API restrictions |
| `gemini_quota_exceeded` | Check project quota, rate limits, and billing |
| `gemini_model_unavailable` | Check the configured model identifier and availability |
| `gemini_request_rejected` | Check the request schema, model support, and project configuration |
| `interpreter_failed` | Check provider availability or backend network access |

Logs record the upstream HTTP status and diagnostic code, without provider response
bodies, keys, or note text. Older deployments return only the generic
`interpreter_failed` message; deploy the updated backend to get these diagnostics.

Google documents that keys detected as leaked may be blocked:
[Gemini troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting).

If `gemini_model_unavailable` persists even though your model appears in Google's
model list, test an actual structured generation request in **Render Shell**, from
its backend working directory:

```bash
python -m app.check_gemini
```

This uses Render's actual environment and the same request schema as the backend.
It prints the selected model, upstream HTTP status, and Google's error message
with the API key redacted. It makes a Gemini generation request and can consume
quota. A successful model listing alone does not verify generation access.

To compare with your local environment, run from the repository root:

```bash
cd backend
source .venv/bin/activate
GEMINI_MODEL=gemini-3.6-flash python -m app.check_gemini
```

If `GEMINI_API_KEY` is not exported, the diagnostic prompts for it securely. It
does not read `.env` automatically. A local pass combined with a Render failure
points to a deployment/environment difference; compare keys and settings without
sharing credentials. Deploy this diagnostic module before running it on Render.
