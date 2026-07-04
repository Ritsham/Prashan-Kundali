from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import json
import os
import httpx

from app.storage.consultation_db import (
    get_queue_status,
    create_consultation,
    get_consultation_queue,
    answer_consultation,
    decline_consultation
)
from app.api.prashna import LocationInput
from app.dependencies import get_current_user, AuthState
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
