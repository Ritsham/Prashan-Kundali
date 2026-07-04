from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import json
import os
import httpx

from app.storage.consultation_db import (
    get_founder_consultant,
    get_public_consultation_queue_status,
    create_consultation_request,
    get_consultation_request,
    list_consultation_requests,
    update_consultation_request,
    get_queue_status,
    create_consultation,
    get_consultation_queue,
    answer_consultation,
    decline_consultation
)
from app.api.prashna import LocationInput
from app.dependencies import get_current_user, AuthState, RequireRole
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.services.timezone_service import timezone_at

router = APIRouter()

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
    topic: str = Field(pattern="^(Career|Marriage|Business|Health|Prashna|Other)$")
    question: str = Field(min_length=3, max_length=2000)
    preferred_time: str = Field(default="", max_length=120)
    payment_status: str = Field(default="not_paid", max_length=40)

class AdminConsultationUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(pending|accepted|in_progress|completed|rejected|cancelled|waiting_queue)$")
    meeting_link: Optional[str] = Field(default=None, max_length=500)
    scheduled_at: Optional[str] = Field(default=None, max_length=120)
    admin_notes: Optional[str] = Field(default=None, max_length=3000)


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
    result = await create_consultation_request(payload.model_dump())
    return result


@router.get("/consultation/request/{request_id}")
async def read_consultation_request(request_id: str):
    request = await get_consultation_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Consultation request not found")
    return {"request": request}


@router.get("/admin/consultations/requests")
async def admin_list_consultation_requests(status: Optional[str] = None, auth: AuthState = Depends(RequireRole("admin"))):
    return {"requests": await list_consultation_requests(status)}


@router.post("/admin/consultations/requests/{request_id}")
async def admin_update_consultation_request(
    request_id: str,
    payload: AdminConsultationUpdate,
    auth: AuthState = Depends(RequireRole("admin")),
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
