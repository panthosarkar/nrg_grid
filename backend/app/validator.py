"""Replay raw hourly decisions independently of the solver's constraint arrays."""
import math

from app.schemas.response import ValidationResult

TOLERANCE = 1e-6


def validate_schedule(scenario, directives, plans):
    checks = dict(energy_balance=True, battery_constraints=True, solar_constraints=True,
                  directive_constraints=True, battery_neutrality=True)
    if len(plans) != 24 or [p.hour for p in plans] != list(range(24)):
        return ValidationResult(valid=False, **{k: False for k in checks})
    energy = scenario.battery.initial_energy_kwh
    b = scenario.battery
    for h, plan in zip(scenario.hours, plans):
        numbers = [plan.grid_kwh, plan.solar_used_kwh, plan.battery_kwh, plan.battery_energy_after_kwh]
        if not all(math.isfinite(n) and n >= 0 for n in numbers):
            return ValidationResult(valid=False, **{k: False for k in checks})
        charging = plan.battery_kwh if plan.battery_action == 'charge' else 0
        discharging = plan.battery_kwh if plan.battery_action == 'discharge' else 0
        checks['battery_constraints'] &= plan.battery_action in ('charge', 'discharge', 'idle')
        checks['battery_constraints'] &= plan.battery_action != 'idle' or plan.battery_kwh <= TOLERANCE
        energy += charging - discharging
        checks['energy_balance'] &= abs(plan.grid_kwh + plan.solar_used_kwh + discharging - h.demand_kwh - charging) <= TOLERANCE
        checks['battery_constraints'] &= (
            b.minimum_energy_kwh - TOLERANCE <= energy <= b.capacity_kwh + TOLERANCE
            and charging <= b.max_charge_kwh_per_hour + TOLERANCE
            and discharging <= b.max_discharge_kwh_per_hour + TOLERANCE
            and abs(energy - plan.battery_energy_after_kwh) <= TOLERANCE)
        available = h.solar_kwh
        for d in directives:
            if not d.applies or h.hour not in d.structured_adjustment.hours:
                continue
            a = d.structured_adjustment
            match d.directive_type:
                case 'solar_reduction': available *= a.factor
                case 'minimum_battery_reserve': checks['directive_constraints'] &= energy >= a.minimum_energy_kwh - TOLERANCE
                case 'max_grid_window': checks['directive_constraints'] &= plan.grid_kwh <= a.max_grid_kwh + TOLERANCE
                case 'no_charge_window': checks['directive_constraints'] &= charging <= TOLERANCE
                case 'no_discharge_window': checks['directive_constraints'] &= discharging <= TOLERANCE
        checks['solar_constraints'] &= plan.solar_used_kwh <= available + TOLERANCE
    checks['battery_neutrality'] = abs(energy - b.initial_energy_kwh) <= TOLERANCE
    return ValidationResult(valid=all(checks.values()), **checks)


def metrics(scenario, plans):
    return dict(total_grid_kwh=sum(p.grid_kwh for p in plans),
                total_cost_bdt=sum(p.grid_kwh * h.tariff_bdt_per_kwh for h, p in zip(scenario.hours, plans)),
                peak_grid_kwh=max(p.grid_kwh for p in plans))
