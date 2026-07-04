from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

import os
import httpx
from app.services.geocoding_service import geocode_place, reverse_geocode_place
from app.services.timezone_service import timezone_at
from app.storage.database import get_chart, save_prashna_chart, save_lagna_chart, sync_user
from app.dependencies import get_current_user, AuthState
from app.core.rate_limiter import RateLimiter

router = APIRouter()

# Rate limiters
prashna_rate_limiter = RateLimiter(requests=10, window=60) # 10 req / minute
lagna_rate_limiter = RateLimiter(requests=10, window=60)



class LocationInput(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    place_name: str = Field(min_length=1, max_length=160)


class PrashnaRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=3, max_length=1000)
    question_domain: str = Field(default="", max_length=40)
    question_subdomain: str = Field(default="", max_length=40)
    location: LocationInput
    asked_at_utc: Optional[str] = None


class LagnaRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    gender: str = Field(pattern="^(male|female|other)$")
    birth_datetime_local: str = Field(min_length=16, max_length=32)
    location: LocationInput


class UserSyncRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    name: str = Field(default="", max_length=120)


@router.post("/users/sync")
def sync_user_endpoint(payload: UserSyncRequest, auth: AuthState = Depends(get_current_user)) -> dict:
    try:
        sync_user(auth.client, auth.user_id, payload.email, payload.name)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User sync failed: {str(e)}")


@router.post("/prashna")
async def create_prashna(payload: PrashnaRequest, auth: AuthState = Depends(get_current_user), _ = Depends(prashna_rate_limiter)) -> dict:
    try:
        asked_at_utc = datetime.now(timezone.utc)
        if payload.asked_at_utc:
            try:
                asked_at_utc = datetime.fromisoformat(payload.asked_at_utc).astimezone(timezone.utc)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid asked_at_utc ISO datetime.") from exc
        
        try:
            astrology_url = os.getenv("ASTROLOGY_ENGINE_URL", "http://localhost:8001")
            
            payload_data = {
                "chart_type": "prashna",
                "name": payload.name,
                "question": payload.question,
                "question_domain": payload.question_domain,
                "question_subdomain": payload.question_subdomain,
                "location": {
                    "latitude": payload.location.latitude,
                    "longitude": payload.location.longitude,
                    "place_name": payload.location.place_name
                }
            }
            if payload.asked_at_utc:
                payload_data["asked_at_utc"] = asked_at_utc.isoformat()
                
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{astrology_url}/calculate", json=payload_data, timeout=30.0)
                
            if resp.status_code == 503:
                raise HTTPException(status_code=503, detail=resp.json().get("detail", "Calculation Dependency Error"))
            elif resp.status_code != 200:
                raise HTTPException(status_code=422, detail=resp.json().get("detail", "Failed to calculate chart"))
                
            result = resp.json()
            chart = result["chart"]
            interpretation = result.get("interpretation")

        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to connect to astrology engine: {str(exc)}") from exc
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        # Step 3: Save and Return immediately (so frontend feels instant)
        chart_id = save_prashna_chart(auth.client, chart, auth.user_id)
        chart["id"] = chart_id
        
        # Step 4: Queue LLM Generation in the background
        if interpretation:
            try:
                llm_url = os.getenv("LLM_ENGINE_URL", "http://localhost:8002")
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{llm_url}/generate",
                        json={
                            "chart_id": chart_id,
                            "chart": chart,
                            "interpretation": interpretation
                        },
                        timeout=5.0
                    )
            except Exception as e:
                # Log but do not fail the request if LLM queuing fails
                import logging
                logging.warning(f"Failed to queue LLM generation: {e}")
            
        return {"chart_id": chart_id, "chart": chart, "status": "processing"}
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(exc), "traceback": tb})


@router.post("/lagna")
async def create_lagna(payload: LagnaRequest, auth: AuthState = Depends(get_current_user), _ = Depends(lagna_rate_limiter)) -> dict:
    try:
        try:
            tz_name = timezone_at(payload.location.latitude, payload.location.longitude)
            local_dt = datetime.fromisoformat(payload.birth_datetime_local)
            astrology_url = os.getenv("ASTROLOGY_ENGINE_URL", "http://localhost:8001")
            
            payload_data = {
                "chart_type": "lagna",
                "name": payload.name,
                "gender": payload.gender,
                "birth_datetime_local": payload.birth_datetime_local,
                "location": {
                    "latitude": payload.location.latitude,
                    "longitude": payload.location.longitude,
                    "place_name": payload.location.place_name
                }
            }
                
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{astrology_url}/calculate", json=payload_data, timeout=30.0)
                
            if resp.status_code == 503:
                raise HTTPException(status_code=503, detail=resp.json().get("detail", "Calculation Dependency Error"))
            elif resp.status_code != 200:
                raise HTTPException(status_code=422, detail=resp.json().get("detail", "Failed to calculate chart"))
                
            chart = resp.json()["chart"]
            
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to connect to astrology engine: {str(exc)}") from exc
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        chart_id = save_lagna_chart(auth.client, chart, auth.user_id)
        chart["id"] = chart_id
        return {"chart_id": chart_id, "chart": chart}
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(exc), "traceback": tb})


@router.get("/charts/{chart_id}")
def read_chart(chart_id: str) -> dict:
    from app.storage.database import supabase
    chart = get_chart(supabase, chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    return {"chart_id": chart_id, "chart": chart}


@router.get("/geocode")
def geocode(query: str, limit: int = 6) -> dict:
    if len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Enter at least 2 characters.")
    return {"query": query, "results": geocode_place(query, limit=max(1, min(limit, 8)))}


@router.get("/reverse_geocode")
def reverse_geocode(lat: float, lon: float) -> dict:
    return reverse_geocode_place(lat, lon)

from fastapi.responses import StreamingResponse
import redis
import json
import os

@router.get("/stream/{chart_id}")
def stream_chart(chart_id: str):
    def event_stream():
        redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"stream:{chart_id}")
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                if data.get('done'):
                    yield "data: [DONE]\n\n"
                    break
                
                text_chunk = data.get('text', '')
                yield f"data: {json.dumps({'text': text_chunk})}\n\n"
                
    return StreamingResponse(event_stream(), media_type="text/event-stream")
