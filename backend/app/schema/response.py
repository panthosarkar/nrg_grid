from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.directive import DirectiveInterpretation


class HourlyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hour: int = Field(..., ge=0, le=23)
    grid_kwh: float = Field(..., ge=0)
    solar_used_kwh: float = Field(..., ge=0)
    battery_action: Literal["charge", "discharge", "idle"]
    battery_kwh: float = Field(..., ge=0)
    battery_energy_after_kwh: float = Field(..., ge=0)


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    energy_balance: bool
    battery_constraints: bool
    solar_constraints: bool
    directive_constraints: bool
    battery_neutrality: bool


class OptimizationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str

    directive_interpretation: list[DirectiveInterpretation]

    hourly_plan: list[HourlyPlan]

    total_grid_kwh: float = Field(..., ge=0)
    total_cost_bdt: float = Field(..., ge=0)
    peak_grid_kwh: float = Field(..., ge=0)

    plan_summary: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_hourly_plan(self):
        if len(self.hourly_plan) != 24:
            raise ValueError(
                "hourly_plan must contain exactly 24 entries"
            )

        hours = [plan.hour for plan in self.hourly_plan]

        if hours != list(range(24)):
            raise ValueError(
                "hourly_plan must contain hours 0 to 23 in ascending order"
            )

        return self


class OptimizationRunInDB(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    scenario_id: str
    schema_version: int = 1

    status: Literal[
        "pending",
        "running",
        "completed",
        "failed",
    ]

    result: OptimizationResponse

    validation: ValidationResult

    created_at: str
    completed_at: str | None = None
