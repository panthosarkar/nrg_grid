from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_hours(hours: list[int]) -> list[int]:
    if not hours:
        raise ValueError("hours cannot be empty")

    if any(hour < 0 or hour > 23 for hour in hours):
        raise ValueError("hours must be between 0 and 23")

    if len(hours) != len(set(hours)):
        raise ValueError("hours must be unique")

    if hours != sorted(hours):
        raise ValueError("hours must be in ascending order")

    return hours


class SolarReductionAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    hours: list[int]
    factor: float = Field(..., ge=0, le=1)

    @field_validator("hours")
    @classmethod
    def validate_hour_values(cls, value: list[int]) -> list[int]:
        return validate_hours(value)


class MinimumBatteryReserveAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    hours: list[int]
    minimum_energy_kwh: float = Field(..., ge=0)

    @field_validator("hours")
    @classmethod
    def validate_hour_values(cls, value: list[int]) -> list[int]:
        return validate_hours(value)


class WindowAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    hours: list[int]

    @field_validator("hours")
    @classmethod
    def validate_hour_values(cls, value: list[int]) -> list[int]:
        return validate_hours(value)


class MaxGridWindowAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    hours: list[int]
    max_grid_kwh: float = Field(..., ge=0)

    @field_validator("hours")
    @classmethod
    def validate_hour_values(cls, value: list[int]) -> list[int]:
        return validate_hours(value)


class SolarReductionDirective(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    note_index: int = Field(..., ge=0)
    applies: Literal[True]
    directive_type: Literal["solar_reduction"]
    structured_adjustment: SolarReductionAdjustment
    explanation: str = Field(..., min_length=1)


class MinimumBatteryReserveDirective(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    note_index: int = Field(..., ge=0)
    applies: Literal[True]
    directive_type: Literal["minimum_battery_reserve"]
    structured_adjustment: MinimumBatteryReserveAdjustment
    explanation: str = Field(..., min_length=1)


class NoChargeWindowDirective(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    note_index: int = Field(..., ge=0)
    applies: Literal[True]
    directive_type: Literal["no_charge_window"]
    structured_adjustment: WindowAdjustment
    explanation: str = Field(..., min_length=1)


class NoDischargeWindowDirective(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    note_index: int = Field(..., ge=0)
    applies: Literal[True]
    directive_type: Literal["no_discharge_window"]
    structured_adjustment: WindowAdjustment
    explanation: str = Field(..., min_length=1)


class MaxGridWindowDirective(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    note_index: int = Field(..., ge=0)
    applies: Literal[True]
    directive_type: Literal["max_grid_window"]
    structured_adjustment: MaxGridWindowAdjustment
    explanation: str = Field(..., min_length=1)


class NoOpDirective(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    note_index: int = Field(..., ge=0)
    applies: Literal[False]
    directive_type: Literal["no_op"]
    structured_adjustment: None = None
    explanation: str = Field(..., min_length=1)


DirectiveInterpretation = Annotated[
    Union[
        SolarReductionDirective,
        MinimumBatteryReserveDirective,
        NoChargeWindowDirective,
        NoDischargeWindowDirective,
        MaxGridWindowDirective,
        NoOpDirective,
    ],
    Field(discriminator="directive_type"),
]
