from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import Field, field_validator

from app.core.rate_limiter import booking_limiter, llm_limiter
from app.dependencies import AuthState, RequireAdmin, get_current_user
from app.schemas.consultation_case import AstrologySnapshot, ConsultationCasePayload
from app.services.job_status import create_job, get_job
from app.services.matchmaking_service import build_match_report
from app.storage.consultation_db import create_consultation_case, get_founder_consultant, get_public_consultation_queue_status
from app.storage.matchmaking_db import (
    get_match_report,
    list_match_reports,
    save_match_report,
    update_match_report_status,
)
from app.storage.audit_db import record_admin_audit
from app.schemas.common import ID_RE, PHONE_RE, StrictRequestModel

router = APIRouter()


class MatchBirthInput(StrictRequestModel):
    name: str = Field(min_length=1, max_length=80)
    date_of_birth: str = Field(min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_of_birth: str = Field(default="", max_length=8, pattern=r"^$|\d{2}:\d{2}(:\d{2})?$")
    birth_place: str = Field(min_length=2, max_length=160)
    selected_place_name: str = Field(default="", max_length=180)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    gender: str = Field(pattern="^(male|female|other)$")
    birth_time_accuracy: str = Field(pattern="^(exact|approximate|unknown)$")


class MatchCreateRequest(StrictRequestModel):
    boy: MatchBirthInput
    girl: MatchBirthInput


class MatchConsultationRequest(StrictRequestModel):
    question: str = Field(default="Please review this Kundali match for marriage compatibility.", max_length=2000)
    contact_email: str = Field(default="", max_length=160, pattern=r"^$|[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = Field(default="", max_length=24, pattern=r"^$|\+?[0-9 ()-]{6,24}$")
    payment_ref: str = Field(default="match_free_review", max_length=120, pattern=ID_RE)
    scheduled_at: Optional[str] = Field(default=None, max_length=120)
    preferred_slot: str = Field(default="", max_length=120)
    report_snapshot: Optional[dict] = None


class AdminMatchStatusUpdate(StrictRequestModel):
    status: str = Field(pattern="^(calculated|consultation_booked|completed|rejected|cancelled)$")


@router.post("/matchmaking/requests", dependencies=[Depends(llm_limiter)])
async def create_matchmaking_request(
    payload: MatchCreateRequest,
    auth: AuthState = Depends(get_current_user),
    sync: bool = Query(default=False),
) -> dict:
    if not sync:
        job = create_job(
            "matchmaking_generation",
            auth.user_id,
            metadata={
                "boy_name": payload.boy.name,
                "girl_name": payload.girl.name,
            },
        )
        try:
            from app.worker import generate_matchmaking_report_task
            generate_matchmaking_report_task.delay(job["job_id"], auth.user_id, payload.model_dump(mode="json"))
        except Exception as exc:
            from app.services.job_status import update_job
            update_job(job["job_id"], status="failed", progress=100, message="Queue unavailable", error=str(exc))
            raise HTTPException(status_code=503, detail="Matchmaking queue is unavailable. Please try again shortly.") from exc
        return {
            "status": "queued",
            "job_id": job["job_id"],
            "message": "Your matchmaking report is being generated.",
        }

    try:
        report = await build_match_report(payload.boy.model_dump(), payload.girl.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Match calculation failed: {str(exc)}") from exc

    saved = await save_match_report(auth.user_id, report)
    return {"match_id": saved["match_id"], "report": saved["report"]}


@router.get("/matchmaking/jobs/{job_id}")
async def read_matchmaking_job(job_id: str = Path(pattern=r"^job_[A-Za-z0-9]{8,40}$"), auth: AuthState = Depends(get_current_user)) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != auth.user_id and not auth.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to read this job")

    response = {
        key: value
        for key, value in job.items()
        if key not in {"user_id"}
    }
    match_id = job.get("match_id")
    if match_id and job.get("status") == "done":
        result = await get_match_report(match_id, auth.user_id if not auth.is_admin else None)
        if result:
            response["match_id"] = result["match_id"]
            response["report"] = result["report"]
    return response


@router.get("/matchmaking/requests/{match_id}")
async def read_matchmaking_result(match_id: Annotated[str, Path(pattern=ID_RE)], auth: AuthState = Depends(get_current_user)) -> dict:
    result = await get_match_report(match_id, auth.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Match report not found.")
    return result


@router.get("/matchmaking/requests/{match_id}/astrologer")
async def recommend_astrologer_for_match(match_id: Annotated[str, Path(pattern=ID_RE)], auth: AuthState = Depends(get_current_user)) -> dict:
    result = await get_match_report(match_id, auth.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Match report not found.")
    consultant = await get_founder_consultant()
    return {
        "consultant": consultant,
        "reason": "Recommended because this consultant currently handles marriage and Kundali review requests on the platform.",
        "match_summary": result["report"]["summary"],
    }


@router.post("/matchmaking/requests/{match_id}/consultation")
async def create_matchmaking_consultation_request(
    match_id: Annotated[str, Path(pattern=ID_RE)],
    payload: MatchConsultationRequest,
    auth: AuthState = Depends(get_current_user),
    _ = Depends(booking_limiter),
) -> dict:
    result = await get_match_report(match_id, auth.user_id)
    report = result["report"] if result else payload.report_snapshot
    if not report:
        raise HTTPException(status_code=404, detail="Match report not found. Please regenerate the match report.")
    try:
        case_payload = build_matchmaking_case_payload(
            match_id=match_id,
            report=report,
            question=payload.question.strip(),
            email=payload.contact_email.strip() or auth.email,
            phone=payload.phone.strip(),
            preferred_slot=payload.preferred_slot or payload.scheduled_at or "",
        )
        result = await create_consultation_case(case_payload, user_id=auth.user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Booking could not be saved to admin queue: {str(exc)}") from exc

    return {
        **result,
        "message": "Match consultation request sent to admin and Rupesh Kumar with the full match case file.",
    }


@router.get("/admin/matchmaking/requests")
async def admin_list_matchmaking_requests(
    status: Optional[str] = Query(default=None, max_length=40),
    auth: AuthState = Depends(RequireAdmin()),
) -> dict:
    return {"requests": await list_match_reports(status)}


@router.patch("/admin/matchmaking/requests/{match_id}")
async def admin_update_matchmaking_request(
    match_id: Annotated[str, Path(pattern=ID_RE)],
    payload: AdminMatchStatusUpdate,
    auth: AuthState = Depends(RequireAdmin()),
) -> dict:
    before = await get_match_report(match_id)
    request = await update_match_report_status(match_id, payload.status)
    if not request:
        raise HTTPException(status_code=404, detail="Match report not found.")
    record_admin_audit(
        actor_user_id=auth.user_id,
        entity_type="matchmaking_request",
        entity_id=match_id,
        action="status_update",
        before_json=before,
        after_json=request,
    )
    return {"request": request}


def build_matchmaking_booking_payload(
    *,
    match_id: str,
    report: dict,
    question: str,
    email: str,
    phone: str,
    preferred_slot: str,
) -> dict:
    boy = report["participants"]["boy"]
    girl = report["participants"]["girl"]
    ashtakoota = report["ashtakoota"]
    summary = report["summary"]
    full_question = (
        f"Matchmaking consultation\n"
        f"Match ID: {match_id}\n"
        f"Boy: {boy['name']} | {boy['date_of_birth']} {boy['time_of_birth']} | {boy['birth_place']}\n"
        f"Girl: {girl['name']} | {girl['date_of_birth']} {girl['time_of_birth']} | {girl['birth_place']}\n"
        f"Guna Milan: {ashtakoota['total_score']}/{ashtakoota['max_score']} ({ashtakoota['category']})\n"
        f"Recommendation: {summary['final_recommendation']}\n"
        f"User question: {question or 'Please review this Kundali match for marriage compatibility.'}"
    )
    return {
        "consultant_id": "founder-rupesh-kumar",
        "name": f"{boy['name']} & {girl['name']}",
        "phone": phone or "not_provided",
        "email": email,
        "date_of_birth": boy["date_of_birth"],
        "time_of_birth": boy["time_of_birth"],
        "place_of_birth": f"{boy['birth_place']} / {girl['birth_place']}",
        "topic": "Marriage",
        "question": full_question,
        "preferred_time": preferred_slot,
        "payment_status": "not_paid",
    }


def build_matchmaking_case_payload(
    *,
    match_id: str,
    report: dict,
    question: str,
    email: str,
    phone: str,
    preferred_slot: str,
) -> ConsultationCasePayload:
    boy = report["participants"]["boy"]
    girl = report["participants"]["girl"]
    ashtakoota = report["ashtakoota"]
    summary = report["summary"]
    full_question = (
        f"Matchmaking consultation\n"
        f"Match ID: {match_id}\n"
        f"Boy: {boy['name']} | {boy['date_of_birth']} {boy['time_of_birth']} | {boy['birth_place']}\n"
        f"Girl: {girl['name']} | {girl['date_of_birth']} {girl['time_of_birth']} | {girl['birth_place']}\n"
        f"Guna Milan: {ashtakoota['total_score']}/{ashtakoota['max_score']} ({ashtakoota['category']})\n"
        f"Recommendation: {summary['final_recommendation']}\n"
        f"User question: {question or 'Please review this Kundali match for marriage compatibility.'}"
    )
    return ConsultationCasePayload.model_validate({
        "source_type": "matchmaking",
        "chart_type": "matchmaking",
        "user": {
            "full_name": f"{boy['name']} & {girl['name']}",
            "email": email or "matchmaking@example.com",
            "mobile_number": phone or "not_provided",
            "date_of_birth": boy.get("date_of_birth"),
            "time_of_birth": boy.get("time_of_birth"),
            "place": f"{boy.get('birth_place', '')} / {girl.get('birth_place', '')}"[:180],
            "latitude": boy.get("latitude"),
            "longitude": boy.get("longitude"),
        },
        "consultation": {
            "question": full_question,
            "additional_message": question,
            "preferred_time": preferred_slot,
            "consultation_mode": "matchmaking_consultation",
            "payment_status": "not_paid",
        },
        "astrology_snapshot": {
            "chart_type": "matchmaking",
            "chart": {
                "meta": {
                    "chart_type": "matchmaking",
                    "match_id": match_id,
                    "overall_result": summary.get("overall_result"),
                    "guna_score": ashtakoota.get("total_score"),
                    "max_score": ashtakoota.get("max_score"),
                }
            },
            "interpretation": summary,
            "source_result": {
                "type": "matchmaking",
                "match_id": match_id,
                "report": report,
            },
            "question_context": {
                "match_id": match_id,
                "question": question,
                "preferred_slot": preferred_slot,
            },
        },
        "idempotency_key": f"matchmaking:{match_id}:{email or auth_safe_email(email)}",
    })


def auth_safe_email(email: str) -> str:
    return email or "anonymous"
