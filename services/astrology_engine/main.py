"""
Astrology Engine Microservice
=============================
Standalone FastAPI server for the Math + Insight pipeline.

Responsibilities:
  - Calculate Prashna & Lagna charts (PySwisseph)
  - Run the Insight Engine (rule-based normalization)
  - Expose a clean internal HTTP API for the Gateway or LLM service

Endpoints:
  POST /calculate   — full chart + insight payload
  GET  /health      — liveness probe
"""
from dotenv import load_dotenv
load_dotenv()

import sys, os

# Make parent packages importable (shared app/ code lives in the repo root)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.chart_calculator import CalculationDependencyError, calculate_prashna_chart
from app.services.timezone_service import timezone_at
from app.insight_engine import build_interpretation

app = FastAPI(
    title="Astrology Engine",
    version="1.0.0",
    description="Internal microservice: Math (PySwisseph) + Insight Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────── Models ────────────────────────────

class LocationInput(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    place_name: str = Field(min_length=1, max_length=160)


class ChartRequest(BaseModel):
    chart_type: str = Field(default="prashna", pattern="^(prashna|lagna)$")
    name: str = Field(min_length=1, max_length=80)
    question: str = Field(default="", max_length=1000)
    question_domain: str = Field(default="", max_length=40)
    question_subdomain: str = Field(default="", max_length=40)
    gender: Optional[str] = Field(default=None, pattern="^(male|female|other)$")
    location: LocationInput
    asked_at_utc: Optional[str] = None
    birth_datetime_local: Optional[str] = None


# ─────────────────────────── Routes ────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "astrology_engine"}


@app.post("/calculate")
async def calculate(payload: ChartRequest) -> dict:
    try:
        # ── Resolve timestamp ──────────────────────────────────────
        if payload.chart_type == "lagna":
            if not payload.birth_datetime_local:
                raise HTTPException(status_code=400, detail="birth_datetime_local is required for lagna charts")
            tz_name = timezone_at(payload.location.latitude, payload.location.longitude)
            local_dt = datetime.fromisoformat(payload.birth_datetime_local)
            if local_dt.tzinfo is None:
                local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_name))
            asked_at_utc = local_dt.astimezone(timezone.utc)
        else:
            asked_at_utc = datetime.now(timezone.utc)
            if payload.asked_at_utc:
                try:
                    asked_at_utc = datetime.fromisoformat(payload.asked_at_utc).astimezone(timezone.utc)
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail="Invalid asked_at_utc ISO datetime.") from exc

        # ── Step 1: Math Engine ────────────────────────────────────
        try:
            chart = await calculate_prashna_chart(
                question=payload.question,
                name=payload.name,
                asked_at_utc=asked_at_utc,
                latitude=payload.location.latitude,
                longitude=payload.location.longitude,
                place_name=payload.location.place_name,
                chart_type=payload.chart_type,
                question_domain=payload.question_domain,
                question_subdomain=payload.question_subdomain,
                gender=payload.gender,
            )
        except CalculationDependencyError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            import traceback
            raise HTTPException(status_code=422, detail=f"{str(exc)}\n\n{traceback.format_exc()}") from exc

        # ── Step 2: Insight Engine ─────────────────────────────────
        interpretation = build_interpretation(chart)
        if interpretation:
            chart["interpretation"] = interpretation

        return {"chart": chart, "interpretation": interpretation}

    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        raise HTTPException(status_code=500, detail={"error": str(exc), "traceback": traceback.format_exc()})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
