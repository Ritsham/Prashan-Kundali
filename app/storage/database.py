import json
from typing import Optional
from uuid import uuid4
from supabase import create_client, Client
from app.config import get_settings, is_placeholder_value

settings = get_settings()
SUPABASE_URL = settings.supabase_url
SUPABASE_ANON_KEY = settings.supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY = settings.supabase_service_role_key

def _create_supabase_client(key: str, label: str) -> Optional[Client]:
    if not SUPABASE_URL or not key:
        return None
    if is_placeholder_value("SUPABASE_URL", SUPABASE_URL) or is_placeholder_value(label, key):
        return None
    try:
        return create_client(SUPABASE_URL, key)
    except Exception as e:
        print(f"Warning: Failed to initialize {label} Supabase client: {e}")
        return None


# Default client is anon-scoped so imports do not silently bypass RLS.
supabase = _create_supabase_client(SUPABASE_ANON_KEY, "anon")
service_supabase = _create_supabase_client(SUPABASE_SERVICE_ROLE_KEY, "service-role")


def get_service_client() -> Optional[Client]:
    return service_supabase


def get_public_client() -> Optional[Client]:
    return supabase

def init_db() -> None:
    # No-op since Supabase handles the database schema remotely
    pass

def sync_user(db: Client, user_id: str, email: str, name: str, mobile_number: str = "") -> None:
    from datetime import datetime, timezone
    client = service_supabase or db
    if not client:
        print("Warning: Supabase client is not initialized. Skipping sync_user.")
        return
    clean_name = (name or "").strip()
    clean_mobile = (mobile_number or "").strip()
    data = {
        "id": user_id,
        "email": email,
        "name": clean_name,
        "full_name": clean_name,
        "last_sign_in": datetime.now(timezone.utc).isoformat()
    }
    if clean_mobile:
        data["mobile_number"] = clean_mobile
    try:
        client.table("users").upsert(data).execute()
    except Exception as e:
        print(f"Warning: Supabase sync_user failed: {e}")

def save_prashna_chart(db: Client, chart: dict, user_id: str) -> str:
    chart_id = f"chart_{uuid4().hex[:12]}"
    question = chart["question"]
    data = {
        "id": chart_id,
        "user_id": user_id,
        "name": question["name"],
        "question": question["text"],
        "asked_at_utc": question["asked_at_utc"],
        "place_name": question["place_name"],
        "latitude": question["latitude"],
        "longitude": question["longitude"],
        "chart_json": json.dumps(chart)
    }
    if db:
        try:
            db.table("prashna_charts").insert(data).execute()
        except Exception as e:
            print(f"Warning: Supabase save_prashna_chart failed: {e}")
    return chart_id

def update_prashna_chart(db: Client, chart_id: str, chart: dict) -> None:
    if not db:
        return
    data = {
        "chart_json": json.dumps(chart)
    }
    db.table("prashna_charts").update(data).eq("id", chart_id).execute()

def save_lagna_chart(db: Client, chart: dict, user_id: str) -> str:
    chart_id = f"chart_{uuid4().hex[:12]}"
    meta = chart.get("meta", {})
    # Use question fields since metadata is computed there
    question = chart.get("question", {})
    data = {
        "id": chart_id,
        "user_id": user_id,
        "name": question.get("name", "Unknown"),
        "gender": question.get("gender", "male"),
        "birth_datetime": question.get("asked_at_local", ""),
        "place_name": question.get("place_name", ""),
        "latitude": question.get("latitude", 0.0),
        "longitude": question.get("longitude", 0.0),
        "chart_json": json.dumps(chart)
    }
    if db:
        try:
            db.table("lagna_charts").insert(data).execute()
        except Exception as e:
            print(f"Warning: Supabase save_lagna_chart failed: {e}")
    return chart_id

def get_chart(db: Client, chart_id: str) -> Optional[dict]:
    if not db:
        return None
    try:
        # First, try to query prashna_charts
        res = db.table("prashna_charts").select("id, user_id, chart_json, created_at").eq("id", chart_id).execute()
        if res.data:
            row = res.data[0]
            chart = json.loads(row["chart_json"])
            chart["id"] = row["id"]
            chart["user_id"] = row.get("user_id")
            chart["created_at"] = row["created_at"]
            return chart
        
        # If not found, try to query lagna_charts
        res = db.table("lagna_charts").select("id, user_id, chart_json, created_at").eq("id", chart_id).execute()
        if res.data:
            row = res.data[0]
            chart = json.loads(row["chart_json"])
            chart["id"] = row["id"]
            chart["user_id"] = row.get("user_id")
            chart["created_at"] = row["created_at"]
            return chart
    except Exception as e:
        print(f"Warning: Supabase get_chart failed: {e}")
        
    return None

from app.storage.cache import get_cache, set_cache

def get_geocode_cache(query: str) -> Optional[list[dict]]:
    cache_key = f"geocode:{query.lower()}"
    return get_cache(cache_key)

def save_geocode_cache(query: str, results: list[dict]) -> None:
    cache_key = f"geocode:{query.lower()}"
    set_cache(cache_key, results, expiration_seconds=86400 * 30) # Cache for 30 days

def save_consultant_booking(db: Client, booking: dict, user_id: str) -> str:
    booking_id = f"booking_{uuid4().hex[:12]}"
    data = {
        "id": booking_id,
        "user_id": user_id,
        "consultant_id": booking["consultant_id"],
        "consultant_name": booking["consultant_name"],
        "consultation_type": booking["consultation_type"],
        "client_name": booking["client_name"],
        "client_email": booking["client_email"],
        "client_phone": booking["client_phone"],
        "query_text": booking["query_text"],
        "chart_id": booking.get("chart_id", ""),
        "chart_type": booking.get("chart_type", ""),
        "chart_json": json.dumps(booking.get("chart")) if booking.get("chart") else "",
        "birth_details_json": json.dumps(booking.get("birth_details")) if booking.get("birth_details") else "",
        "status": booking.get("status", "requested")
    }
    if db:
        try:
            db.table("consultant_bookings").insert(data).execute()
        except Exception as e:
            print(f"Warning: Supabase save_consultant_booking failed: {e}")
    return booking_id

def get_consultant_booking(db: Client, booking_id: str) -> Optional[dict]:
    if not db:
        return None
    try:
        res = db.table("consultant_bookings").select("*").eq("id", booking_id).execute()
        if not res.data:
            return None
        row = res.data[0]
        return {
            "id": row["id"],
            "user_id": row.get("user_id"),
            "consultant_id": row["consultant_id"],
            "consultant_name": row["consultant_name"],
            "consultation_type": row["consultation_type"],
            "client_name": row["client_name"],
            "client_email": row["client_email"],
            "client_phone": row["client_phone"],
            "query_text": row["query_text"],
            "chart_id": row["chart_id"],
            "chart_type": row["chart_type"],
            "chart": json.loads(row["chart_json"]) if row["chart_json"] else None,
            "birth_details": json.loads(row["birth_details_json"]) if row["birth_details_json"] else None,
            "status": row["status"],
            "created_at": row["created_at"],
        }
    except Exception as e:
        print(f"Warning: Supabase get_consultant_booking failed: {e}")
    return None

def save_consultant_message(db: Client, message: dict, user_id: str) -> str:
    message_id = f"msg_{uuid4().hex[:12]}"
    data = {
        "id": message_id,
        "booking_id": message["booking_id"],
        "user_id": user_id,
        "sender_role": message["sender_role"],
        "sender_name": message["sender_name"],
        "message_text": message["message_text"]
    }
    if db:
        try:
            db.table("consultant_messages").insert(data).execute()
        except Exception as e:
            print(f"Warning: Supabase save_consultant_message failed: {e}")
    return message_id

def list_consultant_messages(db: Client, booking_id: str) -> list[dict]:
    if not db:
        return []
    try:
        res = db.table("consultant_messages").select("*").eq("booking_id", booking_id).order("created_at", desc=False).execute()
        return [
            {
                "id": row["id"],
                "booking_id": row["booking_id"],
                "sender_role": row["sender_role"],
                "sender_name": row["sender_name"],
                "message_text": row["message_text"],
                "created_at": row["created_at"],
            }
            for row in res.data
        ]
    except Exception as e:
        print(f"Warning: Supabase list_consultant_messages failed: {e}")
    return []
