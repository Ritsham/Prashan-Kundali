from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import AuthState, RequireRole, get_current_user
from app.schemas.consultation_case import AstrologySnapshot, ConsultationCasePayload
from app.services.matchmaking_service import build_match_report
from app.storage.consultation_db import create_consultation_case, get_founder_consultant, get_public_consultation_queue_status
from app.storage.matchmaking_db import (
    get_match_report,
    list_match_reports,
    save_match_report,
)

router = APIRouter()


class MatchBirthInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    date_of_birth: str = Field(min_length=10, max_length=10)
    time_of_birth: str = Field(default="", max_length=8)
    birth_place: str = Field(min_length=2, max_length=160)
    selected_place_name: str = Field(default="", max_length=180)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    gender: str = Field(pattern="^(male|female|other)$")
    birth_time_accuracy: str = Field(pattern="^(exact|approximate|unknown)$")


class MatchCreateRequest(BaseModel):
    boy: MatchBirthInput
    girl: MatchBirthInput


class MatchConsultationRequest(BaseModel):
    question: str = Field(default="Please review this Kundali match for marriage compatibility.", max_length=2000)
    contact_email: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=24)
    payment_ref: str = Field(default="match_free_review", max_length=120)
    scheduled_at: Optional[str] = Field(default=None, max_length=120)
    preferred_slot: str = Field(default="", max_length=120)
    report_snapshot: Optional[dict] = None


@router.post("/matchmaking/requests")
async def create_matchmaking_request(payload: MatchCreateRequest, auth: AuthState = Depends(get_current_user)) -> dict:
    try:
        report = await build_match_report(payload.boy.model_dump(), payload.girl.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Match calculation failed: {str(exc)}") from exc

    saved = await save_match_report(auth.user_id, report)
    return {"match_id": saved["match_id"], "report": saved["report"]}


@router.get("/matchmaking/requests/{match_id}")
async def read_matchmaking_result(match_id: str, auth: AuthState = Depends(get_current_user)) -> dict:
    result = await get_match_report(match_id, auth.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Match report not found.")
    return result


@router.get("/matchmaking/requests/{match_id}/astrologer")
async def recommend_astrologer_for_match(match_id: str, auth: AuthState = Depends(get_current_user)) -> dict:
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
    match_id: str,
    payload: MatchConsultationRequest,
    auth: AuthState = Depends(get_current_user),
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
    status: Optional[str] = None,
    auth: AuthState = Depends(RequireRole("admin")),
) -> dict:
    return {"requests": await list_match_reports(status)}


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
