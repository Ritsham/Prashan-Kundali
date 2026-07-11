from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import json
import os
import re
import httpx

from app.storage.consultation_db import (
    get_founder_consultant,
    get_public_consultation_queue_status,
    create_consultation_request,
    get_consultation_request,
    list_consultation_requests,
    update_consultation_request,
    create_consultation_case,
    get_consultation_case,
    list_consultation_cases,
    update_consultation_case,
    get_queue_status,
    create_consultation,
    get_consultation_queue,
    answer_consultation,
    decline_consultation
)
from app.api.prashna import LocationInput
from app.dependencies import get_current_user, get_optional_current_user, AuthState, RequireRole
from app.schemas.consultation_case import (
    AstrologySnapshot,
    ConsultationCaseAdminUpdate,
    ConsultationCasePayload,
)
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.services.timezone_service import timezone_at

router = APIRouter()


COORD_RE = re.compile(r"Lat:\s*(-?\d+(?:\.\d+)?),?\s*Lon:\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)


def _public_case(case: dict) -> dict:
    clean = dict(case)
    for key in ("admin_notes", "assigned_astrologer"):
        clean.pop(key, None)
    return clean


def _snapshot_has_chart(snapshot: object) -> bool:
    if not isinstance(snapshot, dict):
        return False
    chart = snapshot.get("chart")
    return bool(
        isinstance(chart, dict)
        and (
            chart.get("signs")
            or chart.get("divisional_charts")
            or chart.get("planets")
            or chart.get("dashas")
        )
    )


def _coords_from_case(case: dict) -> tuple[Optional[float], Optional[float]]:
    user = case.get("user") or {}
    latitude = user.get("latitude") if user.get("latitude") is not None else case.get("latitude")
    longitude = user.get("longitude") if user.get("longitude") is not None else case.get("longitude")
    if latitude is not None and longitude is not None:
        try:
            return float(latitude), float(longitude)
        except (TypeError, ValueError):
            pass

    place = user.get("place") or case.get("place_of_birth") or ""
    match = COORD_RE.search(place)
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def _payload_from_existing_case(case: dict) -> Optional[ConsultationCasePayload]:
    user = case.get("user") or {}
    consultation = case.get("consultation") or {}
    latitude, longitude = _coords_from_case(case)
    place = user.get("place") or case.get("place_of_birth") or ""
    chart_type = case.get("chart_type") or ("prashna" if case.get("topic") == "Prashna" else "lagna")
    source_type = case.get("source_type") or ("prashna" if chart_type == "prashna" else "direct_consultation")

    payload_data = {
        "source_type": source_type,
        "chart_type": chart_type,
        "user": {
            "full_name": user.get("full_name") or case.get("name") or "Consultation Case",
            "email": user.get("email") or case.get("email") or "unknown@example.com",
            "mobile_number": user.get("mobile_number") or case.get("phone") or "0000000000",
            "gender": user.get("gender") or case.get("gender"),
            "date_of_birth": user.get("date_of_birth") or case.get("date_of_birth"),
            "time_of_birth": user.get("time_of_birth") or case.get("time_of_birth"),
            "place": place,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": user.get("timezone") or case.get("timezone"),
        },
        "consultation": {
            "question": consultation.get("question") or case.get("question") or "Consultation question",
            "additional_message": consultation.get("additional_message") or case.get("additional_message"),
            "preferred_date": consultation.get("preferred_date") or case.get("preferred_date"),
            "preferred_time": consultation.get("preferred_time") or case.get("preferred_time"),
            "consultation_mode": consultation.get("consultation_mode") or case.get("consultation_mode"),
            "payment_status": consultation.get("payment_status") or case.get("payment_status"),
        },
        "astrology_snapshot": {
            "chart_type": chart_type,
            "chart": None,
        },
    }
    try:
        return ConsultationCasePayload.model_validate(payload_data)
    except Exception as exc:
        print(f"Warning: could not build consultation case payload for snapshot repair: {exc}")
        return None


async def _ensure_case_snapshot(case: dict) -> dict:
    if case.get("source_type") == "matchmaking" or case.get("chart_type") == "matchmaking":
        return case
    if _snapshot_has_chart(case.get("astrology_snapshot")):
        return case

    payload = _payload_from_existing_case(case)
    if not payload:
        return case

    try:
        enriched = await _enrich_case_snapshot(payload)
    except HTTPException as exc:
        print(f"Warning: consultation case snapshot repair failed: {exc.detail}")
        return case
    except Exception as exc:
        print(f"Warning: consultation case snapshot repair failed: {exc}")
        return case

    snapshot = enriched.astrology_snapshot.model_dump(mode="json", exclude_none=True)
    if not _snapshot_has_chart(snapshot):
        return case

    try:
        result = await update_consultation_case(case["case_id"], {"astrology_snapshot": snapshot})
        return result.get("case") or case
    except Exception as exc:
        print(f"Warning: consultation case snapshot repair calculated but could not be persisted: {exc}")
        repaired = dict(case)
        repaired["astrology_snapshot"] = snapshot
        repaired["astrological_snapshot"] = snapshot
        repaired["chart_snapshot"] = snapshot
        return repaired


async def _enrich_case_snapshot(payload: ConsultationCasePayload) -> ConsultationCasePayload:
    snapshot = payload.astrology_snapshot
    if snapshot.chart:
        return payload

    user = payload.user
    if user.latitude is None or user.longitude is None or not user.place:
        return payload

    astrology_url = os.getenv("ASTROLOGY_ENGINE_URL", "http://localhost:8001")
    chart_req_data = {
        "chart_type": payload.chart_type.value,
        "name": user.full_name,
        "question": payload.consultation.question,
        "gender": user.gender or "other",
        "location": {
            "latitude": user.latitude,
            "longitude": user.longitude,
            "place_name": user.place,
        },
    }

    if payload.chart_type.value == "lagna":
        if not user.date_of_birth or not user.time_of_birth:
            return payload
        chart_req_data["birth_datetime_local"] = f"{user.date_of_birth}T{user.time_of_birth}"
    else:
        if user.date_of_birth and user.time_of_birth:
            try:
                tz_name = user.timezone or timezone_at(user.latitude, user.longitude)
                local_dt = datetime.fromisoformat(f"{user.date_of_birth}T{user.time_of_birth}")
                if local_dt.tzinfo is None:
                    local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_name))
                chart_req_data["asked_at_utc"] = local_dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{astrology_url}/calculate", json=chart_req_data, timeout=30.0)

    if resp.status_code != 200:
        raise HTTPException(status_code=422, detail=f"Failed to calculate consultation chart snapshot: {resp.text}")

    result = resp.json()
    chart = result.get("chart") or {}
    interpretation = result.get("interpretation") or chart.get("interpretation")
    enriched_snapshot = AstrologySnapshot.model_validate({
        "chart_type": payload.chart_type.value,
        "chart": chart,
        "interpretation": interpretation,
        "divisional_charts": chart.get("divisional_charts"),
        "planetary_positions": chart.get("planets"),
        "house_positions": chart.get("houses"),
        "aspects": chart.get("aspects"),
        "yogas": chart.get("yogas"),
        "dashas": chart.get("dashas"),
        "kp_system": chart.get("kp_system"),
        "calculation_metadata": chart.get("meta"),
        "question_context": chart.get("question"),
        "source_result": result,
        "additional_calculations": {"transit": chart.get("transit")},
    })
    return payload.model_copy(update={"astrology_snapshot": enriched_snapshot})

class ConsultationBookRequest(BaseModel):
    question: str = Field(min_length=3, max_length=200)
    name: str = Field(min_length=1, max_length=80)
    gender: str = Field(pattern="^(male|female|other)$")
    birth_datetime_local: str = Field(min_length=16, max_length=32)
    location: LocationInput
    payment_ref: str = Field(min_length=1)
    whatsapp_no: str = Field(min_length=10, max_length=15, description="WhatsApp number with country code")

class AnswerRequest(BaseModel):
    answer: str = Field(min_length=5, max_length=2000)

class PublicConsultationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=6, max_length=24)
    email: str = Field(min_length=5, max_length=160)
    date_of_birth: str = Field(min_length=4, max_length=20)
    time_of_birth: str = Field(min_length=2, max_length=20)
    place_of_birth: str = Field(min_length=1, max_length=160)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    topic: str = Field(pattern="^(Career|Marriage|Business|Health|Prashna|Other)$")
    question: str = Field(min_length=3, max_length=2000)
    preferred_time: str = Field(default="", max_length=120)
    payment_status: str = Field(default="not_paid", max_length=40)
    chart_snapshot: Optional[dict] = None

class AdminConsultationUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(pending|reviewed|accepted|scheduled|in_progress|completed|rejected|cancelled|waiting_queue)$")
    meeting_link: Optional[str] = Field(default=None, max_length=500)
    scheduled_at: Optional[str] = Field(default=None, max_length=120)
    admin_notes: Optional[str] = Field(default=None, max_length=3000)


@router.post("/consultation-cases")
async def create_case(
    payload: ConsultationCasePayload,
    auth: Optional[AuthState] = Depends(get_optional_current_user),
):
    try:
        payload = await _enrich_case_snapshot(payload)
        result = await create_consultation_case(payload, user_id=auth.user_id if auth else None)
        if result.get("case"):
            result["case"] = _public_case(result["case"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/consultation-cases/{case_id}")
async def read_case(case_id: str):
    case = await get_consultation_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Consultation case not found")
    return {"case": _public_case(case)}


@router.get("/admin/consultation-cases")
async def admin_list_cases(
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    chart_type: Optional[str] = None,
    date: Optional[str] = None,
    user_name: Optional[str] = None,
    case_id: Optional[str] = None,
    auth: AuthState = Depends(RequireRole("admin")),
):
    return {
        "cases": await list_consultation_cases(
            status=status,
            source_type=source_type,
            chart_type=chart_type,
            user_name=user_name,
            case_id=case_id,
            created_date=date,
        )
    }


@router.get("/admin/consultation-cases/{case_id}")
async def admin_read_case(case_id: str, auth: AuthState = Depends(RequireRole("admin"))):
    case = await get_consultation_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Consultation case not found")
    case = await _ensure_case_snapshot(case)
    return {"case": case}


@router.patch("/admin/consultation-cases/{case_id}")
async def admin_patch_case(
    case_id: str,
    payload: ConsultationCaseAdminUpdate,
    auth: AuthState = Depends(RequireRole("admin")),
):
    result = await update_consultation_case(case_id, payload.model_dump())
    if not result["case"]:
        raise HTTPException(status_code=404, detail="Consultation case not found")
    return result


@router.get("/consultation/profile")
async def consultation_profile():
    return {
        "consultant": await get_founder_consultant(),
        "positioning": "Consultations are currently available with our founder astrologer. More verified astrologers may be added later after quality review.",
    }


@router.get("/consultation/request-status")
async def consultation_request_status():
    return await get_public_consultation_queue_status()


@router.post("/consultation/request")
async def request_consultation(payload: PublicConsultationRequest):
    try:
        data = payload.model_dump()
        
        # Pre-process chart if lat/lon are provided
        if payload.latitude and payload.longitude and payload.date_of_birth and payload.time_of_birth:
            try:
                # Convert DD/MM/YYYY or YYYY-MM-DD to ISO format for parsing
                # Actually, HTML5 date input sends YYYY-MM-DD, and time is HH:MM
                dt_str = f"{payload.date_of_birth}T{payload.time_of_birth}"
                local_dt = datetime.fromisoformat(dt_str)
                tz_name = timezone_at(payload.latitude, payload.longitude)
                
                if local_dt.tzinfo is None:
                    local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_name))
                birth_utc = local_dt.astimezone(timezone.utc)
                
                astrology_url = os.getenv("ASTROLOGY_ENGINE_URL", "http://localhost:8001")
                chart_type = "prashna" if payload.topic == "Prashna" else "lagna"
                
                chart_req_data = {
                    "chart_type": chart_type,
                    "name": payload.name,
                    "question": payload.question,
                    "location": {
                        "latitude": payload.latitude,
                        "longitude": payload.longitude,
                        "place_name": payload.place_of_birth
                    },
                    "asked_at_utc": birth_utc.isoformat()
                }
                
                async with httpx.AsyncClient() as client:
                    resp = await client.post(f"{astrology_url}/calculate", json=chart_req_data, timeout=30.0)
                    
                if resp.status_code == 200:
                    data["astrological_snapshot"] = json.dumps(resp.json()["chart"])
                else:
                    print(f"Warning: Chart generation returned {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"Warning: Could not fetch astrological snapshot for Free Lead: {e}")
                
        # If frontend provided a snapshot directly, prefer that
        if payload.chart_snapshot:
            data["astrological_snapshot"] = json.dumps(payload.chart_snapshot)
        
        # Remove chart_snapshot from data before sending to DB
        data.pop("chart_snapshot", None)

                
        result = await create_consultation_request(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consultation/request/{request_id}")
async def read_consultation_request(request_id: str):
    request = await get_consultation_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Consultation request not found")
    return {"request": request}


@router.get("/admin/consultations/requests")
async def admin_list_consultation_requests(status: Optional[str] = None):
    return {"requests": await list_consultation_requests(status)}


@router.put("/admin/consultations/requests/{request_id}")
@router.post("/admin/consultations/requests/{request_id}")
async def admin_update_consultation_request(
    request_id: str,
    payload: AdminConsultationUpdate
):
    result = await update_consultation_request(request_id, payload.model_dump())
    if not result["request"]:
        raise HTTPException(status_code=404, detail="Consultation request not found")
    return result

@router.get("/consultation/status")
async def check_status():
    status = await get_queue_status()
    can_book = status["current_queue_size"] < status["max_capacity"]
    return {
        **status,
        "can_book": can_book
    }

@router.post("/consultation/book")
async def book_consultation(payload: ConsultationBookRequest, auth: AuthState = Depends(get_current_user)):
    # 1. Check Capacity
    status = await get_queue_status()
    if status["current_queue_size"] >= status["max_capacity"]:
        raise HTTPException(status_code=429, detail="Consultant queue is currently full.")

    # 2. Pre-processing: Generate Astronomical Snapshot
    try:
        tz_name = timezone_at(payload.location.latitude, payload.location.longitude)
        local_dt = datetime.fromisoformat(payload.birth_datetime_local)
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_name))
        birth_utc = local_dt.astimezone(timezone.utc)
        
        astrology_url = os.getenv("ASTROLOGY_ENGINE_URL", "http://localhost:8001")
        
        payload_data = {
            "chart_type": "prashna",
            "name": payload.name,
            "question": payload.question,
            "location": {
                "latitude": payload.location.latitude,
                "longitude": payload.location.longitude,
                "place_name": payload.location.place_name
            },
            "asked_at_utc": birth_utc.isoformat()
        }
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{astrology_url}/calculate", json=payload_data, timeout=30.0)
            
        if resp.status_code != 200:
            raise HTTPException(status_code=422, detail="Failed to calculate astrological snapshot for consultation.")
            
        snapshot = resp.json()["chart"]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Chart calculation failed: {str(exc)}")

    # 3. Create consultation record
    try:
        birth_date = payload.birth_datetime_local.split('T')[0]
        birth_time = payload.birth_datetime_local.split('T')[1]
        
        result = await create_consultation(
            user_name=payload.name,
            user_email=auth.email,
            question_text=payload.question,
            astrological_snapshot=json.dumps(snapshot),
            payment_ref=payload.payment_ref,
            whatsapp_no=payload.whatsapp_no,
            gender=payload.gender,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_place=payload.location.place_name
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/consultation/queue")
async def get_queue():
    queue = await get_consultation_queue()
    for q in queue:
        q["astrological_snapshot"] = json.loads(q["astrological_snapshot"])
    return {"queue": queue}

@router.post("/consultation/{consultation_id}/answer")
async def answer_question(consultation_id: str, payload: AnswerRequest):
    success = await answer_consultation(consultation_id, payload.answer)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to answer consultation. Might not exist or is already answered.")
    return {"status": "success"}

@router.post("/consultation/{consultation_id}/decline")
async def decline_question(consultation_id: str):
    success = await decline_consultation(consultation_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to decline consultation.")
    return {"status": "success"}
