from fastapi import APIRouter, HTTPException, Depends, Path, Query
from pydantic import Field, field_validator
from typing import Annotated, Optional
import json
import re
import httpx
import logging

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
from app.dependencies import get_current_user, get_optional_current_user, AuthState, RequireAdmin
from app.core.rate_limiter import booking_limiter, llm_limiter, public_limiter
from app.core.consultation_lifecycle import normalize_consultation_status
from app.schemas.consultation_case import (
    AstrologySnapshot,
    ConsultationCaseAdminUpdate,
    ConsultationCasePayload,
)
from app.schemas.common import ID_RE, LocationInput, PHONE_RE, StrictRequestModel, parse_iso_datetime
from app.storage.payments_db import is_verified_payment, update_payment_status
from app.storage.audit_db import record_admin_audit
from app.storage.database import get_service_client
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.config import get_settings
from app.services.astrology_gateway import AstrologyEngineHTTPError, calculate_chart
from app.services.timezone_service import timezone_at

router = APIRouter()
logger = logging.getLogger(__name__)


COORD_RE = re.compile(r"Lat:\s*(-?\d+(?:\.\d+)?),?\s*Lon:\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)


def _public_case(case: dict) -> dict:
    clean = dict(case)
    for key in ("admin_notes", "assigned_astrologer"):
        clean.pop(key, None)
    return clean


def _is_admin(auth: AuthState) -> bool:
    return auth.is_admin


def _can_read_own_case(auth: AuthState, case: dict) -> bool:
    user = case.get("user") or {}
    return (
        case.get("user_id") == auth.user_id
        or user.get("email") == auth.email
        or case.get("email") == auth.email
        or case.get("assigned_astrologer") == auth.user_id
        or _is_admin(auth)
    )


def _requires_verified_payment() -> bool:
    settings = get_settings()
    if settings.is_production:
        return True
    return settings.require_verified_payment


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
        logger.warning("consultation_case_payload_rebuild_failed")
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
        logger.warning("consultation_case_snapshot_repair_failed status=%s", exc.status_code)
        return case
    except Exception as exc:
        logger.warning("consultation_case_snapshot_repair_failed")
        return case

    snapshot = enriched.astrology_snapshot.model_dump(mode="json", exclude_none=True)
    if not _snapshot_has_chart(snapshot):
        return case

    try:
        result = await update_consultation_case(case["case_id"], {"astrology_snapshot": snapshot})
        return result.get("case") or case
    except Exception as exc:
        logger.warning("consultation_case_snapshot_repair_persist_failed")
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

    try:
        result = await calculate_chart(chart_req_data, timeout=30.0)
    except AstrologyEngineHTTPError as exc:
        raise HTTPException(status_code=422, detail=f"Failed to calculate consultation chart snapshot: {exc.detail}") from exc
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

class ConsultationBookRequest(StrictRequestModel):
    question: str = Field(min_length=3, max_length=200)
    name: str = Field(min_length=1, max_length=80)
    gender: str = Field(pattern="^(male|female|other)$")
    birth_datetime_local: str = Field(min_length=16, max_length=32)
    location: LocationInput
    payment_ref: str = Field(min_length=1, max_length=120, pattern=ID_RE)
    whatsapp_no: str = Field(min_length=6, max_length=24, pattern=PHONE_RE, description="WhatsApp number with country code")

    @field_validator("birth_datetime_local")
    @classmethod
    def validate_birth_datetime(cls, value: str) -> str:
        parse_iso_datetime(value, "birth_datetime_local")
        return value


class AnswerRequest(StrictRequestModel):
    answer: str = Field(min_length=5, max_length=2000)


class PublicConsultationRequest(StrictRequestModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=6, max_length=24, pattern=PHONE_RE)
    email: str = Field(min_length=5, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    date_of_birth: str = Field(min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_of_birth: str = Field(min_length=5, max_length=8, pattern=r"^\d{2}:\d{2}(:\d{2})?$")
    place_of_birth: str = Field(min_length=1, max_length=160)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    topic: str = Field(pattern="^(Career|Marriage|Business|Health|Prashna|Birth Chart|Matchmaking|Other)$")
    question: str = Field(min_length=3, max_length=2000)
    preferred_date: Optional[str] = Field(default=None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    preferred_time: str = Field(default="", max_length=8, pattern=r"^$|^\d{2}:\d{2}(:\d{2})?$")
    payment_status: str = Field(default="not_paid", pattern=r"^(not_paid|pending|created)$")
    quoted_price: Optional[float] = Field(default=None, gt=0, le=100000)
    currency: str = Field(default="INR", max_length=3, pattern=r"^[A-Z]{3}$")
    chart_snapshot: Optional[dict] = None


class CancelConsultationRequest(StrictRequestModel):
    requester_email: Optional[str] = Field(default=None, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AdminConsultationUpdate(StrictRequestModel):
    status: Optional[str] = Field(default=None, pattern="^(requested|pending_payment|confirmed|active|completed|cancelled|refunded|pending|reviewed|accepted|scheduled|in_progress|rejected|waiting_queue)$")
    meeting_link: Optional[str] = Field(default=None, max_length=500)
    scheduled_at: Optional[str] = Field(default=None, max_length=120)
    admin_notes: Optional[str] = Field(default=None, max_length=3000)


@router.post("/consultation-cases", dependencies=[Depends(booking_limiter)])
async def create_case(
    payload: ConsultationCasePayload,
    auth: Optional[AuthState] = Depends(get_optional_current_user),
):
    try:
        payload = await _enrich_case_snapshot(payload)
        db = auth.client if auth else get_service_client()
        if not db:
            raise HTTPException(status_code=500, detail="Consultation storage is not configured")
        result = await create_consultation_case(payload, user_id=auth.user_id if auth else None, db_client=db)
        if result.get("case"):
            result["case"] = _public_case(result["case"])
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create consultation case") from exc


@router.get("/consultation-cases/{case_id}")
async def read_case(case_id: Annotated[str, Path(pattern=ID_RE)], auth: AuthState = Depends(get_current_user)):
    case = await get_consultation_case(case_id, get_service_client())
    if not case:
        raise HTTPException(status_code=404, detail="Consultation case not found")
    if not _can_read_own_case(auth, case):
        raise HTTPException(status_code=403, detail="Not allowed to read this consultation case")
    return {"case": _public_case(case)}


@router.get("/admin/consultation-cases")
async def admin_list_cases(
    status: Optional[str] = Query(default=None, max_length=40),
    source_type: Optional[str] = None,
    chart_type: Optional[str] = None,
    date: Optional[str] = None,
    user_name: Optional[str] = None,
    case_id: Optional[str] = Query(default=None, pattern=ID_RE),
    auth: AuthState = Depends(RequireAdmin()),
):
    return {
        "cases": await list_consultation_cases(
            status=normalize_consultation_status(status) if status else None,
            source_type=source_type,
            chart_type=chart_type,
            user_name=user_name,
            case_id=case_id,
            created_date=date,
            db_client=auth.client,
        )
    }


@router.get("/admin/consultation-cases/{case_id}")
async def admin_read_case(case_id: Annotated[str, Path(pattern=ID_RE)], auth: AuthState = Depends(RequireAdmin())):
    case = await get_consultation_case(case_id, auth.client)
    if not case:
        raise HTTPException(status_code=404, detail="Consultation case not found")
    case = await _ensure_case_snapshot(case)
    return {"case": case}


@router.patch("/admin/consultation-cases/{case_id}")
async def admin_patch_case(
    case_id: Annotated[str, Path(pattern=ID_RE)],
    payload: ConsultationCaseAdminUpdate,
    auth: AuthState = Depends(RequireAdmin()),
):
    before = await get_consultation_case(case_id, auth.client)
    try:
        result = await update_consultation_case(case_id, payload.model_dump(), auth.client)
        if not result["case"]:
            raise HTTPException(status_code=404, detail="Consultation case not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_admin_audit(
        actor_user_id=auth.user_id,
        entity_type="consultation_case",
        entity_id=case_id,
        action="update",
        before_json=before,
        after_json=result["case"],
    )
    return result


@router.get("/consultation/profile", dependencies=[Depends(public_limiter)])
async def consultation_profile():
    return {
        "consultant": await get_founder_consultant(),
        "positioning": "Consultations are currently available with our founder astrologer. More verified astrologers may be added later after quality review.",
    }


@router.get("/consultation/request-status", dependencies=[Depends(public_limiter)])
async def consultation_request_status():
    return await get_public_consultation_queue_status(get_service_client())


@router.post("/consultation/request", dependencies=[Depends(booking_limiter)])
async def request_consultation(
    payload: PublicConsultationRequest,
    auth: Optional[AuthState] = Depends(get_optional_current_user),
):
    try:
        db = get_service_client()
        if not db:
            raise HTTPException(status_code=500, detail="Supabase service role client is not configured")

        data = payload.model_dump()

        # If frontend provided a snapshot directly, prefer that
        if payload.chart_snapshot:
            data["astrological_snapshot"] = json.dumps(payload.chart_snapshot)
        
        # Remove chart_snapshot from data before sending to DB
        data.pop("chart_snapshot", None)

                
        result = await create_consultation_request(
            data,
            user_id=auth.user_id if auth else None,
            db_client=db,
        )
        request_id = (result.get("request") or {}).get("id")
        should_enrich_snapshot = (
            request_id
            and not payload.chart_snapshot
            and payload.latitude is not None
            and payload.longitude is not None
            and payload.date_of_birth
            and payload.time_of_birth
        )
        if should_enrich_snapshot:
            try:
                from app.worker import enrich_consultation_request_snapshot_task
                enrich_consultation_request_snapshot_task.delay(request_id, payload.model_dump(mode="json"))
                result["snapshot_status"] = "queued"
            except Exception as exc:
                logger.warning("public_consultation_snapshot_queue_failed: %s", exc)
                result["snapshot_status"] = "unavailable"
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create consultation request") from e


@router.get("/consultation/request/{request_id}")
async def read_consultation_request(request_id: Annotated[str, Path(pattern=ID_RE)], auth: AuthState = Depends(get_current_user)):
    request = await get_consultation_request(request_id, get_service_client())
    if not request:
        raise HTTPException(status_code=404, detail="Consultation request not found")
    if not _can_read_own_case(auth, request):
        raise HTTPException(status_code=403, detail="Not allowed to read this consultation request")
    return {"request": request}


@router.post("/consultation/request/{request_id}/cancel", dependencies=[Depends(booking_limiter)])
async def cancel_consultation_request(
    request_id: Annotated[str, Path(pattern=ID_RE)],
    payload: CancelConsultationRequest,
    auth: Optional[AuthState] = Depends(get_optional_current_user),
):
    db = get_service_client()
    if not db:
        raise HTTPException(status_code=500, detail="Supabase service role client is not configured")

    request = await get_consultation_request(request_id, db)
    if not request:
        raise HTTPException(status_code=404, detail="Consultation request not found")

    request_email = str(request.get("email") or request.get("user", {}).get("email") or "").strip().lower()
    requester_email = str(payload.requester_email or "").strip().lower()
    owns_request = bool(
        (auth and _can_read_own_case(auth, request))
        or (request_email and requester_email and request_email == requester_email)
    )
    if not owns_request:
        raise HTTPException(status_code=403, detail="Not allowed to cancel this consultation request")

    status = normalize_consultation_status(request.get("status"))
    payment_status = str(request.get("payment_status") or request.get("consultation", {}).get("payment_status") or "").lower()
    if payment_status == "paid" or status in {"confirmed", "active", "completed", "refunded"}:
        raise HTTPException(status_code=400, detail="Paid or active consultation requests cannot be cancelled from this page")

    result = await update_consultation_request(
        request_id,
        {"status": "cancelled", "payment_status": "cancelled"},
        db,
    )
    return result


@router.get("/admin/consultations/requests")
async def admin_list_consultation_requests(
    status: Optional[str] = Query(default=None, max_length=40),
    auth: AuthState = Depends(RequireAdmin()),
):
    return {"requests": await list_consultation_requests(normalize_consultation_status(status) if status else None, auth.client)}


@router.put("/admin/consultations/requests/{request_id}")
@router.post("/admin/consultations/requests/{request_id}")
async def admin_update_consultation_request(
    request_id: Annotated[str, Path(pattern=ID_RE)],
    payload: AdminConsultationUpdate,
    auth: AuthState = Depends(RequireAdmin()),
):
    before = await get_consultation_request(request_id, auth.client)
    try:
        update_payload = payload.model_dump()
        if update_payload.get("status"):
            update_payload["status"] = normalize_consultation_status(update_payload["status"])
        result = await update_consultation_request(request_id, update_payload, auth.client)
        if not result["request"]:
            raise HTTPException(status_code=404, detail="Consultation request not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_admin_audit(
        actor_user_id=auth.user_id,
        entity_type="consultation_request",
        entity_id=request_id,
        action="update",
        before_json=before,
        after_json=result["request"],
    )
    return result

@router.get("/consultation/status", dependencies=[Depends(public_limiter)])
async def check_status():
    status = await get_queue_status()
    can_book = status["current_queue_size"] < status["max_capacity"]
    return {
        **status,
        "can_book": can_book
    }

@router.post("/consultation/book", dependencies=[Depends(booking_limiter), Depends(llm_limiter)])
async def book_consultation(payload: ConsultationBookRequest, auth: AuthState = Depends(get_current_user)):
    if _requires_verified_payment() and not is_verified_payment(
        db=auth.client,
        provider="razorpay",
        provider_ref=payload.payment_ref,
        user_id=auth.user_id,
    ):
        raise HTTPException(status_code=402, detail="A verified Razorpay payment is required before booking.")

    # 1. Check Capacity
    status = await get_queue_status()
    if status["current_queue_size"] >= status["max_capacity"]:
        raise HTTPException(status_code=429, detail="Consultant queue is currently full.")

    # 2. Create consultation record immediately; chart snapshot is enriched in the background.
    try:
        birth_date = payload.birth_datetime_local.split('T')[0]
        birth_time = payload.birth_datetime_local.split('T')[1]
        pending_snapshot = {
            "status": "queued",
            "message": "Astrological snapshot is being generated.",
            "chart_type": "prashna",
        }
        
        result = await create_consultation(
            user_id=auth.user_id,
            user_name=payload.name,
            user_email=auth.email,
            question_text=payload.question,
            astrological_snapshot=json.dumps(pending_snapshot),
            payment_ref=payload.payment_ref,
            whatsapp_no=payload.whatsapp_no,
            gender=payload.gender,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_place=payload.location.place_name
        )
        if _requires_verified_payment():
            update_payment_status(
                provider="razorpay",
                provider_ref=payload.payment_ref,
                status="paid",
                booking_id=result.get("id"),
            )
        try:
            from app.worker import enrich_paid_consultation_snapshot_task
            enrich_paid_consultation_snapshot_task.delay(result["id"], payload.model_dump(mode="json"))
            result["snapshot_status"] = "queued"
        except Exception as exc:
            logger.warning("paid_consultation_snapshot_queue_failed: %s", exc)
            result["snapshot_status"] = "unavailable"
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to book consultation") from exc

@router.get("/consultation/queue")
async def get_queue(auth: AuthState = Depends(RequireAdmin())):
    queue = await get_consultation_queue()
    for q in queue:
        raw_snapshot = q.get("astrological_snapshot")
        if isinstance(raw_snapshot, str) and raw_snapshot.strip():
            try:
                q["astrological_snapshot"] = json.loads(raw_snapshot)
            except json.JSONDecodeError:
                q["astrological_snapshot"] = {"status": "unavailable", "raw": raw_snapshot}
        elif not raw_snapshot:
            q["astrological_snapshot"] = {"status": "queued", "message": "Astrological snapshot is being generated."}
    return {"queue": queue}

@router.post("/consultation/{consultation_id}/answer")
async def answer_question(
    consultation_id: Annotated[str, Path(pattern=ID_RE)],
    payload: AnswerRequest,
    auth: AuthState = Depends(RequireAdmin()),
):
    success = await answer_consultation(consultation_id, payload.answer)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to answer consultation. Might not exist or is already answered.")
    record_admin_audit(
        actor_user_id=auth.user_id,
        entity_type="paid_consultation",
        entity_id=consultation_id,
        action="answer",
        after_json={"answered": True},
    )
    return {"status": "success"}

@router.post("/consultation/{consultation_id}/decline")
async def decline_question(
    consultation_id: Annotated[str, Path(pattern=ID_RE)],
    auth: AuthState = Depends(RequireAdmin()),
):
    success = await decline_consultation(consultation_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to decline consultation.")
    record_admin_audit(
        actor_user_id=auth.user_id,
        entity_type="paid_consultation",
        entity_id=consultation_id,
        action="decline",
        after_json={"declined": True},
    )
    return {"status": "success"}
