from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.chart_calculator import CalculationDependencyError, calculate_prashna_chart
from app.services.geocoding_service import geocode_place, reverse_geocode_place
from app.services.timezone_service import timezone_at
from app.storage.database import get_chart, save_prashna_chart, save_lagna_chart, sync_user
from app.dependencies import get_current_user, AuthState

router = APIRouter()


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
def create_prashna(payload: PrashnaRequest, auth: AuthState = Depends(get_current_user)) -> dict:
    try:
        asked_at_utc = datetime.now(timezone.utc)
        if payload.asked_at_utc:
            try:
                asked_at_utc = datetime.fromisoformat(payload.asked_at_utc).astimezone(timezone.utc)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid asked_at_utc ISO datetime.") from exc
        
        try:
            chart = calculate_prashna_chart(
                question=payload.question,
                name=payload.name,
                asked_at_utc=asked_at_utc,
                latitude=payload.location.latitude,
                longitude=payload.location.longitude,
                place_name=payload.location.place_name,
                chart_type="prashna",
                question_domain=payload.question_domain,
                question_subdomain=payload.question_subdomain,
            )
        except CalculationDependencyError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        chart_id = save_prashna_chart(auth.client, chart, auth.user_id)
        chart["id"] = chart_id
        return {"chart_id": chart_id, "chart": chart}
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(exc), "traceback": tb})


@router.post("/lagna")
def create_lagna(payload: LagnaRequest, auth: AuthState = Depends(get_current_user)) -> dict:
    try:
        try:
            tz_name = timezone_at(payload.location.latitude, payload.location.longitude)
            local_dt = datetime.fromisoformat(payload.birth_datetime_local)
            if local_dt.tzinfo is None:
                local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_name))
            birth_utc = local_dt.astimezone(timezone.utc)
            chart = calculate_prashna_chart(
                question="",
                name=payload.name,
                asked_at_utc=birth_utc,
                latitude=payload.location.latitude,
                longitude=payload.location.longitude,
                place_name=payload.location.place_name,
                chart_type="lagna",
                gender=payload.gender,
            )
        except CalculationDependencyError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
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
