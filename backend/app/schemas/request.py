from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HourData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hour: int = Field(..., ge=0, le=23)
    demand_kwh: float = Field(..., ge=0)
    solar_kwh: float = Field(..., ge=0)
    tariff_bdt_per_kwh: float = Field(..., ge=0)


class BatteryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capacity_kwh: float = Field(..., gt=0)
    initial_energy_kwh: float = Field(..., ge=0)
    minimum_energy_kwh: float = Field(..., ge=0)
    max_charge_kwh_per_hour: float = Field(..., ge=0)
    max_discharge_kwh_per_hour: float = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_energy_limits(self):
        if self.initial_energy_kwh > self.capacity_kwh:
            raise ValueError(
                "initial_energy_kwh cannot exceed capacity_kwh"
            )

        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError(
                "minimum_energy_kwh cannot exceed capacity_kwh"
            )

        return self


class OperatorNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_index: int = Field(..., ge=0)
    text: str = Field(..., min_length=1)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Operator note cannot be empty")

        return value


class ScenarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(..., min_length=1)

    operator_notes: list[OperatorNote] = Field(
        ...,
        min_length=1,
        max_length=3
    )

    hours: list[HourData] = Field(
        ...,
        min_length=24,
        max_length=24
    )

    battery: BatteryConfig

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("scenario_id cannot be empty")

        return value

    @model_validator(mode="after")
    def validate_scenario(self):
        # Hours must be exactly 0, 1, 2, ..., 23
        hour_values = [hour.hour for hour in self.hours]

        if hour_values != list(range(24)):
            raise ValueError(
                "hours must contain exactly 24 entries from 0 to 23 "
                "in ascending order"
            )

        # Note indexes must be sequential: 0, 1, 2, ...
        note_indexes = [
            note.note_index for note in self.operator_notes
        ]

        expected_indexes = list(range(len(self.operator_notes)))

        if note_indexes != expected_indexes:
            raise ValueError(
                "operator note indexes must start at 0 and be sequential"
            )

        return self
