import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.errors import EnergyError
from app.interpreter import interpret
from app.optimizer import optimize
from app.schemas.frontend import FrontendScenario, FrontendResponse
from app.schemas.request import ScenarioCreate
from app.schemas.response import OptimizationResponse
from app.validator import metrics, validate_schedule

app = FastAPI(title='NRG Grid API', version='1.0.0')
app.add_middleware(CORSMiddleware,
                   allow_origins=[x.strip() for x in os.getenv(
                       'CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',') if x.strip()],
                   allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])


@app.exception_handler(EnergyError)
async def energy_error_handler(request: Request, exc: EnergyError):
    return JSONResponse(status_code=exc.status, content={'error': {'code': exc.code, 'message': exc.message}})


@app.exception_handler(RequestValidationError)
async def request_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'error': {'code': 'invalid_request',
                                                            'message': 'Request validation failed.', 'details': [
                                                                {'location': list(e['loc']), 'message': e['msg'], 'type': e['type']} for e in exc.errors()]}})


@app.get('/')
def read_root() -> dict[str, str]:
    return {'message': 'NRG Grid API'}


@app.get('/health')
def health_check() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/optimize-energy', response_model=OptimizationResponse | FrontendResponse,
          responses={409: {'description': 'Infeasible scenario'}, 422: {'description': 'Invalid request or unsupported note'},
                     502: {'description': 'Invalid or failed interpretation'}, 503: {'description': 'Service unavailable'},
                     504: {'description': 'Interpreter timeout'}})
def optimize_energy(payload: ScenarioCreate | FrontendScenario):
    try:
        scenario = payload.canonical() if isinstance(
            payload, FrontendScenario) else payload
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    directives = interpret(scenario)
    plans = optimize(scenario, directives)
    validation = validate_schedule(scenario, directives, plans)
    if not validation.valid:
        raise EnergyError(500, 'schedule_validation_failed',
                          'The computed schedule failed independent validation.')
    totals = metrics(scenario, plans)
    summary = (f"Validated minimum-cost schedule: {totals['total_grid_kwh']:.2f} kWh from the grid "
               f"at BDT {totals['total_cost_bdt']:.2f}; peak hourly grid use {totals['peak_grid_kwh']:.2f} kWh. "
               'The battery finishes at its initial energy.')
    if isinstance(payload, FrontendScenario):
        return FrontendResponse(schedule=[dict(
            **h.model_dump(), grid_kwh=p.grid_kwh, solar_used_kwh=p.solar_used_kwh,
            charge_kwh=p.battery_kwh if p.battery_action == 'charge' else 0,
            discharge_kwh=p.battery_kwh if p.battery_action == 'discharge' else 0,
            battery_energy_kwh=p.battery_energy_after_kwh,
            cost_bdt=p.grid_kwh*h.tariff_bdt_per_kwh,
        ) for h, p in zip(scenario.hours, plans)], summary=summary, interpretations=[dict(
            note=scenario.operator_notes[d.note_index], directive=d.directive_type,
            explanation=d.explanation) for d in directives], validation=validation, **totals)
    return OptimizationResponse(scenario_id=scenario.scenario_id, directive_interpretation=directives,
                                hourly_plan=plans, plan_summary=summary, validation=validation, **totals)
