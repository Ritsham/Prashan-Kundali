from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.consultation_lifecycle import CONSULTATION_STATUSES, normalize_consultation_status


class ConsultationSourceType(str, Enum):
    prashna = "prashna"
    direct_consultation = "direct_consultation"
    matchmaking = "matchmaking"


class ConsultationChartType(str, Enum):
    prashna = "prashna"
    lagna = "lagna"
    matchmaking = "matchmaking"


class ConsultationStatus(str, Enum):
    requested = "requested"
    pending_payment = "pending_payment"
    confirmed = "confirmed"
    active = "active"
    refunded = "refunded"
    pending = "pending"
    reviewed = "reviewed"
    accepted = "accepted"
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    rejected = "rejected"
    waiting_queue = "waiting_queue"


class PlanetaryPosition(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    longitude: Optional[float] = None
    sign: Optional[str] = None
    sign_index: Optional[int] = None
    house: Optional[Union[int, str]] = None
    formatted_degree: Optional[str] = None
    nakshatra: Optional[str] = None
    pada: Optional[Union[int, str]] = None
    retrograde: Optional[bool] = None


ChartSignMap = dict[str, list[str]]


class ChartData(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
    question: Optional[dict[str, Any]] = None
    lagna: Optional[dict[str, Any]] = None
    signs: Optional[ChartSignMap] = None
    planets: Optional[list[PlanetaryPosition]] = None
    kp_system: Optional[dict[str, Any]] = None
    dashas: Optional[dict[str, Any]] = None
    divisional_charts: Optional[dict[str, ChartSignMap]] = None
    transit: Optional[dict[str, Any]] = None
    interpretation: Optional[Union[dict[str, Any], str]] = None


class AstrologySnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    chart_id: Optional[str] = None
    chart_type: ConsultationChartType
    chart: Optional[ChartData] = None
    interpretation: Optional[Union[dict[str, Any], str]] = None
    divisional_charts: Optional[dict[str, ChartSignMap]] = None
    planetary_positions: Optional[list[PlanetaryPosition]] = None
    house_positions: Optional[Union[dict[str, Any], list[Any]]] = None
    aspects: Optional[Union[dict[str, Any], list[Any]]] = None
    yogas: Optional[Union[dict[str, Any], list[Any]]] = None
    dashas: Optional[dict[str, Any]] = None
    kp_system: Optional[dict[str, Any]] = None
    calculation_metadata: Optional[dict[str, Any]] = None
    question_context: Optional[dict[str, Any]] = None
    source_result: Optional[dict[str, Any]] = None
    additional_calculations: Optional[dict[str, Any]] = None

    @field_validator("chart", mode="before")
    @classmethod
    def empty_chart_to_none(cls, value: Any) -> Any:
        return None if value == {} else value


class UserConsultationDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    mobile_number: str = Field(min_length=6, max_length=24, pattern=r"^\+?[0-9 ()-]{6,24}$")
    gender: Optional[str] = Field(default=None, pattern="^(male|female|other)$")
    date_of_birth: Optional[str] = Field(default=None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_of_birth: Optional[str] = Field(default=None, max_length=8, pattern=r"^\d{2}:\d{2}(:\d{2})?$")
    place: Optional[str] = Field(default=None, max_length=180)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    timezone: Optional[str] = Field(default=None, max_length=80)


class ConsultationDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=3, max_length=2000)
    additional_message: Optional[str] = Field(default=None, max_length=4000)
    preferred_date: Optional[str] = Field(default=None, max_length=40)
    preferred_time: Optional[str] = Field(default=None, max_length=120)
    consultation_mode: Optional[str] = Field(default=None, max_length=80)
    payment_status: Optional[str] = Field(default=None, max_length=40, pattern=r"^(not_paid|pending|created|paid|failed|refunded)?$")
    quoted_price: Optional[float] = Field(default=None, gt=0, le=100000)
    currency: Optional[str] = Field(default="INR", max_length=3, pattern=r"^[A-Z]{3}$")


class ConsultationCasePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_type: ConsultationSourceType
    chart_type: ConsultationChartType
    user: UserConsultationDetails
    consultation: ConsultationDetails
    astrology_snapshot: AstrologySnapshot
    idempotency_key: Optional[str] = Field(default=None, max_length=120)

    @field_validator("astrology_snapshot")
    @classmethod
    def chart_types_must_match(cls, value: AstrologySnapshot, info: Any) -> AstrologySnapshot:
        chart_type = info.data.get("chart_type")
        if chart_type and value.chart_type != chart_type:
            raise ValueError("astrology_snapshot.chart_type must match chart_type")
        return value


class ConsultationCase(ConsultationCasePayload):
    case_id: str
    user_id: Optional[str] = None
    case_status: ConsultationStatus
    booking_status: Optional[str] = None
    admin_notes: Optional[str] = None
    assigned_astrologer: Optional[str] = None
    meeting_link: Optional[str] = None
    scheduled_at: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConsultationCaseAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_status: Optional[ConsultationStatus] = None
    admin_notes: Optional[str] = Field(default=None, max_length=5000)
    assigned_astrologer: Optional[str] = Field(default=None, max_length=120)
    meeting_link: Optional[str] = Field(default=None, max_length=500)
    scheduled_at: Optional[str] = Field(default=None, max_length=120)

    @field_validator("case_status", mode="before")
    @classmethod
    def normalize_case_status(cls, value: Any) -> Any:
        if value is None:
            return None
        normalized = normalize_consultation_status(value)
        if normalized in CONSULTATION_STATUSES:
            return normalized
        return value
