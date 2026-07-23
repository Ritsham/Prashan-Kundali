from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from pydantic import Field, field_validator

import httpx
from app.config import get_settings
from app.services.geocoding_service import geocode_place, reverse_geocode_place
from app.storage.database import get_chart, save_prashna_chart, save_lagna_chart, sync_user, update_prashna_chart
from app.dependencies import get_current_user, AuthState
from app.core.rate_limiter import RateLimiter, llm_limiter, public_limiter
from app.insight_engine import build_interpretation
from app.schemas.common import ID_RE, LocationInput, StrictRequestModel, parse_iso_datetime
from app.services.astrology_gateway import AstrologyEngineHTTPError, calculate_chart
from app.services.job_status import create_job, get_job

router = APIRouter()

# Rate limiters
prashna_rate_limiter = RateLimiter(requests=10, window=60) # 10 req / minute
lagna_rate_limiter = RateLimiter(requests=10, window=60)



class PrashnaRequest(StrictRequestModel):
    name: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=3, max_length=1000)
    question_domain: str = Field(default="", max_length=40)
    question_subdomain: str = Field(default="", max_length=40)
    location: LocationInput
    asked_at_utc: Optional[str] = None

    @field_validator("asked_at_utc")
    @classmethod
    def validate_asked_at_utc(cls, value: Optional[str]) -> Optional[str]:
        if value:
            parse_iso_datetime(value, "asked_at_utc")
        return value


class LagnaRequest(StrictRequestModel):
    name: str = Field(min_length=1, max_length=80)
    gender: str = Field(pattern="^(male|female|other)$")
    birth_datetime_local: str = Field(min_length=16, max_length=32)
    location: LocationInput

    @field_validator("birth_datetime_local")
    @classmethod
    def validate_birth_datetime(cls, value: str) -> str:
        parse_iso_datetime(value, "birth_datetime_local")
        return value


class UserSyncRequest(StrictRequestModel):
    email: str = Field(min_length=5, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str = Field(default="", max_length=120)
    mobile_number: str = Field(default="", max_length=24, pattern=r"^$|^\+?[0-9 ()-]{6,24}$")


def _is_admin(auth: AuthState) -> bool:
    return auth.is_admin


@router.post("/users/sync")
def sync_user_endpoint(payload: UserSyncRequest, auth: AuthState = Depends(get_current_user)) -> dict:
    try:
        if payload.email.lower() != auth.email.lower():
            raise HTTPException(status_code=400, detail="Profile email must match the signed-in Google account.")
        if auth.profile_exists:
            return {"status": "success", "profile_exists": True}
        sync_user(auth.client, auth.user_id, auth.email, payload.name, payload.mobile_number)
        return {"status": "success", "profile_exists": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User sync failed: {str(e)}")


@router.post("/prashna")
async def create_prashna(
    payload: PrashnaRequest,
    auth: AuthState = Depends(get_current_user),
    _ = Depends(prashna_rate_limiter),
    sync: bool = Query(default=False),
) -> dict:
    try:
        if not sync:
            job = create_job(
                "prashna_generation",
                auth.user_id,
                metadata={
                    "question_domain": payload.question_domain,
                    "question_subdomain": payload.question_subdomain,
                },
            )
            try:
                from app.worker import generate_prashna_chart_task
                generate_prashna_chart_task.delay(job["job_id"], auth.user_id, payload.model_dump(mode="json"))
            except Exception as exc:
                from app.services.job_status import update_job
                update_job(
                    job["job_id"],
                    status="running_inline",
                    progress=10,
                    message="Queue unavailable; generating directly",
                    error=str(exc),
                )
                sync = True
            else:
                return {
                    "status": "queued",
                    "job_id": job["job_id"],
                    "message": "Your Prashna reading is being generated.",
                }

        asked_at_utc = datetime.now(timezone.utc)
        if payload.asked_at_utc:
            try:
                asked_at_utc = datetime.fromisoformat(payload.asked_at_utc).astimezone(timezone.utc)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid asked_at_utc ISO datetime.") from exc
        
        try:
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

            result = await calculate_chart(payload_data, timeout=30.0)
            chart = result["chart"]
            interpretation = result.get("interpretation") or chart.get("interpretation")
            if not interpretation:
                interpretation = build_interpretation(chart)
            if interpretation:
                chart["interpretation"] = interpretation

        except AstrologyEngineHTTPError as exc:
            status_code = 503 if exc.status_code == 503 else 422
            raise HTTPException(status_code=status_code, detail=exc.detail) from exc
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        # Step 3: Save with the rule-engine interpretation attached.
        chart_id = save_prashna_chart(auth.client, chart, auth.user_id)
        chart["id"] = chart_id
        
        # Step 4: Try to attach the narrative interpretation immediately.
        if interpretation:
            answer = None
            try:
                llm_url = get_settings().llm_engine_url
                async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=5.0)) as client:
                    llm_resp = await client.post(
                        f"{llm_url}/generate/sync",
                        json={
                            "chart_id": chart_id,
                            "chart": chart,
                            "interpretation": interpretation
                        },
                    )
                if llm_resp.status_code == 200:
                    answer = llm_resp.json().get("answer")
            except Exception as exc:
                import logging
                logging.warning("Synchronous LLM interpretation failed, using local narrative fallback: %s", exc)

            interpretation["answer"] = answer if answer and answer.get("text") else local_interpretation_answer(chart, interpretation)
            chart["interpretation"] = interpretation
            try:
                update_prashna_chart(auth.client, chart_id, chart)
            except Exception as exc:
                import logging
                logging.warning("Failed to update chart with interpretation: %s", exc)

        return {"chart_id": chart_id, "chart": chart, "interpretation": interpretation, "status": "done" if interpretation else "chart_ready"}
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("create_prashna_failed")
        raise HTTPException(status_code=500, detail="Failed to create Prashna chart") from exc


@router.get("/prashna/jobs/{job_id}")
def read_prashna_job(job_id: str = Path(pattern=r"^job_[A-Za-z0-9]{8,40}$"), auth: AuthState = Depends(get_current_user)) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != auth.user_id and not _is_admin(auth):
        raise HTTPException(status_code=403, detail="Not allowed to read this job")

    response = {
        key: value
        for key, value in job.items()
        if key not in {"user_id"}
    }
    chart_id = job.get("chart_id")
    if chart_id and job.get("status") == "done":
        chart = get_chart(auth.client, chart_id)
        if chart:
            response["chart"] = chart
            response["interpretation"] = chart.get("interpretation")
    return response


@router.post("/lagna")
async def create_lagna(payload: LagnaRequest, auth: AuthState = Depends(get_current_user), _ = Depends(lagna_rate_limiter)) -> dict:
    try:
        try:
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

            chart = (await calculate_chart(payload_data, timeout=30.0))["chart"]

        except AstrologyEngineHTTPError as exc:
            status_code = 503 if exc.status_code == 503 else 422
            raise HTTPException(status_code=status_code, detail=exc.detail) from exc
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        chart_id = save_lagna_chart(auth.client, chart, auth.user_id)
        chart["id"] = chart_id
        return {"chart_id": chart_id, "chart": chart}
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("create_lagna_failed")
        raise HTTPException(status_code=500, detail="Failed to create Lagna chart") from exc


def local_interpretation_answer(chart: dict, interpretation: dict) -> dict:
    question = chart.get("question", {})
    lagna = chart.get("lagna", {})
    planets = {planet.get("name"): planet for planet in chart.get("planets", [])}
    moon = planets.get("Moon", {})
    verdict = interpretation.get("verdict", {}) or {}
    confidence = interpretation.get("confidence", "medium")
    domain = interpretation.get("domain") or question.get("domain") or "general"
    timing = interpretation.get("timing") or {}
    evidence = interpretation.get("evidence") or []
    supports = [item for item in evidence if item.get("status") in {"strong", "support", "clear"}]
    cautions = [item for item in evidence if item.get("status") in {"caution", "blocked", "weak"}]
    active_dasha = chart.get("dashas", {}).get("current_mahadasha", {})

    support_text = supports[0].get("text") if supports else "The chart has some supportive factors, but they need practical follow-through."
    caution_text = cautions[0].get("text") if cautions else "No single obstruction dominates, though timing still needs patience."
    timing_text = (
        timing.get("summary")
        or timing.get("window")
        or (f"The current {active_dasha.get('lord')} Mahadasha is important for timing." if active_dasha.get("lord") else "Timing should be judged from the active Dasha and current Moon condition.")
    )
    domain_house = {
        "illness": "6th house",
        "marriage": "7th house",
        "child": "5th house",
        "job_career": "10th house",
        "wealth": "2nd and 11th houses",
        "foreign": "9th and 12th houses",
        "education": "4th and 5th houses",
    }.get(domain, "relevant bhava")

    text = f"""Executive Summary
{verdict.get('summary') or 'The Prashna gives a conditional answer that depends on the strength of the Lagna, Moon, and the relevant house.'} Confidence is {confidence}. The chart should be read practically: the Lagna shows the strength of the question itself, the Moon shows the current mental and circumstantial pressure, and the {domain_house} carries the main result for this domain.

Astrological Analysis
The Prashna Lagna is {lagna.get('sign', '-')} at {lagna.get('formatted_degree', '')}, falling in {lagna.get('nakshatra', '-')} Pada {lagna.get('pada', '-')}. This sets the base condition of the matter. The Moon is in {moon.get('sign', '-')} at {moon.get('formatted_degree', '')}, house {moon.get('house', '-')}, in {moon.get('nakshatra', '-')} Pada {moon.get('pada', '-')}. In Prashna, Moon is especially important because it describes the querent's mind, the immediacy of the question, and how quickly circumstances can move.

The strongest support is: {support_text}

The strongest caution is: {caution_text}

Practical Interpretation
For this question, judge the {domain_house} along with its lord, occupants, and relation to Lagna and Moon. If supportive factors are stronger, the matter can move forward, but if caution factors dominate, the outcome becomes delayed, conditional, or dependent on correction. This interpretation is traditional astrological guidance and should be used alongside practical judgment.

Timing
{timing_text} Use the active Vimshottari Dasha chain as the main timing trigger. When the Dasha lord supports the relevant house, events become easier to activate. When it connects to obstruction, disease, debt, delay, or hidden houses, the result needs patience and corrective action.

Things to Avoid
Avoid acting only from anxiety or impatience. In Prashna, a disturbed Moon can make the situation feel more urgent than it is. Do not ignore real-world documentation, medical advice, relationship communication, or professional process depending on the domain of the question.

Final Verdict
The chart leans according to the balance of support and obstruction described above. The answer is not meant to replace professional advice, but it gives a clear astrological direction for what is likely, what needs correction, and where timing should be watched."""

    return {
        "text": text.strip(),
        "mode": "local_rule_engine",
        "provider": "insight_engine",
        "model": "",
        "note": "Generated locally from the backend interpretation engine because the LLM service was unavailable or did not return text.",
    }


@router.get("/charts/{chart_id}")
def read_chart(chart_id: str = Path(pattern=ID_RE), auth: AuthState = Depends(get_current_user)) -> dict:
    chart = get_chart(auth.client, chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if chart.get("user_id") != auth.user_id and not _is_admin(auth):
        raise HTTPException(status_code=403, detail="Not allowed to read this chart")
    return {"chart_id": chart_id, "chart": chart}


@router.get("/geocode")
def geocode(
    query: str = Query(min_length=2, max_length=160),
    limit: int = Query(default=6, ge=1, le=8),
    _ = Depends(public_limiter),
) -> dict:
    if len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Enter at least 2 characters.")
    return {"query": query, "results": geocode_place(query, limit=max(1, min(limit, 8)))}


@router.get("/reverse_geocode")
def reverse_geocode(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    _ = Depends(public_limiter),
) -> dict:
    return reverse_geocode_place(lat, lon)

from fastapi.responses import StreamingResponse
import redis
import json

@router.get("/stream/{chart_id}")
def stream_chart(chart_id: str = Path(pattern=ID_RE), auth: AuthState = Depends(get_current_user), _ = Depends(llm_limiter)):
    chart = get_chart(auth.client, chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if chart.get("user_id") != auth.user_id and not _is_admin(auth):
        raise HTTPException(status_code=403, detail="Not allowed to stream this chart")

    def event_stream():
        redis_client = redis.Redis.from_url(get_settings().redis_url)
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
