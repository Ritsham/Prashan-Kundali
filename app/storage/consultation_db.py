import json
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import os

from app.storage.database import supabase

ACTIVE_CONSULTATION_STATUSES = ["pending", "accepted", "in_progress"]
MAX_ACTIVE_CONSULTATION_REQUESTS = 20

FOUNDER_CONSULTANT = {
    "id": "founder-rupesh-kumar",
    "name": "Rupesh Kumar",
    "title": "Founder Astrologer / Primary Consultant",
    "photo_url": "https://www.shanitemple.com/index_images/astrology-puja/janamkundli.png",
    "bio": "Founder astrologer at Prashna Astro, focused on practical guidance through Birth Chart, Prashna Kundali, prediction analysis, and case-based consultation.",
    "experience": "3+ years",
    "systems": ["Vedic Astrology", "Prashna Kundali", "Lagna Kundali", "KP-oriented analysis"],
    "languages": ["Hindi", "English"],
    "consultation_type": "Birth Chart, Prashna, Career, Marriage, Business, Health, and personal guidance",
    "consultation_fee": None,
    "is_active": True,
}

async def init_consultation_db() -> None:
    # Supabase handles schema via SQL migrations
    pass


async def get_founder_consultant() -> Dict[str, Any]:
    return FOUNDER_CONSULTANT


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def count_active_consultation_requests() -> int:
    try:
        res = supabase.table("consultation_requests").select("id").in_("status", ACTIVE_CONSULTATION_STATUSES).execute()
        return len(res.data or [])
    except Exception as exc:
        print(f"Warning: active consultation request count failed: {exc}")
        return 0


async def get_public_consultation_queue_status() -> Dict[str, Any]:
    active_count = await count_active_consultation_requests()
    try:
        waiting_res = supabase.table("consultation_requests").select("id").eq("status", "waiting_queue").execute()
        waiting_count = len(waiting_res.data or [])
    except Exception as exc:
        print(f"Warning: waiting consultation request count failed: {exc}")
        waiting_count = 0
    return {
        "active_count": active_count,
        "max_active": MAX_ACTIVE_CONSULTATION_REQUESTS,
        "available_slots": max(0, MAX_ACTIVE_CONSULTATION_REQUESTS - active_count),
        "waiting_count": waiting_count,
        "can_request_active_slot": active_count < MAX_ACTIVE_CONSULTATION_REQUESTS,
    }


async def next_waiting_queue_number() -> int:
    res = (
        supabase.table("consultation_requests")
        .select("queue_number")
        .eq("status", "waiting_queue")
        .order("queue_number", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return 1
    return int(res.data[0].get("queue_number") or 0) + 1


async def create_consultation_request(payload: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    active_count = await count_active_consultation_requests()
    status = "pending" if active_count < MAX_ACTIVE_CONSULTATION_REQUESTS else "waiting_queue"
    queue_number = None if status == "pending" else await next_waiting_queue_number()
    now = _now_iso()
    request_id = f"creq_{uuid4().hex[:12]}"

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
        "topic": payload["topic"],
        "question": payload["question"],
        "preferred_time": payload.get("preferred_time"),
        "payment_status": payload.get("payment_status") or "not_paid",
        "status": status,
        "queue_number": queue_number,
        "meeting_link": None,
        "scheduled_at": None,
        "admin_notes": None,
        "created_at": now,
        "updated_at": now,
    }
    supabase.table("consultation_requests").insert(row).execute()

    return {
        "request": row,
        "slot_available": status == "pending",
        "message": (
            "Your consultation request has been received. The consultant will review it soon."
            if status == "pending"
            else "Currently, all consultation slots are full. You have been added to the waiting queue. You will be notified when your turn comes."
        ),
    }


async def list_consultation_requests(status: Optional[str] = None) -> List[Dict[str, Any]]:
    query = supabase.table("consultation_requests").select("*")
    if status:
        query = query.eq("status", status)
    res = query.order("created_at").execute()
    return [dict(row) for row in (res.data or [])]


async def get_consultation_request(request_id: str) -> Optional[Dict[str, Any]]:
    res = supabase.table("consultation_requests").select("*").eq("id", request_id).execute()
    if not res.data:
        return None
    return dict(res.data[0])


async def update_consultation_request(request_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    updates = {key: value for key, value in updates.items() if value is not None}
    updates["updated_at"] = _now_iso()
    supabase.table("consultation_requests").update(updates).eq("id", request_id).execute()

    promoted = None
    if updates.get("status") in {"completed", "rejected", "cancelled"}:
        promoted = await promote_oldest_waiting_request()

    request = await get_consultation_request(request_id)
    return {"request": request, "promoted_request": promoted}


async def promote_oldest_waiting_request() -> Optional[Dict[str, Any]]:
    active_count = await count_active_consultation_requests()
    if active_count >= MAX_ACTIVE_CONSULTATION_REQUESTS:
        return None

    res = (
        supabase.table("consultation_requests")
        .select("*")
        .eq("status", "waiting_queue")
        .order("created_at")
        .limit(1)
        .execute()
    )
    if not res.data:
        return None

    waiting = dict(res.data[0])
    updates = {
        "status": "pending",
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

            # Insert consultation
            supabase.table("paid_consultations").insert({
                "id": consultation_id,
                "user_name": user_name,
                "user_email": user_email,
                "question_text": question_text,
                "astrological_snapshot": astrological_snapshot,
                "whatsapp_no": whatsapp_no,
                "gender": gender,
                "birth_date": birth_date,
                "birth_time": birth_time,
                "birth_place": birth_place,
                "status": "QUEUED",
                "payment_ref": payment_ref,
                "amount": 299.0,
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
        "status": "QUEUED",
        "created_at": created_at,
        "sla_deadline": sla_deadline
    }

async def get_consultation_queue() -> List[Dict[str, Any]]:
    try:
        if supabase:
            res = supabase.table("paid_consultations").select("*").eq("status", "QUEUED").order("sla_deadline").execute()
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
            if not res.data or res.data[0]["status"] != 'QUEUED':
                return False
                
            amount = res.data[0]["amount"]
            platform_cut = amount * 0.40
            consultant_cut = amount * 0.60
            
            # Update consultation
            supabase.table("paid_consultations").update({
                "status": "ANSWERED",
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
            if not res.data or res.data[0]["status"] != 'QUEUED':
                return False
                
            supabase.table("paid_consultations").update({
                "status": "DECLINED",
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
