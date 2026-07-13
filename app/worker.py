import logging
import asyncio
import json
from typing import Dict, Any
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.celery_app import celery_app
from app.insight_engine import build_interpretation
from app.llm_engine import generate_interpretation_answer
from app.services.job_status import increment_job_metric, update_job
from app.storage.database import get_service_client, save_prashna_chart, update_prashna_chart

logger = logging.getLogger(__name__)

@celery_app.task(
    name="generate_reading_task",
    autoretry_for=(httpx.RequestError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_reading_task(chart_id: str, chart: Dict[str, Any], interpretation: Dict[str, Any]) -> str:
    """
    Background task to run the Map-Reduce LLM pipeline.
    This prevents the API from blocking while OpenAI/Gemini generates the 1000-word response.
    """
    logger.info(f"Starting background generation for chart {chart_id}")
    try:
        # Run the heavy LLM Map-Reduce pipeline
        answer = generate_interpretation_answer(chart, interpretation, chart_id=chart_id)
        interpretation["answer"] = answer
        chart["interpretation"] = interpretation
        
        # Update Supabase with the final generated text
        update_prashna_chart(get_service_client(), chart_id, chart)
        logger.info(f"Successfully generated and saved reading for chart {chart_id}")
        return "SUCCESS"
    except Exception as e:
        logger.error(f"Failed to generate reading for chart {chart_id}: {str(e)}")
        # Ideally, we would save the error state to the database here so the frontend knows it failed
        raise e


@celery_app.task(
    name="generate_prashna_chart_task",
    autoretry_for=(httpx.RequestError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_prashna_chart_task(job_id: str, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full Prashna pipeline in the background:
    calculate chart -> save chart -> generate narrative -> update chart.
    """
    logger.info("Starting queued Prashna job %s for user %s", job_id, user_id)
    update_job(job_id, status="calculating_chart", progress=15, message="Calculating chart")

    try:
        asked_at_utc = datetime.now(timezone.utc)
        if payload.get("asked_at_utc"):
            asked_at_utc = datetime.fromisoformat(payload["asked_at_utc"]).astimezone(timezone.utc)

        location = payload["location"]
        chart_payload = {
            "chart_type": "prashna",
            "name": payload["name"],
            "question": payload["question"],
            "question_domain": payload.get("question_domain", ""),
            "question_subdomain": payload.get("question_subdomain", ""),
            "location": {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "place_name": location["place_name"],
            },
        }
        if payload.get("asked_at_utc"):
            chart_payload["asked_at_utc"] = asked_at_utc.isoformat()

        astrology_url = get_settings().astrology_engine_url
        with httpx.Client(timeout=httpx.Timeout(35.0, connect=5.0)) as client:
            resp = client.post(f"{astrology_url}/calculate", json=chart_payload)

        if resp.status_code == 503:
            raise RuntimeError(resp.json().get("detail", "Calculation dependency error"))
        if resp.status_code != 200:
            raise RuntimeError(resp.json().get("detail", "Failed to calculate chart"))

        result = resp.json()
        chart = result["chart"]
        interpretation = result.get("interpretation") or chart.get("interpretation") or build_interpretation(chart)
        if interpretation:
            chart["interpretation"] = interpretation

        chart_id = save_prashna_chart(get_service_client(), chart, user_id)
        chart["id"] = chart_id
        update_job(
            job_id,
            status="generating_answer" if interpretation else "done",
            progress=65 if interpretation else 100,
            message="Generating detailed reading" if interpretation else "Chart ready",
            chart_id=chart_id,
        )

        if interpretation:
            try:
                answer = generate_interpretation_answer(chart, interpretation, chart_id=chart_id)
            except Exception as exc:
                logger.warning("Queued LLM generation failed for %s, using local fallback: %s", chart_id, exc)
                from app.api.prashna import local_interpretation_answer
                answer = local_interpretation_answer(chart, interpretation)

            interpretation["answer"] = answer
            chart["interpretation"] = interpretation
            update_prashna_chart(get_service_client(), chart_id, chart)

        update_job(job_id, status="done", progress=100, message="Reading ready", chart_id=chart_id)
        increment_job_metric("prashna_done")
        logger.info("Queued Prashna job %s completed with chart %s", job_id, chart_id)
        return {"status": "done", "job_id": job_id, "chart_id": chart_id}
    except Exception as exc:
        logger.exception("Queued Prashna job %s failed", job_id)
        update_job(job_id, status="failed", progress=100, message="Generation failed", error=str(exc))
        increment_job_metric("prashna_failed")
        raise


@celery_app.task(
    name="generate_matchmaking_report_task",
    autoretry_for=(httpx.RequestError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_matchmaking_report_task(job_id: str, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build and persist a matchmaking report in the background.
    """
    logger.info("Starting queued matchmaking job %s for user %s", job_id, user_id)
    update_job(job_id, status="calculating_match", progress=20, message="Calculating compatibility")

    async def _run() -> dict[str, Any]:
        from app.services.matchmaking_service import build_match_report
        from app.storage.matchmaking_db import save_match_report

        report = await build_match_report(payload["boy"], payload["girl"])
        update_job(job_id, status="saving_report", progress=80, message="Saving report")
        saved = await save_match_report(user_id, report)
        return saved

    try:
        saved = asyncio.run(_run())
        update_job(
            job_id,
            status="done",
            progress=100,
            message="Match report ready",
            match_id=saved["match_id"],
        )
        increment_job_metric("matchmaking_done")
        logger.info("Queued matchmaking job %s completed with match %s", job_id, saved["match_id"])
        return {"status": "done", "job_id": job_id, "match_id": saved["match_id"]}
    except Exception as exc:
        logger.exception("Queued matchmaking job %s failed", job_id)
        update_job(job_id, status="failed", progress=100, message="Matchmaking failed", error=str(exc))
        increment_job_metric("matchmaking_failed")
        raise


@celery_app.task(
    name="enrich_consultation_request_snapshot_task",
    autoretry_for=(httpx.RequestError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def enrich_consultation_request_snapshot_task(request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a chart snapshot for a public consultation request after the
    request has already been accepted.
    """
    logger.info("Starting consultation snapshot enrichment for %s", request_id)

    async def _run() -> dict[str, Any]:
        from zoneinfo import ZoneInfo

        from app.services.timezone_service import timezone_at
        from app.storage.consultation_db import update_consultation_request

        local_dt = datetime.fromisoformat(f"{payload['date_of_birth']}T{payload['time_of_birth']}")
        tz_name = timezone_at(payload["latitude"], payload["longitude"])
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_name))
        birth_utc = local_dt.astimezone(timezone.utc)

        chart_type = "prashna" if payload.get("topic") == "Prashna" else "lagna"
        chart_req_data = {
            "chart_type": chart_type,
            "name": payload["name"],
            "question": payload.get("question", ""),
            "location": {
                "latitude": payload["latitude"],
                "longitude": payload["longitude"],
                "place_name": payload["place_of_birth"],
            },
        }
        if chart_type == "lagna":
            chart_req_data["birth_datetime_local"] = f"{payload['date_of_birth']}T{payload['time_of_birth']}"
        else:
            chart_req_data["asked_at_utc"] = birth_utc.isoformat()

        astrology_url = get_settings().astrology_engine_url
        with httpx.Client(timeout=httpx.Timeout(35.0, connect=5.0)) as client:
            resp = client.post(f"{astrology_url}/calculate", json=chart_req_data)
        if resp.status_code != 200:
            raise RuntimeError(f"Snapshot calculation failed with status {resp.status_code}")

        chart = resp.json()["chart"]
        return await update_consultation_request(request_id, {"astrological_snapshot": json.dumps(chart)})

    try:
        result = asyncio.run(_run())
        increment_job_metric("consultation_snapshot_done")
        logger.info("Consultation snapshot enrichment completed for %s", request_id)
        return {"status": "done", "request_id": request_id, "request": result.get("request")}
    except Exception as exc:
        logger.exception("Consultation snapshot enrichment failed for %s", request_id)
        increment_job_metric("consultation_snapshot_failed")
        raise


@celery_app.task(
    name="enrich_paid_consultation_snapshot_task",
    autoretry_for=(httpx.RequestError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def enrich_paid_consultation_snapshot_task(consultation_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a paid consultation chart snapshot after the booking is accepted.
    """
    logger.info("Starting paid consultation snapshot enrichment for %s", consultation_id)

    async def _run() -> bool:
        from zoneinfo import ZoneInfo

        from app.services.timezone_service import timezone_at
        from app.storage.consultation_db import update_paid_consultation_snapshot

        local_dt = datetime.fromisoformat(payload["birth_datetime_local"])
        location = payload["location"]
        tz_name = timezone_at(location["latitude"], location["longitude"])
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_name))
        birth_utc = local_dt.astimezone(timezone.utc)

        chart_req_data = {
            "chart_type": "prashna",
            "name": payload["name"],
            "question": payload["question"],
            "location": {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "place_name": location["place_name"],
            },
            "asked_at_utc": birth_utc.isoformat(),
        }

        astrology_url = get_settings().astrology_engine_url
        with httpx.Client(timeout=httpx.Timeout(35.0, connect=5.0)) as client:
            resp = client.post(f"{astrology_url}/calculate", json=chart_req_data)
        if resp.status_code != 200:
            raise RuntimeError(f"Paid snapshot calculation failed with status {resp.status_code}")

        chart = resp.json()["chart"]
        return await update_paid_consultation_snapshot(consultation_id, json.dumps(chart))

    try:
        updated = asyncio.run(_run())
        increment_job_metric("paid_snapshot_done" if updated else "paid_snapshot_failed")
        logger.info("Paid consultation snapshot enrichment completed for %s", consultation_id)
        return {"status": "done" if updated else "not_updated", "consultation_id": consultation_id}
    except Exception:
        logger.exception("Paid consultation snapshot enrichment failed for %s", consultation_id)
        increment_job_metric("paid_snapshot_failed")
        raise
