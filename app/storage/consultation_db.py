import json
import os
import re
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from app.core.consultation_lifecycle import (
    ACTIVE_CONSULTATION_STATUSES,
    CONSULTATION_STATUS_CONFIRMED,
    CONSULTATION_STATUS_PENDING_PAYMENT,
    CONSULTATION_STATUS_REQUESTED,
    assert_consultation_transition,
    normalize_consultation_status,
    validate_price_amount,
)
from app.config import get_settings
from app.storage.database import supabase
from app.schemas.consultation_case import ConsultationCasePayload

MAX_ACTIVE_CONSULTATION_REQUESTS = 20
MAX_ACTIVE_CONSULTATION_REQUESTS_PER_ACCOUNT = 5
MISSING_SCHEMA_COLUMN_RE = re.compile(r"Could not find the '([^']+)' column")

FOUNDER_CONSULTANT = {
    "id": "founder-rupesh-kumar",
    "name": "Rupesh Kumar",
    "title": "Founder Astrologer / Primary Consultant",
    "photo_url": "https://www.shanitemple.com/index_images/astrology-puja/janamkundli.png",
    "bio": "Founder astrologer at Shree Lakshmi Astro, focused on practical guidance through Birth Chart, Prashna Kundali, prediction analysis, and case-based consultation.",
    "experience": "3+ years",
    "systems": ["Vedic Astrology", "Prashna Kundali", "Lagna Kundali", "KP-oriented analysis"],
    "languages": ["Hindi", "English"],
    "consultation_type": "Birth Chart, Prashna, Career, Marriage, Business, Health, and personal guidance",
    "consultation_fee": None,
    "contact_phone": "",
    "whatsapp_number": "",
    "is_active": True,
}

async def init_consultation_db() -> None:
    # Supabase handles schema via SQL migrations
    pass


async def get_founder_consultant() -> Dict[str, Any]:
    settings = get_settings()
    consultant = dict(FOUNDER_CONSULTANT)
    consultant["consultation_fee"] = float(validate_price_amount(settings.consultation_price_inr))
    consultant["contact_phone"] = os.getenv("FOUNDER_CONSULTANT_PHONE", consultant.get("contact_phone") or "").strip()
    consultant["whatsapp_number"] = os.getenv("FOUNDER_CONSULTANT_WHATSAPP", consultant.get("whatsapp_number") or "").strip()
    return consultant


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _encode_json(value: Any) -> Any:
    if value is None:
        return None
    return value


def _missing_schema_column(exc: Exception) -> Optional[str]:
    match = MISSING_SCHEMA_COLUMN_RE.search(str(exc))
    return match.group(1) if match else None


def _insert_with_schema_fallback(db: Any, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
    insert_row = dict(row)
    removed_columns: list[str] = []
    while True:
        try:
            db.table(table).insert(insert_row).execute()
            if removed_columns:
                print(f"Warning: {table} insert omitted unsupported columns: {', '.join(removed_columns)}")
            return insert_row
        except Exception as exc:
            missing_column = _missing_schema_column(exc)
            if not missing_column or missing_column not in insert_row:
                raise
            if get_settings().is_production:
                raise RuntimeError(f"Production schema is missing required column: {missing_column}") from exc
            removed_columns.append(missing_column)
            insert_row.pop(missing_column, None)


def _normalize_case_row(row: Dict[str, Any]) -> Dict[str, Any]:
    case = dict(row)
    snapshot = _json_value(case.get("astrology_snapshot") or case.get("astrological_snapshot"))
    case["astrology_snapshot"] = snapshot
    case["astrological_snapshot"] = snapshot
    case["chart_snapshot"] = snapshot
    contract = snapshot.get("case_contract") if isinstance(snapshot, dict) else {}
    source_result = snapshot.get("source_result") if isinstance(snapshot, dict) else {}
    if not isinstance(contract, dict):
        contract = {}
    if not isinstance(source_result, dict):
        source_result = {}
    case["case_id"] = case.get("id")
    case["case_status"] = case.get("status")
    case.setdefault(
        "source_type",
        contract.get("source_type")
        or ("matchmaking" if source_result.get("type") == "matchmaking" or case.get("topic") == "Marriage Match" else ("prashna" if case.get("topic") == "Prashna" else "direct_consultation")),
    )
    case.setdefault(
        "chart_type",
        contract.get("chart_type")
        or ("matchmaking" if source_result.get("type") == "matchmaking" or case.get("topic") == "Marriage Match" else ("prashna" if case.get("topic") == "Prashna" else "lagna")),
    )
    case["user"] = {
        "full_name": case.get("name") or "",
        "email": case.get("email") or "",
        "mobile_number": case.get("phone") or "",
        "gender": case.get("gender"),
        "date_of_birth": case.get("date_of_birth"),
        "time_of_birth": case.get("time_of_birth"),
        "place": case.get("place_of_birth"),
        "latitude": case.get("latitude"),
        "longitude": case.get("longitude"),
        "timezone": case.get("timezone"),
    }
    case["consultation"] = {
        "question": case.get("question") or "",
        "additional_message": case.get("additional_message") or contract.get("additional_message"),
        "preferred_date": case.get("preferred_date"),
        "preferred_time": case.get("preferred_time") or contract.get("preferred_time"),
        "consultation_mode": case.get("consultation_mode") or contract.get("consultation_mode"),
        "payment_status": case.get("payment_status"),
        "quoted_price": case.get("quoted_price"),
        "currency": case.get("currency") or "INR",
    }
    return case


def _status_filter_values() -> list[str]:
    statuses = ACTIVE_CONSULTATION_STATUSES - {CONSULTATION_STATUS_PENDING_PAYMENT}
    return sorted(statuses | {"pending", "accepted", "scheduled", "in_progress", "waiting_queue", "QUEUED"})


async def _has_active_booking_conflict(
    db: Any,
    *,
    user_id: Optional[str],
    email: Optional[str],
    consultant_id: str,
    preferred_date: Optional[str],
    preferred_time: Optional[str],
) -> bool:
    if not db:
        return False
    active_ids: set[str] = set()
    try:
        if user_id:
            user_res = (
                db.table("consultation_requests")
                .select("id")
                .eq("consultant_id", consultant_id)
                .in_("status", _status_filter_values())
                .eq("user_id", user_id)
                .limit(MAX_ACTIVE_CONSULTATION_REQUESTS_PER_ACCOUNT)
                .execute()
            )
            active_ids.update(str(row.get("id")) for row in (user_res.data or []) if row.get("id"))
        if email and len(active_ids) < MAX_ACTIVE_CONSULTATION_REQUESTS_PER_ACCOUNT:
            email_res = (
                db.table("consultation_requests")
                .select("id")
                .eq("consultant_id", consultant_id)
                .in_("status", _status_filter_values())
                .eq("email", email)
                .limit(MAX_ACTIVE_CONSULTATION_REQUESTS_PER_ACCOUNT)
                .execute()
            )
            active_ids.update(str(row.get("id")) for row in (email_res.data or []) if row.get("id"))
        return len(active_ids) >= MAX_ACTIVE_CONSULTATION_REQUESTS_PER_ACCOUNT
    except Exception as exc:
        print(f"Warning: consultation conflict lookup failed: {exc}")
        return False


async def create_consultation_case(
    payload: ConsultationCasePayload,
    user_id: Optional[str] = None,
    db_client: Optional[Any] = None,
) -> Dict[str, Any]:
    db = db_client or supabase
    active_count = await count_active_consultation_requests(db)
    status = CONSULTATION_STATUS_REQUESTED
    queue_number = None if active_count < MAX_ACTIVE_CONSULTATION_REQUESTS else await next_waiting_queue_number(db)
    now = _now_iso()

    if payload.idempotency_key:
        try:
            res = (
                db.table("consultation_requests")
                .select("*")
                .eq("idempotency_key", payload.idempotency_key)
                .limit(1)
                .execute()
            )
            if res.data:
                return {
                    "case": _normalize_case_row(dict(res.data[0])),
                    "slot_available": res.data[0].get("status") != "waiting_queue",
                    "message": "This consultation case was already submitted.",
                    "duplicate": True,
                }
        except Exception as exc:
            print(f"Warning: consultation case idempotency lookup failed: {exc}")

    case_id = f"case_{uuid4().hex[:12]}"
    user = payload.user
    consultation = payload.consultation
    snapshot = payload.astrology_snapshot.model_dump(mode="json", exclude_none=True)
    if await _has_active_booking_conflict(
        db,
        user_id=user_id,
        email=user.email,
        consultant_id=FOUNDER_CONSULTANT["id"],
        preferred_date=consultation.preferred_date,
        preferred_time=consultation.preferred_time,
    ):
        raise ValueError(f"You can have up to {MAX_ACTIVE_CONSULTATION_REQUESTS_PER_ACCOUNT} active consultation requests at a time.")

    row = {
        "id": case_id,
        "user_id": user_id,
        "consultant_id": FOUNDER_CONSULTANT["id"],
        "source_type": payload.source_type.value,
        "chart_type": payload.chart_type.value,
        "name": user.full_name,
        "phone": user.mobile_number,
        "email": user.email,
        "gender": user.gender,
        "date_of_birth": user.date_of_birth or "",
        "time_of_birth": user.time_of_birth or "",
        "place_of_birth": user.place or "",
        "latitude": user.latitude,
        "longitude": user.longitude,
        "timezone": user.timezone,
        "topic": (
            "Prashna"
            if payload.chart_type.value == "prashna"
            else ("Marriage Match" if payload.chart_type.value == "matchmaking" else "Birth Chart")
        ),
        "question": consultation.question,
        "additional_message": consultation.additional_message,
        "preferred_date": consultation.preferred_date,
        "preferred_time": consultation.preferred_time or "",
        "consultation_mode": consultation.consultation_mode,
        "payment_status": consultation.payment_status or "not_paid",
        "quoted_price": consultation.quoted_price,
        "status": status,
        "queue_number": queue_number,
        "astrology_snapshot": _encode_json(snapshot),
        "astrological_snapshot": json.dumps(snapshot),
        "idempotency_key": payload.idempotency_key,
        "meeting_link": None,
        "scheduled_at": None,
        "admin_notes": None,
        "assigned_astrologer": None,
        "created_at": now,
        "updated_at": now,
    }

    try:
        row = _insert_with_schema_fallback(db, "consultation_requests", row)
    except Exception as exc:
        if "PGRST204" not in str(exc):
            print(f"Error: consultation case insert failed: {exc}")
            raise ValueError(f"Supabase Security Error: {exc}")
        legacy_row = _legacy_consultation_case_row(row, payload, snapshot)
        try:
            legacy_row = _insert_with_schema_fallback(db, "consultation_requests", legacy_row)
            row = _normalize_case_row(legacy_row)
        except Exception as legacy_exc:
            print(f"Error: consultation case legacy insert failed: {legacy_exc}")
            raise ValueError(f"Supabase Security Error: {legacy_exc}")

    return {
        "case": _normalize_case_row(row),
        "slot_available": queue_number is None,
        "message": (
            "Your consultation request has been received. Payment is not collected yet; the consultant will confirm next steps."
            if queue_number is None
            else "Currently, all consultation slots are full. You have been added to the waiting queue."
        ),
        "duplicate": False,
    }


def _legacy_consultation_case_row(row: Dict[str, Any], payload: ConsultationCasePayload, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    source = payload.source_type.value
    chart_type = payload.chart_type.value
    legacy_snapshot = dict(snapshot)
    legacy_snapshot.setdefault("case_contract", {
        "source_type": source,
        "chart_type": chart_type,
        "additional_message": row.get("additional_message"),
        "consultation_mode": row.get("consultation_mode"),
        "preferred_date": row.get("preferred_date"),
        "preferred_time": row.get("preferred_time"),
        "assigned_astrologer": row.get("assigned_astrologer"),
        "idempotency_key": row.get("idempotency_key"),
    })
    return {
        "id": row["id"],
        "user_id": row.get("user_id"),
        "consultant_id": row.get("consultant_id"),
        "name": row.get("name"),
        "phone": row.get("phone"),
        "email": row.get("email"),
        "date_of_birth": row.get("date_of_birth") or "",
        "time_of_birth": row.get("time_of_birth") or "",
        "place_of_birth": row.get("place_of_birth") or "",
        "topic": row.get("topic") or "Other",
        "question": row.get("question") or "",
        "preferred_time": row.get("preferred_time") or "",
        "payment_status": row.get("payment_status") or "not_paid",
        "status": row.get("status") or "pending",
        "queue_number": row.get("queue_number"),
        "meeting_link": row.get("meeting_link"),
        "scheduled_at": row.get("scheduled_at"),
        "admin_notes": row.get("admin_notes"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "astrological_snapshot": json.dumps(legacy_snapshot),
    }


async def get_consultation_case(case_id: str, db_client: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    try:
        db = db_client or supabase
        res = db.table("consultation_requests").select("*").eq("id", case_id).execute()
        if not res.data:
            return None
        return _normalize_case_row(dict(res.data[0]))
    except Exception as exc:
        print(f"Warning: get_consultation_case failed: {exc}")
        return None


async def list_consultation_cases(
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    chart_type: Optional[str] = None,
    user_name: Optional[str] = None,
    case_id: Optional[str] = None,
    created_date: Optional[str] = None,
    db_client: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    try:
        db = db_client or supabase
        query = db.table("consultation_requests").select("*")
        if status:
            query = query.eq("status", status)
        if source_type:
            query = query.eq("source_type", source_type)
        if chart_type:
            query = query.eq("chart_type", chart_type)
        if case_id:
            query = query.eq("id", case_id)
        if user_name:
            query = query.ilike("name", f"%{user_name}%")
        if created_date:
            query = query.gte("created_at", f"{created_date}T00:00:00").lt("created_at", f"{created_date}T23:59:59.999999")
        res = query.order("created_at", desc=True).execute()
        return [_normalize_case_row(dict(row)) for row in (res.data or [])]
    except Exception as exc:
        print(f"Warning: list_consultation_cases failed: {exc}")
        return []


async def update_consultation_case(case_id: str, updates: Dict[str, Any], db_client: Optional[Any] = None) -> Dict[str, Any]:
    db = db_client or supabase
    update_row: Dict[str, Any] = {}
    current = await get_consultation_case(case_id, db)
    if updates.get("case_status") is not None:
        status_value = updates["case_status"]
        next_status = normalize_consultation_status(getattr(status_value, "value", status_value))
        if current:
            assert_consultation_transition(current.get("status"), next_status)
        update_row["status"] = next_status
    for key in ["admin_notes", "assigned_astrologer", "meeting_link", "scheduled_at"]:
        if updates.get(key) is not None:
            update_row[key] = updates[key]
    if updates.get("astrology_snapshot") is not None:
        snapshot = updates["astrology_snapshot"]
        update_row["astrology_snapshot"] = _encode_json(snapshot)
        update_row["astrological_snapshot"] = json.dumps(snapshot)

    update_row["updated_at"] = _now_iso()
    db.table("consultation_requests").update(update_row).eq("id", case_id).execute()

    promoted = None
    if update_row.get("status") in {"completed", "cancelled", "refunded"}:
        promoted = await promote_oldest_waiting_request()

    return {"case": await get_consultation_case(case_id, db), "promoted_case": promoted}


async def count_active_consultation_requests(db_client: Optional[Any] = None) -> int:
    db = db_client or supabase
    try:
        stats_res = db.table("consultant_platform_stats").select("current_queue_size").eq("id", 1).execute()
        if stats_res.data:
            return int(stats_res.data[0].get("current_queue_size") or 0)
    except Exception as exc:
        print(f"Warning: consultation stats count failed: {exc}")

    try:
        res = db.table("consultation_requests").select("id").in_("status", _status_filter_values()).execute()
        return len(res.data or [])
    except Exception as exc:
        print(f"Warning: active consultation request count failed: {exc}")

    try:
        res = db.table("paid_consultations").select("id").in_("status", _status_filter_values()).execute()
        return len(res.data or [])
    except Exception as exc:
        print(f"Warning: active consultation request count failed: {exc}")
        return 0


async def get_public_consultation_queue_status(db_client: Optional[Any] = None) -> Dict[str, Any]:
    db = db_client or supabase
    active_count = await count_active_consultation_requests(db)
    try:
        stats_res = db.table("consultant_platform_stats").select("max_capacity").eq("id", 1).execute()
        max_active = int(stats_res.data[0].get("max_capacity") or MAX_ACTIVE_CONSULTATION_REQUESTS) if stats_res.data else MAX_ACTIVE_CONSULTATION_REQUESTS
    except Exception as exc:
        print(f"Warning: consultation capacity lookup failed: {exc}")
        max_active = MAX_ACTIVE_CONSULTATION_REQUESTS
    return {
        "active_count": active_count,
        "max_active": max_active,
        "available_slots": max(0, max_active - active_count),
        "waiting_count": 0,
        "can_request_active_slot": active_count < max_active,
    }


async def next_waiting_queue_number(db_client: Optional[Any] = None) -> int:
    db = db_client or supabase
    try:
        res = (
            db.table("consultation_requests")
            .select("queue_number")
            .eq("status", "waiting_queue")
            .order("queue_number", desc=True)
            .limit(1)
            .execute()
        )
        if not res.data:
            return 1
        return int(res.data[0].get("queue_number") or 0) + 1
    except Exception as exc:
        print(f"Warning: next_waiting_queue_number failed: {exc}")
        return 1


async def create_consultation_request(
    payload: Dict[str, Any],
    user_id: Optional[str] = None,
    db_client: Optional[Any] = None,
) -> Dict[str, Any]:
    db = db_client or supabase
    active_count = await count_active_consultation_requests(db)
    payment_status = str(payload.get("payment_status") or "not_paid").lower()
    status = CONSULTATION_STATUS_PENDING_PAYMENT if payment_status in {"pending", "created"} else CONSULTATION_STATUS_REQUESTED
    queue_number = None if active_count < MAX_ACTIVE_CONSULTATION_REQUESTS else await next_waiting_queue_number(db)
    now = _now_iso()
    request_id = f"creq_{uuid4().hex[:12]}"
    if await _has_active_booking_conflict(
        db,
        user_id=user_id,
        email=payload.get("email"),
        consultant_id=payload.get("consultant_id") or FOUNDER_CONSULTANT["id"],
        preferred_date=payload.get("preferred_date"),
        preferred_time=payload.get("preferred_time"),
    ):
        raise ValueError(f"You can have up to {MAX_ACTIVE_CONSULTATION_REQUESTS_PER_ACCOUNT} active consultation requests at a time.")

    row = {
        "id": request_id,
        "user_id": user_id,
        "consultant_id": payload.get("consultant_id") or FOUNDER_CONSULTANT["id"],
        "name": payload["name"],
        "phone": payload["phone"],
        "email": payload["email"],
        "date_of_birth": payload["date_of_birth"],
        "time_of_birth": payload["time_of_birth"],
        "place_of_birth": payload["place_of_birth"],
        "topic": payload.get("topic", "Other"),
        "question": payload.get("question", ""),
        "preferred_time": payload.get("preferred_time", ""),
        "payment_status": payment_status,
        "quoted_price": payload.get("quoted_price"),
        "status": status,
        "queue_number": queue_number,
        "astrological_snapshot": payload.get("astrological_snapshot"),
        "meeting_link": None,
        "scheduled_at": None,
        "admin_notes": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        row = _insert_with_schema_fallback(db, "consultation_requests", row)
    except Exception as exc:
        print(f"Error: consultation_requests insert failed: {exc}")
        raise ValueError(f"Supabase Security Error: {exc}")

    if queue_number is not None:
        message = "Currently, all consultation slots are full. You have been added to the waiting queue. You will be notified when your turn comes."
    elif status == CONSULTATION_STATUS_PENDING_PAYMENT:
        message = "Your consultation request has been created. Complete payment to confirm it for astrologer review."
    else:
        message = "Your consultation request has been received. Payment is not collected yet; the consultant will confirm next steps."

    return {
        "request": row,
        "slot_available": queue_number is None,
        "message": message,
    }


async def mark_consultation_request_paid(
    request_id: str,
    *,
    provider: str,
    provider_ref: str,
    payment_id: Optional[str] = None,
    db_client: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    db = db_client or supabase
    current = await get_consultation_request(request_id, db)
    if not current:
        return None

    notes = current.get("admin_notes") or ""
    payment_note = f"Payment verified via {provider}: order={provider_ref}"
    if payment_id:
        payment_note += f", payment={payment_id}"
    if payment_note not in notes:
        notes = (notes + "\n" + payment_note).strip()

    updates = {
        "payment_status": "paid",
        "status": CONSULTATION_STATUS_CONFIRMED,
        "admin_notes": notes,
        "updated_at": _now_iso(),
    }
    try:
        db.table("consultation_requests").update(updates).eq("id", request_id).execute()
    except Exception as exc:
        print(f"Warning: mark_consultation_request_paid failed: {exc}")
        return None
    return await get_consultation_request(request_id, db)


async def list_consultation_requests(status: Optional[str] = None, db_client: Optional[Any] = None) -> List[Dict[str, Any]]:
    try:
        db = db_client or supabase
        query = db.table("consultation_requests").select("*")
        if status:
            query = query.eq("status", status)
        res = query.order("created_at").execute()
        return [_normalize_case_row(dict(row)) for row in (res.data or [])]
    except Exception as exc:
        print(f"Warning: list_consultation_requests failed: {exc}")
        return []


async def get_consultation_request(request_id: str, db_client: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    try:
        db = db_client or supabase
        res = db.table("consultation_requests").select("*").eq("id", request_id).execute()
        if not res.data:
            return None
        return _normalize_case_row(dict(res.data[0]))
    except Exception as exc:
        print(f"Warning: get_consultation_request failed: {exc}")
        return None


async def update_consultation_request(request_id: str, updates: Dict[str, Any], db_client: Optional[Any] = None) -> Dict[str, Any]:
    db = db_client or supabase
    updates = {key: value for key, value in updates.items() if value is not None}
    if "status" in updates:
        current = await get_consultation_request(request_id, db)
        next_status = normalize_consultation_status(updates["status"])
        if current:
            assert_consultation_transition(current.get("status"), next_status)
        updates["status"] = next_status
    updates["updated_at"] = _now_iso()
    db.table("consultation_requests").update(updates).eq("id", request_id).execute()

    promoted = None
    if updates.get("status") in {"completed", "cancelled", "refunded"}:
        promoted = await promote_oldest_waiting_request()

    request = await get_consultation_request(request_id, db)
    return {"request": request, "promoted_request": promoted}


async def promote_oldest_waiting_request() -> Optional[Dict[str, Any]]:
    active_count = await count_active_consultation_requests()
    if active_count >= MAX_ACTIVE_CONSULTATION_REQUESTS:
        return None

    res = (
        supabase.table("consultation_requests")
        .select("*")
        .eq("status", CONSULTATION_STATUS_REQUESTED)
        .order("created_at")
        .limit(25)
        .execute()
    )
    if not res.data:
        return None

    waiting_row = next((row for row in res.data if row.get("queue_number") is not None), None)
    if not waiting_row:
        return None
    waiting = dict(waiting_row)
    updates = {
        "status": CONSULTATION_STATUS_REQUESTED,
        "queue_number": None,
        "updated_at": _now_iso(),
        "admin_notes": ((waiting.get("admin_notes") or "") + "\nAuto moved from waiting queue to pending.").strip(),
    }
    supabase.table("consultation_requests").update(updates).eq("id", waiting["id"]).execute()
    waiting.update(updates)
    waiting["notification_message"] = "Your consultation request is now active. The consultant will review it soon."
    return waiting

async def get_queue_status() -> Dict[str, Any]:
    try:
        if supabase:
            res = supabase.table("consultant_platform_stats").select("current_queue_size, max_capacity").eq("id", 1).execute()
            if res.data:
                return res.data[0]
    except Exception as e:
        print(f"Warning: Supabase get_queue_status failed: {e}")
    return {"current_queue_size": 0, "max_capacity": 20}

async def create_consultation(
    user_id: Optional[str],
    user_name: str, 
    user_email: str, 
    question_text: str, 
    astrological_snapshot: str, 
    payment_ref: str,
    whatsapp_no: str = None,
    gender: str = None,
    birth_date: str = None,
    birth_time: str = None,
    birth_place: str = None
) -> Dict[str, Any]:
    consultation_id = f"cons_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    created_at = now.isoformat()
    sla_deadline = (now + timedelta(hours=24)).isoformat()
    
    try:
        if supabase:
            # Check capacity before inserting
            stats_res = supabase.table("consultant_platform_stats").select("current_queue_size, max_capacity").eq("id", 1).execute()
            current_size = 0
            if stats_res.data:
                stats = stats_res.data[0]
                current_size = stats["current_queue_size"]
                if current_size >= stats["max_capacity"]:
                    raise Exception("Queue is full")
            amount = validate_price_amount(get_settings().consultation_price_inr)

            # Insert consultation
            supabase.table("paid_consultations").insert({
                "id": consultation_id,
                "user_id": user_id,
                "user_name": user_name,
                "user_email": user_email,
                "question_text": question_text,
                "astrological_snapshot": astrological_snapshot,
                "whatsapp_no": whatsapp_no,
                "gender": gender,
                "birth_date": birth_date,
                "birth_time": birth_time,
                "birth_place": birth_place,
                "status": CONSULTATION_STATUS_CONFIRMED,
                "payment_ref": payment_ref,
                "amount": float(amount),
                "currency": "INR",
                "created_at": created_at,
                "sla_deadline": sla_deadline
            }).execute()
            
            # Increment queue
            supabase.table("consultant_platform_stats").update({
                "current_queue_size": current_size + 1
            }).eq("id", 1).execute()
    except Exception as e:
        print(f"Warning: Supabase create_consultation failed: {e}")
        
    return {
        "id": consultation_id,
        "status": CONSULTATION_STATUS_CONFIRMED,
        "created_at": created_at,
        "sla_deadline": sla_deadline
    }


async def update_paid_consultation_snapshot(
    consultation_id: str,
    astrological_snapshot: str,
    db_client: Optional[Any] = None,
) -> bool:
    db = db_client or supabase
    try:
        if db:
            db.table("paid_consultations").update({
                "astrological_snapshot": astrological_snapshot,
            }).eq("id", consultation_id).execute()
            return True
    except Exception as exc:
        print(f"Warning: update_paid_consultation_snapshot failed: {exc}")
    return False

async def get_consultation_queue() -> List[Dict[str, Any]]:
    try:
        if supabase:
            res = supabase.table("paid_consultations").select("*").in_("status", [CONSULTATION_STATUS_CONFIRMED, "QUEUED"]).order("sla_deadline").execute()
            return [dict(row) for row in res.data]
    except Exception as e:
        print(f"Warning: Supabase get_consultation_queue failed: {e}")
    return []

async def answer_consultation(consultation_id: str, answer_text: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    try:
        if supabase:
            # Get consultation
            res = supabase.table("paid_consultations").select("status, amount").eq("id", consultation_id).execute()
            if not res.data or normalize_consultation_status(res.data[0]["status"]) != CONSULTATION_STATUS_CONFIRMED:
                return False
                
            amount = res.data[0]["amount"]
            platform_cut = amount * 0.40
            consultant_cut = amount * 0.60
            
            # Update consultation
            supabase.table("paid_consultations").update({
                "status": "completed",
                "answered_at": now,
                "answer_text": answer_text
            }).eq("id", consultation_id).execute()
            
            # Update stats
            stats_res = supabase.table("consultant_platform_stats").select("*").eq("id", 1).execute()
            if stats_res.data:
                stats = stats_res.data[0]
                supabase.table("consultant_platform_stats").update({
                    "current_queue_size": max(0, stats["current_queue_size"] - 1),
                    "total_platform_earnings": stats["total_platform_earnings"] + platform_cut,
                    "consultant_earnings": stats["consultant_earnings"] + consultant_cut
                }).eq("id", 1).execute()
            return True
    except Exception as e:
        print(f"Warning: Supabase answer_consultation failed: {e}")
    return False

async def decline_consultation(consultation_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    try:
        if supabase:
            res = supabase.table("paid_consultations").select("status").eq("id", consultation_id).execute()
            if not res.data or normalize_consultation_status(res.data[0]["status"]) != CONSULTATION_STATUS_CONFIRMED:
                return False
                
            supabase.table("paid_consultations").update({
                "status": "cancelled",
                "answered_at": now
            }).eq("id", consultation_id).execute()
            
            stats_res = supabase.table("consultant_platform_stats").select("current_queue_size").eq("id", 1).execute()
            if stats_res.data:
                stats = stats_res.data[0]
                supabase.table("consultant_platform_stats").update({
                    "current_queue_size": max(0, stats["current_queue_size"] - 1)
                }).eq("id", 1).execute()
            return True
    except Exception as e:
        print(f"Warning: Supabase decline_consultation failed: {e}")
    return False
