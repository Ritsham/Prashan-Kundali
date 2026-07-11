from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

from app.storage.database import supabase
from app.storage.consultation_db import FOUNDER_CONSULTANT

_LOCAL_MATCHES: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_matchmaking_db() -> None:
    pass


async def save_match_report(user_id: str, report: dict[str, Any], status: str = "calculated") -> dict[str, Any]:
    match_id = f"match_{uuid4().hex[:12]}"
    row = {
        "id": match_id,
        "user_id": user_id,
        "status": status,
        "boy_name": report["participants"]["boy"]["name"],
        "girl_name": report["participants"]["girl"]["name"],
        "guna_score": report["ashtakoota"]["total_score"],
        "max_score": report["ashtakoota"]["max_score"],
        "result_category": report["summary"]["overall_result"],
        "report_json": json.dumps(report),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    _LOCAL_MATCHES[match_id] = row
    try:
        if supabase:
            supabase.table("match_requests").insert(row).execute()
    except Exception as exc:
        print(f"Warning: Supabase save_match_report failed: {exc}")
    return {"match_id": match_id, "report": report}


async def get_match_report(match_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    row = _LOCAL_MATCHES.get(match_id)
    try:
        if supabase:
            query = supabase.table("match_requests").select("*").eq("id", match_id)
            if user_id:
                query = query.eq("user_id", user_id)
            res = query.execute()
            if res.data:
                row = dict(res.data[0])
    except Exception as exc:
        print(f"Warning: Supabase get_match_report failed: {exc}")

    if not row:
        return None
    report_json = row.get("report_json")
    report = json.loads(report_json) if isinstance(report_json, str) else report_json
    return {"match_id": row["id"], "request": row, "report": report}


async def list_match_reports(status: str | None = None) -> list[dict[str, Any]]:
    rows = list(_LOCAL_MATCHES.values())
    try:
        if supabase:
            query = supabase.table("match_requests").select("*")
            if status:
                query = query.eq("status", status)
            res = query.order("created_at", desc=True).execute()
            rows = [dict(row) for row in (res.data or [])]
    except Exception as exc:
        print(f"Warning: Supabase list_match_reports failed: {exc}")
    return [public_match_row(row) for row in rows]


async def create_matchmaking_consultation(
    *,
    user_id: str,
    user_email: str,
    phone: str = "",
    match_id: str,
    report: dict[str, Any],
    question: str,
    payment_ref: str = "match_free_review",
    scheduled_at: str | None = None,
    db_client: Any | None = None,
) -> dict[str, Any]:
    consultation_id = f"cons_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    snapshot = {
        "type": "matchmaking",
        "match_id": match_id,
        "report": report,
        "user_question": question,
        "ai_summary": report["summary"]["ai_summary"],
        "attached_at": now.isoformat(),
    }
    boy = report["participants"]["boy"]
    girl = report["participants"]["girl"]
    row = {
        "id": consultation_id,
        "user_name": f"{boy['name']} & {girl['name']}",
        "user_email": user_email,
        "question_text": question or "Please review this Kundali match for marriage compatibility.",
        "astrological_snapshot": json.dumps(snapshot),
        "whatsapp_no": phone or None,
        "gender": "other",
        "birth_date": boy["date_of_birth"],
        "birth_time": boy["time_of_birth"],
        "birth_place": f"{boy['birth_place']} / {girl['birth_place']}",
        "status": "QUEUED",
        "payment_ref": payment_ref,
        "amount": 0.0,
        "created_at": now.isoformat(),
        "sla_deadline": (now + timedelta(hours=24)).isoformat(),
        "scheduled_at": scheduled_at,
        "match_request_id": match_id,
        "consultant_id": FOUNDER_CONSULTANT["id"],
    }
    db = db_client or supabase
    try:
        if db:
            insert_row = {k: v for k, v in row.items() if k not in {"scheduled_at", "match_request_id", "consultant_id"}}
            db.table("paid_consultations").insert(insert_row).execute()
    except Exception as exc:
        print(f"Warning: Supabase create_matchmaking_consultation failed: {exc}")
        raise RuntimeError(f"Consultation booking could not be saved to admin queue: {exc}") from exc

    try:
        if db:
            stats_res = db.table("consultant_platform_stats").select("current_queue_size").eq("id", 1).execute()
            if stats_res.data:
                current_size = int(stats_res.data[0].get("current_queue_size") or 0)
                db.table("consultant_platform_stats").update({"current_queue_size": current_size + 1}).eq("id", 1).execute()
    except Exception as exc:
        print(f"Warning: Supabase matchmaking queue stats update failed: {exc}")

    try:
        if db:
            db.table("match_requests").update({"status": "consultation_booked", "updated_at": now.isoformat()}).eq("id", match_id).execute()
    except Exception as exc:
        print(f"Warning: Supabase matchmaking status update failed: {exc}")

    return {
        "consultation": row,
        "message": "Booking confirmed. Match details were sent to Rupesh Kumar and added to the admin queue.",
    }


def build_admin_question(match_id: str, report: dict[str, Any], question: str) -> str:
    boy = report["participants"]["boy"]
    girl = report["participants"]["girl"]
    summary = report["summary"]
    ashtakoota = report["ashtakoota"]
    return (
        f"Matchmaking consultation\n"
        f"Match ID: {match_id}\n"
        f"Boy: {boy['name']} | {boy['date_of_birth']} {boy['time_of_birth']} | {boy['birth_place']}\n"
        f"Girl: {girl['name']} | {girl['date_of_birth']} {girl['time_of_birth']} | {girl['birth_place']}\n"
        f"Guna Milan: {ashtakoota['total_score']}/{ashtakoota['max_score']} ({ashtakoota['category']})\n"
        f"Recommendation: {summary['final_recommendation']}\n"
        f"User question: {question or 'Please review this Kundali match for marriage compatibility.'}"
    )


def public_match_row(row: dict[str, Any]) -> dict[str, Any]:
    report_data = row.get("report_json") or row.get("report_data")
    return {
        "id": row["id"],
        "user_id": row.get("user_id"),
        "status": row.get("status"),
        "boy_name": row.get("boy_name"),
        "girl_name": row.get("girl_name"),
        "guna_score": row.get("guna_score"),
        "max_score": row.get("max_score"),
        "result_category": row.get("result_category"),
        "report_data": report_data,
        "report_json": report_data,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
