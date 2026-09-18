from pydantic import BaseModel, ConfigDict, Field

from app.schemas.request import HourData, ScenarioCreate
from app.schemas.response import ValidationResult


class FrontendBattery(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, strict=True)
    capacity_kwh: float
    initial_energy_kwh: float
    minimum_energy_kwh: float
    max_charge_kwh: float
    max_discharge_kwh: float


class FrontendScenario(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, strict=True)
    name: str
    hours: list[HourData] = Field(min_length=24, max_length=24)
    battery: FrontendBattery
    notes: list[str] = Field(max_length=3)

    def canonical(self):
        battery = self.battery.model_dump()
        battery['max_charge_kwh_per_hour'] = battery.pop('max_charge_kwh')
        battery['max_discharge_kwh_per_hour'] = battery.pop('max_discharge_kwh')
        return ScenarioCreate(scenario_id=self.name, hours=sorted(self.hours, key=lambda h: h.hour),
                              battery=battery,
                              operator_notes=self.notes)


class FrontendHour(HourData):
    grid_kwh: float
    solar_used_kwh: float
    charge_kwh: float
    discharge_kwh: float
    battery_energy_kwh: float
    cost_bdt: float


class FrontendInterpretation(BaseModel):
    note: str
    directive: str
    explanation: str


class FrontendResponse(BaseModel):
    schedule: list[FrontendHour]
    summary: str
    interpretations: list[FrontendInterpretation]
    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float
    validation: ValidationResult
