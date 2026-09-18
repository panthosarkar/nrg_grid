import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.interpreter import ParsedNote, ParsedNotes, interpret, validate_interpretations
from app.errors import EnergyError
from app.optimizer import optimize
from app.schemas.request import ScenarioCreate
from app.validator import validate_schedule

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('NOTE_INTERPRETER', 'rules')


@pytest.fixture
def payload():
    return dict(scenario_id='test', operator_notes=[],
                hours=[dict(hour=h, demand_kwh=1, solar_kwh=0, tariff_bdt_per_kwh=2) for h in range(24)],
                battery=dict(capacity_kwh=10, initial_energy_kwh=0, minimum_energy_kwh=0,
                             max_charge_kwh_per_hour=5, max_discharge_kwh_per_hour=5))


def directive(kind, hours, value=None, index=0):
    return ParsedNote(note_index=index, directive_type=kind, hours=hours, value=value, explanation='Test')


def with_directives(payload, notes):
    payload['operator_notes'] = ['test' for _ in notes]
    scenario = ScenarioCreate(**payload)
    return scenario, validate_interpretations(scenario, ParsedNotes(notes=notes))


def test_health_and_openapi():
    assert client.get('/health').json() == {'status': 'ok'}
    assert '/optimize-energy' in client.get('/openapi.json').json()['paths']


def test_baseline(payload):
    response = client.post('/optimize-energy', json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['total_cost_bdt'] == pytest.approx(48)
    assert data['total_grid_kwh'] == pytest.approx(24)
    assert data['validation']['valid']
    assert len(data['hourly_plan']) == 24


def test_arbitrage(payload):
    for h in payload['hours']:
        h.update(demand_kwh=0, tariff_bdt_per_kwh=10)
    payload['hours'][0]['tariff_bdt_per_kwh'] = 1
    payload['hours'][1]['demand_kwh'] = 5
    data = client.post('/optimize-energy', json=payload).json()
    assert data['total_cost_bdt'] == pytest.approx(5)
    assert data['hourly_plan'][0]['battery_action'] == 'charge'
    assert data['hourly_plan'][1]['battery_action'] == 'discharge'


def test_solar_and_zero_demand(payload):
    for h in payload['hours']:
        h.update(solar_kwh=20, demand_kwh=0)
    data = client.post('/optimize-energy', json=payload).json()
    assert data['total_cost_bdt'] == 0
    assert data['total_grid_kwh'] == 0
    assert data['validation']['valid']


@pytest.mark.parametrize('kind,value', [('no_charge_window', None), ('no_discharge_window', None),
                                       ('minimum_battery_reserve', 2), ('max_grid_window', 0.5),
                                       ('solar_reduction', 0.5)])
def test_directives(payload, kind, value):
    payload['battery']['initial_energy_kwh'] = 3
    for h in payload['hours']:
        h['solar_kwh'] = 2
    scenario, ds = with_directives(payload, [directive(kind, [5, 6], value)])
    plan = optimize(scenario, ds)
    assert validate_schedule(scenario, ds, plan).valid
    if kind == 'solar_reduction':
        assert all(plan[h].solar_used_kwh <= 1 + 1e-6 for h in [5, 6])


def test_infeasible(payload):
    payload['operator_notes'] = ['Limit grid to 0 kWh from 0 to 23.']
    response = client.post('/optimize-energy', json=payload)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'infeasible'


def test_overlap_and_excess_reserve(payload):
    scenario, ds = with_directives(payload, [directive('minimum_battery_reserve', [1], 11)])
    with pytest.raises(EnergyError) as e:
        optimize(scenario, ds)
    assert e.value.status == 409
    for h in payload['hours']:
        h['solar_kwh'] = 8
    scenario, ds = with_directives(payload, [directive('solar_reduction', [0], .5),
                                           directive('solar_reduction', [0], .5, 1)])
    plan = optimize(scenario, ds)
    assert plan[0].solar_used_kwh <= 2 + 1e-6
    assert validate_schedule(scenario, ds, plan).valid


@pytest.mark.parametrize('mutation', ['duplicate', 'missing', 'negative', 'below_minimum', 'unknown', 'boolean'])
def test_bad_inputs(payload, mutation):
    if mutation == 'duplicate': payload['hours'][1]['hour'] = 0
    if mutation == 'missing': payload['hours'].pop()
    if mutation == 'negative': payload['hours'][0]['solar_kwh'] = -1
    if mutation == 'below_minimum': payload['battery']['minimum_energy_kwh'] = 2
    if mutation == 'unknown': payload['extra'] = 1
    if mutation == 'boolean': payload['hours'][0]['hour'] = True
    assert client.post('/optimize-energy', json=payload).status_code == 422


def test_nonfinite_and_malformed(payload):
    payload['hours'][0]['solar_kwh'] = float('inf')
    with pytest.raises(ValidationError): ScenarioCreate(**payload)
    assert client.post('/optimize-energy', content='{').status_code == 422


@pytest.mark.parametrize('field', ['grid_kwh', 'solar_used_kwh', 'battery_kwh', 'battery_energy_after_kwh'])
def test_replay_rejects_corruption(payload, field):
    scenario = ScenarioCreate(**payload)
    plan = optimize(scenario, [])
    setattr(plan[0], field, getattr(plan[0], field) + 1)
    assert not validate_schedule(scenario, [], plan).valid


def test_replay_blocks_success(payload, monkeypatch):
    import app.main as main
    original = main.optimize
    def corrupt(s, ds):
        plan = original(s, ds)
        plan[0].grid_kwh += 1
        return plan
    monkeypatch.setattr(main, 'optimize', corrupt)
    assert client.post('/optimize-energy', json=payload).status_code == 500


def test_frontend_contract(payload):
    payload['battery']['initial_energy_kwh'] = 8
    battery = payload['battery']
    battery['max_charge_kwh'] = battery.pop('max_charge_kwh_per_hour')
    battery['max_discharge_kwh'] = battery.pop('max_discharge_kwh_per_hour')
    frontend = dict(name='Campus', hours=list(reversed(payload['hours'])), battery=battery, notes=[
        'Keep at least 8 kWh in the battery from 18:00 to 22:00.',
        'Do not charge the battery between 17:00 and 20:00.'])
    response = client.post('/optimize-energy', json=frontend)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data['schedule']) == 24
    assert len(data['interpretations']) == 2
    assert data['schedule'][18]['battery_energy_kwh'] >= 8 - 1e-6
    assert data['schedule'][17]['charge_kwh'] == 0
    assert data['total_cost_bdt'] == pytest.approx(sum(h['cost_bdt'] for h in data['schedule']))
    frontend['battery']['capacity_kwh'] = -1
    assert client.post('/optimize-energy', json=frontend).status_code == 422


def test_rules_reject_ambiguity(payload):
    payload['operator_notes'] = ['Keep plenty of battery for later']
    response = client.post('/optimize-energy', json=payload)
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'unsupported_note'


def test_overnight_and_noop(payload):
    payload['operator_notes'] = ['Do not charge the battery from 22:00 to 2:00.',
                                 'No additional constraints']
    ds = interpret(ScenarioCreate(**payload))
    assert ds[0].structured_adjustment.hours == [0, 1, 2, 22, 23]
    assert not ds[1].applies


@pytest.mark.parametrize('failure', ['missing', 'wrong_index', 'bad_factor', 'unsupported'])
def test_invalid_interpretations(payload, failure):
    payload['operator_notes'] = ['Test']
    notes = [directive('solar_reduction', [0], .5)]
    if failure == 'missing': notes = []
    if failure == 'wrong_index': notes[0].note_index = 1
    if failure == 'bad_factor': notes[0].value = 2
    if failure == 'unsupported': notes[0].directive_type = 'unsupported'
    with pytest.raises((ValueError, EnergyError)):
        validate_interpretations(ScenarioCreate(**payload), ParsedNotes(notes=notes))


@pytest.mark.parametrize('outcome,status,attempts', [
    ('success', 200, 1), ('refusal', 502, 1), ('timeout', 504, 2),
    ('failure', 502, 2), ('rate_limit', 502, 2), ('unauthorized', 502, 1),
    ('retry_success', 200, 2), ('invalid_json', 502, 1), ('truncated', 502, 1),
    ('bad_directive', 502, 1), ('bad_envelope', 502, 1),
])
def test_llm_pipeline(payload, monkeypatch, outcome, status, attempts):
    import app.interpreter as module
    monkeypatch.setenv('NOTE_INTERPRETER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-test')
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    payload['operator_notes'] = ['No constraints']
    requests = []

    def handler(request):
        requests.append(request)
        assert str(request.url) == 'https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent'
        assert request.headers['x-goog-api-key'] == 'test-only'
        assert request.extensions['timeout']['read'] == 10
        body = json.loads(request.content)
        assert body['systemInstruction']['parts'][0]['text'] == module.PROMPT
        assert body['generationConfig']['responseMimeType'] == 'application/json'
        assert body['generationConfig']['responseJsonSchema'] == ParsedNotes.model_json_schema()
        assert 'battery' not in json.loads(body['contents'][0]['parts'][0]['text'])[0]
        if outcome == 'timeout': raise httpx.ReadTimeout('Timed out', request=request)
        if outcome == 'failure': raise httpx.ConnectError('Failed', request=request)
        if outcome == 'rate_limit': return httpx.Response(429)
        if outcome == 'unauthorized': return httpx.Response(403)
        if outcome == 'retry_success' and len(requests) == 1: return httpx.Response(503)
        if outcome == 'refusal': return httpx.Response(200, json={'promptFeedback': {'blockReason': 'SAFETY'}})
        if outcome == 'bad_envelope': return httpx.Response(200, json={'candidates': None})
        notes = ParsedNotes(notes=[directive('no_op', [])])
        if outcome == 'bad_directive': notes.notes[0].note_index = 9
        text = '{' if outcome == 'invalid_json' else notes.model_dump_json()
        return httpx.Response(200, json={'candidates': [{
            'finishReason': 'MAX_TOKENS' if outcome == 'truncated' else 'STOP',
            'content': {'parts': [{'text': text}]},
        }]})

    original_client = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **kwargs: original_client(
        transport=httpx.MockTransport(handler), **kwargs))
    response = client.post('/optimize-energy', json=payload)
    assert response.status_code == status, response.text
    assert len(requests) == attempts
    assert 'test-only' not in response.text


def test_gemini_is_default_and_requires_key(payload, monkeypatch):
    monkeypatch.delenv('NOTE_INTERPRETER', raising=False)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    payload['operator_notes'] = ['No constraints']
    response = client.post('/optimize-energy', json=payload)
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'interpreter_not_configured'


def test_cors():
    response = client.options('/optimize-energy', headers={'Origin': 'http://localhost:3000',
                                                         'Access-Control-Request-Method': 'POST'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:3000'


@pytest.mark.parametrize('name,status,cost', [('tariff-savings', 200, 5),
                                             ('operator-constraints', 200, 50),
                                             ('infeasible', 409, None)])
def test_documented_examples(name, status, cost):
    payload = json.loads((Path(__file__).parents[1] / 'examples' / f'{name}.json').read_text())
    response = client.post('/optimize-energy', json=payload)
    assert response.status_code == status
    if cost is not None:
        assert response.json()['total_cost_bdt'] == pytest.approx(cost)


@pytest.mark.parametrize('upstream,message,code', [
    (403, 'Your API key was reported as leaked. secret-test-value', 'gemini_key_blocked'),
    (400, 'API key not valid. secret-test-value', 'gemini_access_denied'),
    (401, 'Invalid credentials secret-test-value', 'gemini_access_denied'),
    (403, 'Permission denied secret-test-value', 'gemini_access_denied'),
    (429, 'Quota exceeded secret-test-value', 'gemini_quota_exceeded'),
    (404, 'Model not found secret-test-value', 'gemini_model_unavailable'),
    (400, 'Invalid schema secret-test-value', 'gemini_request_rejected'),
    (503, 'Unavailable secret-test-value', 'interpreter_failed'),
])
def test_provider_error_diagnostics(payload, monkeypatch, caplog, upstream, message, code):
    import app.interpreter as module
    monkeypatch.setenv('NOTE_INTERPRETER', 'gemini')
    payload['operator_notes'] = ['No constraints']
    def fail(_):
        response = httpx.Response(upstream, json={'error': {'message': message}},
                                  request=httpx.Request('POST', 'https://example.com'))
        response.raise_for_status()
    monkeypatch.setattr(module, 'gemini_notes', fail)
    response = client.post('/optimize-energy', json=payload)
    assert response.status_code == 502
    assert response.json()['error']['code'] == code
    assert f'upstream_http_status={upstream}' in caplog.text
    assert 'secret-test-value' not in response.text
    assert 'secret-test-value' not in caplog.text


def test_string_notes_contract(payload):
    payload['operator_notes'] = ['  No constraints  ', 'Do not charge the battery from 2 to 4.']
    scenario = ScenarioCreate(**payload)
    assert scenario.operator_notes[0] == 'No constraints'
    assert [n.note_index for n in scenario.indexed_notes] == [0, 1]
    response = client.post('/optimize-energy', json=payload)
    assert response.status_code == 200
    assert [d['note_index'] for d in response.json()['directive_interpretation']] == [0, 1]
    schema = client.get('/openapi.json').json()['components']['schemas']['ScenarioCreate']
    assert schema['properties']['operator_notes']['items']['type'] == 'string'


@pytest.mark.parametrize('notes', [[' '], ['x' * 1001], [123], [{'note_index': 0, 'text': 'No constraints'}], ['x'] * 4])
def test_invalid_string_notes(payload, notes):
    payload['operator_notes'] = notes
    assert client.post('/optimize-energy', json=payload).status_code == 422


def test_requested_note_format(payload):
    payload['operator_notes'] = [
        'Solar output will drop to about 20% from 1 PM to 3 PM.',
        'Do not charge the battery between 2 PM and 4 PM.',
    ]
    scenario = ScenarioCreate(**payload)
    assert [n.text for n in scenario.indexed_notes] == payload['operator_notes']


def test_gemini_diagnostic_redacts_provider_message(monkeypatch, capsys):
    import app.check_gemini as diagnostic
    monkeypatch.setenv('GEMINI_API_KEY', 'private-diagnostic-key')
    monkeypatch.setenv('GEMINI_MODEL', 'gemini-3.6-flash')
    def fail(_):
        response = httpx.Response(404, json={'error': {
            'status': 'NOT_FOUND', 'message': 'Resource missing for private-diagnostic-key'}},
            request=httpx.Request('POST', 'https://example.com'))
        response.raise_for_status()
    monkeypatch.setattr(diagnostic, 'gemini_notes', fail)
    assert diagnostic.main() == 1
    output = capsys.readouterr().out
    assert 'NOT_FOUND' in output
    assert '404' in output
    assert 'private-diagnostic-key' not in output
    assert '[REDACTED]' in output


def test_gemini_diagnostic_checks_success(monkeypatch, capsys):
    import app.check_gemini as diagnostic
    monkeypatch.setenv('GEMINI_API_KEY', 'private-diagnostic-key')
    monkeypatch.setattr(diagnostic, 'gemini_notes', lambda _: ParsedNotes(notes=[directive('no_op', [])]))
    assert diagnostic.main() == 0
    assert 'PASS:' in capsys.readouterr().out
