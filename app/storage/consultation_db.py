import json
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import os

from app.storage.database import supabase

async def init_consultation_db() -> None:
    # Supabase handles schema via SQL migrations
    pass

async def get_queue_status() -> Dict[str, Any]:
    res = supabase.table("consultant_platform_stats").select("current_queue_size, max_capacity").eq("id", 1).execute()
    if res.data:
        return res.data[0]
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
    
    # Check capacity before inserting
    stats_res = supabase.table("consultant_platform_stats").select("current_queue_size, max_capacity").eq("id", 1).execute()
    if stats_res.data:
        stats = stats_res.data[0]
        if stats["current_queue_size"] >= stats["max_capacity"]:
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
    # Supabase doesn't easily support atomic increments, fetch and update
    current_size = stats["current_queue_size"] if stats_res.data else 0
    supabase.table("consultant_platform_stats").update({
        "current_queue_size": current_size + 1
    }).eq("id", 1).execute()
        
    return {
        "id": consultation_id,
        "status": "QUEUED",
        "created_at": created_at,
        "sla_deadline": sla_deadline
    }

async def get_consultation_queue() -> List[Dict[str, Any]]:
    res = supabase.table("paid_consultations").select("*").eq("status", "QUEUED").order("sla_deadline").execute()
    return [dict(row) for row in res.data]

async def answer_consultation(consultation_id: str, answer_text: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    
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

async def decline_consultation(consultation_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    
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
