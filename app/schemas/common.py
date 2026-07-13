from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ID_RE = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
PHONE_RE = r"^\+?[0-9 ()-]{6,24}$"
TZ_OFFSET_RE = r"^[+-][0-1][0-9]:[0-5][0-9]$"


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("*", mode="before")
    @classmethod
    def reject_control_chars(cls, value: Any) -> Any:
        if isinstance(value, str) and CONTROL_CHAR_RE.search(value):
            raise ValueError("Control characters are not allowed")
        return value


class StatusResponse(BaseModel):
    status: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: str
    app_env: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    app_env: str
    checks: dict[str, bool]


class LocationInput(StrictRequestModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    place_name: str = Field(min_length=1, max_length=160)


class DateString(StrictRequestModel):
    value: str = Field(min_length=10, max_length=10)

    @field_validator("value")
    @classmethod
    def valid_iso_date(cls, value: str) -> str:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Date must be YYYY-MM-DD") from exc
        return value


def parse_iso_datetime(value: str, field_name: str = "datetime") -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO datetime") from exc
