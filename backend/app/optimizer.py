"""Lossless, hourly linear dispatch. Positive battery flow means charging."""
import numpy as np
from scipy.optimize import linprog

from app.errors import EnergyError
from app.schemas.request import ScenarioCreate
from app.schemas.response import HourlyPlan


def optimize(scenario: ScenarioCreate, directives: list) -> list[HourlyPlan]:
    b = scenario.battery
    solar = [h.solar_kwh for h in scenario.hours]
    reserve = [b.minimum_energy_kwh] * 24
    grid_cap = [None] * 24
    charge = [b.max_charge_kwh_per_hour] * 24
    discharge = [b.max_discharge_kwh_per_hour] * 24
    for directive in directives:
        a = directive.structured_adjustment
        if not directive.applies:
            continue
        for h in a.hours:
            match directive.directive_type:
                case 'solar_reduction': solar[h] *= a.factor
                case 'minimum_battery_reserve': reserve[h] = max(reserve[h], a.minimum_energy_kwh)
                case 'max_grid_window': grid_cap[h] = min(grid_cap[h] if grid_cap[h] is not None else float('inf'), a.max_grid_kwh)
                case 'no_charge_window': charge[h] = 0
                case 'no_discharge_window': discharge[h] = 0
    if any(r > b.capacity_kwh for r in reserve):
        raise EnergyError(409, 'infeasible', 'The requested battery reserve exceeds capacity.')

    # Variables are grid[24], solar_used[24], net_charge[24], end_energy[24].
    objective = np.zeros(96)
    objective[:24] = [h.tariff_bdt_per_kwh for h in scenario.hours]
    equalities, values = [], []
    for h in range(24):
        balance = np.zeros(96)
        balance[h], balance[24+h], balance[48+h] = 1, 1, -1
        equalities.append(balance)
        values.append(scenario.hours[h].demand_kwh)
        state = np.zeros(96)
        state[72+h], state[48+h] = 1, -1
        if h:
            state[72+h-1] = -1
        equalities.append(state)
        values.append(b.initial_energy_kwh if h == 0 else 0)
    final = np.zeros(96)
    final[95] = 1
    equalities.append(final)
    values.append(b.initial_energy_kwh)
    bounds = ([(0, cap) for cap in grid_cap] + [(0, s) for s in solar]
              + [(-discharge[h], charge[h]) for h in range(24)]
              + [(r, b.capacity_kwh) for r in reserve])
    result = linprog(objective, A_eq=equalities, b_eq=values, bounds=bounds,
                     method='highs', options={'time_limit': 5.0})
    if result.status == 2:
        raise EnergyError(409, 'infeasible', 'No schedule satisfies the battery and operator constraints.')
    if not result.success:
        raise EnergyError(503, 'solver_failed', 'The optimizer could not produce an optimal schedule.')
    plans = []
    for h in range(24):
        flow = float(result.x[48+h])
        plans.append(HourlyPlan(
            hour=h, grid_kwh=max(0.0, float(result.x[h])),
            solar_used_kwh=max(0.0, float(result.x[24+h])),
            battery_action='charge' if flow > 0 else 'discharge' if flow < 0 else 'idle',
            battery_kwh=abs(flow), battery_energy_after_kwh=max(0.0, float(result.x[72+h])),
        ))
    return plans
