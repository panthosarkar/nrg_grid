Build GridWise-AI in **8 phases**, getting the deterministic optimizer working before integrating the LLM.

This plan follows your architecture document and the existing `frontend/` Next.js and `backend/` FastAPI setup. The document references a competition problem statement that wasn’t provided, so exact request/response fields and ambiguous rules should be confirmed in Phase 1.

**Phase 1 — Define the API contract and energy rules**

- Define Pydantic schemas for the 24 hourly records, battery parameters, operator notes, directives, and optimization response.
- Require each hour from 0–23 exactly once; validate numeric ranges and battery limits.
- Confirm battery efficiency, whether simultaneous charging/discharging is allowed, reserve timing, overlapping directives, and the meaning of `applies`.
- Define responses for invalid requests, unsupported notes, LLM failures, and infeasible scenarios.

**Checkpoint:** Valid example requests and expected response structures are documented and validated.

**Phase 2 — Build the deterministic optimizer**

- Implement the cost objective, hourly energy balance, solar availability, battery bounds, and charge/discharge limits.
- Enforce final battery energy equal to initial battery energy.
- Implement the constraint builder for all six directive types.
- Use manually constructed directives while developing the solver.
- Return explicit infeasibility results when constraints cannot be satisfied.

**Checkpoint:** The optimizer produces correct schedules for hand-checkable scenarios, including cheap charging hours, expensive discharge hours, excess solar, and grid caps.

**Phase 3 — Independently validate every schedule**

- Build a replay validator that checks all 24 hours.
- Recalculate battery state, energy balance, solar usage, action limits, and directive compliance.
- Verify the end-of-day battery requirement.
- Recalculate total grid energy, total cost, and peak hourly grid usage.
- Define numerical tolerances for solver output.

**Checkpoint:** Valid schedules pass; deliberately corrupted schedules fail. Invalid schedules cannot be returned as successful results.

**Phase 4 — Implement note interpretation**

- Build the LLM interpreter and structured-output prompt.
- Produce one directive per note, preserving its association with the original note.
- Validate directive types, hours, values, and applicability in deterministic code.
- Support `solar_reduction`, `minimum_battery_reserve`, `no_charge_window`, `no_discharge_window`, `max_grid_window`, and `no_op`.
- Define how ambiguous or unsupported notes are handled instead of silently ignoring meaningful constraints.
- Keep model credentials in backend environment variables.

**Checkpoint:** Paraphrased notes yield equivalent directives; malformed or unsupported output cannot reach the optimizer.

**Phase 5 — Connect the complete API pipeline**

Implement `POST /optimize-energy` through:

```text
Request validation → LLM interpretation → Directive validation
→ Constraint builder → Optimizer → Schedule validation → Response
```

- Add interpretation results, the 24-hour schedule, aggregate metrics, and a factual summary.
- Add LLM timeouts, bounded retries, and structured error handling.
- Keep `GET /health` available for deployment checks.

**Checkpoint:** A single request completes the full pipeline, and failures return clear, consistent errors.

**Phase 6 — Build the Next.js interface**

- Add inputs for hourly demand, solar, tariffs, battery configuration, and operator notes.
- Provide sample scenarios and JSON import.
- Display interpreted directives, cost, grid usage, battery state, and the hourly schedule.
- Add charts for demand, solar, grid usage, and battery energy.
- Handle loading, validation errors, and infeasible scenarios.
- Configure the backend URL and backend CORS for the deployed frontend.

**Checkpoint:** A user can submit a scenario and understand its results without using API tools.

**Phase 7 — Test against realistic and adversarial scenarios**

- Cover zero solar, zero demand, battery boundary conditions, conflicting directives, and impossible grid caps.
- Test malformed JSON, missing/duplicate hours, ambiguous notes, and invalid LLM output.
- Verify known optimal results on small, hand-calculated cases.
- Exercise the complete frontend-to-backend flow.
- Record representative scenarios for a repeatable demo.

**Checkpoint:** The test suite passes, and each displayed metric matches the validated schedule.

**Phase 8 — Deploy and prepare the demo**

- Dockerize the backend and document environment variables.
- Configure Render with root directory `backend` and:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- Deploy the frontend and configure its API URL.
- Verify public health, documentation, and optimization endpoints.
- Prepare examples showing tariff savings, operator constraints, and infeasibility handling.

**Checkpoint:** The public application completes the demo scenarios reliably.

**Priority for the hackathon:** Complete Phases 1–5 first to deliver the core API. Begin automated checks during each phase; use Phase 7 for broader coverage. If time is tight, keep the frontend minimal and prioritize a correct, independently validated schedule over visual polish.