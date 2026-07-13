from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import Field, field_validator

from app.config import get_settings
from app.core.rate_limiter import booking_limiter
from app.core.consultation_lifecycle import ACTIVE_CONSULTATION_STATUSES, TERMINAL_CONSULTATION_STATUSES
from app.storage.database import (
    get_chart,
    get_consultant_booking,
    list_consultant_messages,
    save_consultant_booking,
    save_consultant_message,
)
from app.dependencies import get_current_user, AuthState
from app.schemas.common import ID_RE, PHONE_RE, StrictRequestModel, parse_iso_datetime

router = APIRouter()

CONSULTANTS = [
    {
        "id": "rupesh-kumar",
        "name": "Rupesh Kumar",
        "experience_years": 3,
        "email": "anitarupesiifl99@gmail.com",
        "specialties": ["Prashna Kundli", "Lagna Kundli", "One-to-one consultation"],
    }
]


class BirthDetails(StrictRequestModel):
    name: str = Field(min_length=1, max_length=80)
    gender: str = Field(default="", pattern="^(|male|female|other)$")
    birth_datetime_local: str = Field(default="", max_length=32)
    place_name: str = Field(default="", max_length=160)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @field_validator("birth_datetime_local")
    @classmethod
    def validate_birth_datetime(cls, value: str) -> str:
        if value:
            parse_iso_datetime(value, "birth_datetime_local")
        return value


class BookingRequest(StrictRequestModel):
    consultant_id: str = Field(min_length=1, max_length=80)
    consultation_type: str = Field(pattern="^(same_prashna|kundali|lagna)$")
    client_name: str = Field(min_length=1, max_length=80)
    client_email: str = Field(min_length=5, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    client_phone: str = Field(min_length=6, max_length=24, pattern=PHONE_RE)
    query_text: str = Field(min_length=3, max_length=2000)
    chart_id: str = Field(default="", max_length=128, pattern=r"^$|[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    chart: Optional[dict] = None
    birth_details: Optional[BirthDetails] = None


class MessageRequest(StrictRequestModel):
    sender_role: str = Field(pattern="^(user|astrologer)$")
    sender_name: str = Field(min_length=1, max_length=80)
    message_text: str = Field(min_length=1, max_length=3000)


def can_access_booking(auth: AuthState, booking: dict) -> bool:
    return auth.is_admin or booking.get("user_id") == auth.user_id or booking.get("client_email") == auth.email


def has_active_booking_conflict(auth: AuthState, consultant_id: str) -> bool:
    if not auth.client:
        return False
    try:
        res = (
            auth.client.table("consultant_bookings")
            .select("id, status")
            .eq("user_id", auth.user_id)
            .eq("consultant_id", consultant_id)
            .in_("status", sorted(ACTIVE_CONSULTATION_STATUSES | {"pending", "accepted", "scheduled", "in_progress"}))
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


@router.get("/consultants")
def list_consultants() -> dict:
    return {"consultants": CONSULTANTS}


@router.post("/consultants/bookings", dependencies=[Depends(booking_limiter)])
def create_booking(payload: BookingRequest, auth: AuthState = Depends(get_current_user)) -> dict:
    consultant = consultant_by_id(payload.consultant_id)
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found.")
    if payload.client_email.lower() != auth.email.lower():
        raise HTTPException(status_code=400, detail="Booking email must match the signed-in user.")
    if has_active_booking_conflict(auth, payload.consultant_id):
        raise HTTPException(status_code=409, detail="You already have an active booking with this consultant.")

    chart = payload.chart
    chart_id = payload.chart_id
    if chart_id and not chart:
        chart = get_chart(auth.client, chart_id)
        if not chart:
            raise HTTPException(status_code=404, detail="Chart not found for consultation.")

    if payload.consultation_type in {"same_prashna", "lagna"} and not chart:
        raise HTTPException(status_code=400, detail="This consultation type requires the current chart data.")
    if payload.consultation_type == "kundali" and not payload.birth_details:
        raise HTTPException(status_code=400, detail="Kundali consultation requires birth details.")

    booking = {
        "consultant_id": consultant["id"],
        "consultant_name": consultant["name"],
        "consultation_type": payload.consultation_type,
        "client_name": payload.client_name,
        "client_email": payload.client_email,
        "client_phone": payload.client_phone,
        "query_text": payload.query_text,
        "chart_id": chart_id or chart.get("id", "") if chart else "",
        "chart_type": chart.get("meta", {}).get("chart_type", "") if chart else "",
        "chart": chart,
        "birth_details": payload.birth_details.model_dump() if payload.birth_details else None,
        "status": "requested",
    }
    booking_id = save_consultant_booking(auth.client, booking, auth.user_id)
    booking["id"] = booking_id

    initial_message_id = save_consultant_message(
        auth.client,
        {
            "booking_id": booking_id,
            "sender_role": "user",
            "sender_name": payload.client_name,
            "message_text": payload.query_text,
        },
        auth.user_id
    )

    return {
        "booking": {**booking, "id": booking_id},
        "messages": list_consultant_messages(auth.client, booking_id),
    }


@router.get("/consultants/bookings/{booking_id}")
def read_booking(booking_id: Annotated[str, Path(pattern=ID_RE)], auth: AuthState = Depends(get_current_user)) -> dict:
    booking = get_consultant_booking(auth.client, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if not can_access_booking(auth, booking):
        raise HTTPException(status_code=403, detail="Not allowed to read this booking.")
    return {"booking": booking, "messages": list_consultant_messages(auth.client, booking_id)}


@router.post("/consultants/bookings/{booking_id}/messages")
def create_message(
    booking_id: Annotated[str, Path(pattern=ID_RE)],
    payload: MessageRequest,
    auth: AuthState = Depends(get_current_user),
    _ = Depends(booking_limiter),
) -> dict:
    booking = get_consultant_booking(auth.client, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if not can_access_booking(auth, booking):
        raise HTTPException(status_code=403, detail="Not allowed to message this booking.")
    if str(booking.get("status") or "").lower() in TERMINAL_CONSULTATION_STATUSES:
        raise HTTPException(status_code=400, detail="This booking is closed for new messages.")
    if payload.sender_role != "user" and not auth.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can send astrologer messages from this endpoint.")
    message = {
        "booking_id": booking_id,
        "sender_role": payload.sender_role if auth.is_admin else "user",
        "sender_name": payload.sender_name,
        "message_text": payload.message_text,
    }
    message_id = save_consultant_message(auth.client, message, auth.user_id)
    message["id"] = message_id
    return {"message": message, "messages": list_consultant_messages(auth.client, booking_id)}


def consultant_by_id(consultant_id: str) -> Optional[dict]:
    return next((item for item in CONSULTANTS if item["id"] == consultant_id), None)


def supabase_booking_payload(booking: dict) -> dict:
    return {
        "id": booking["id"],
        "consultant_id": booking["consultant_id"],
        "consultant_name": booking["consultant_name"],
        "consultation_type": booking["consultation_type"],
        "client_name": booking["client_name"],
        "client_email": booking["client_email"],
        "client_phone": booking["client_phone"],
        "query_text": booking["query_text"],
        "chart_id": booking.get("chart_id", ""),
        "chart_type": booking.get("chart_type", ""),
        "chart_json": booking.get("chart"),
        "birth_details_json": booking.get("birth_details"),
        "status": booking.get("status", "requested"),
    }


def sync_supabase(table: str, payload: dict) -> dict:
    settings = get_settings()
    url = settings.supabase_url
    key = settings.supabase_service_role_key
    if not url or not key:
        return {"enabled": False, "reason": "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to sync."}
    request = urllib.request.Request(
        f"{url}/rest/v1/{table}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return {"enabled": True, "status": response.status}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"enabled": True, "error": f"HTTP {exc.code}: {body[:240]}"}
    except Exception as exc:
        return {"enabled": True, "error": str(exc)}
