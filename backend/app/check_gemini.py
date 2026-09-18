"""Run with `python -m app.check_gemini` from backend/ to diagnose generation.

Uses process environment (including Render settings). Prompts securely for a key
when none is set. Makes one logical request with the backend's normal retry policy.
Never loads .env implicitly, logs the key, or dumps successful model output.
"""
import getpass
import json
import os

import httpx

from app.errors import EnergyError, safe_provider_message
from app.interpreter import gemini_notes, validate_interpretations
from app.schemas.request import ScenarioCreate


def main() -> int:
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        key = getpass.getpass('Gemini API key (hidden): ').strip()
        os.environ['GEMINI_API_KEY'] = key
    model = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash').strip()
    print(f'Model: {model}')
    print('API: v1beta / generateContent with backend structured-output schema')
    scenario = ScenarioCreate(
        scenario_id='gemini-diagnostic', operator_notes=['No additional constraints'],
        hours=[dict(hour=h, demand_kwh=0, solar_kwh=0, tariff_bdt_per_kwh=1) for h in range(24)],
        battery=dict(capacity_kwh=1, initial_energy_kwh=0, minimum_energy_kwh=0,
                     max_charge_kwh_per_hour=1, max_discharge_kwh_per_hour=1),
    )
    try:
        parsed = gemini_notes(scenario)
        validate_interpretations(scenario, parsed)
    except httpx.HTTPStatusError as exc:
        print(f'Google HTTP status: {exc.response.status_code}')
        try:
            error = exc.response.json().get('error', {})
            if not isinstance(error, dict):
                error = {}
        except (ValueError, AttributeError):
            error = {}
        print(json.dumps({
            'status': safe_provider_message(str(error.get('status', 'unknown')), key),
            'message': safe_provider_message(str(error.get('message', 'No JSON error message received.')), key),
        }, indent=2))
        return 1
    except httpx.HTTPError as exc:
        print(f'Network error: {type(exc).__name__} (details suppressed)')
        return 1
    except (ValueError, EnergyError):
        print('Configuration or structured-response validation failed. Check model/key settings and provider output support.')
        return 1
    print('PASS: Gemini generation and directive validation succeeded.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
