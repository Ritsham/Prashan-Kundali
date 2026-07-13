from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.storage.database import get_service_client, supabase


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_data(result: Any) -> list[dict[str, Any]]:
    return list(getattr(result, "data", None) or [])


def create_payment_record(
    *,
    user_id: Optional[str],
    amount: float,
    currency: str,
    provider: str,
    provider_ref: str,
    status: str = "created",
    booking_id: Optional[str] = None,
    match_request_id: Optional[str] = None,
    db: Any = None,
) -> dict[str, Any]:
    client = db or supabase
    payment = {
        "id": f"payrec_{uuid4().hex[:12]}",
        "user_id": user_id,
        "booking_id": booking_id,
        "match_request_id": match_request_id,
        "amount": amount,
        "currency": currency,
        "status": status,
        "provider": provider,
        "provider_ref": provider_ref,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    if client:
        client.table("payments").insert(payment).execute()
    return payment


def update_payment_status(
    *,
    provider: str,
    provider_ref: str,
    status: str,
    booking_id: Optional[str] = None,
    db: Any = None,
) -> Optional[dict[str, Any]]:
    client = db or get_service_client()
    if not client:
        return None

    updates: dict[str, Any] = {"status": status, "updated_at": _now_iso()}
    if booking_id:
        updates["booking_id"] = booking_id

    res = (
        client.table("payments")
        .update(updates)
        .eq("provider", provider)
        .eq("provider_ref", provider_ref)
        .execute()
    )
    rows = _safe_data(res)
    return rows[0] if rows else None


def get_payment_by_provider_ref(
    *,
    provider: str,
    provider_ref: str,
    user_id: Optional[str] = None,
    db: Any = None,
) -> Optional[dict[str, Any]]:
    client = db or supabase
    if not client:
        return None
    query = client.table("payments").select("*").eq("provider", provider).eq("provider_ref", provider_ref)
    if user_id:
        query = query.eq("user_id", user_id)
    res = query.limit(1).execute()
    rows = _safe_data(res)
    return rows[0] if rows else None


def is_verified_payment(
    *,
    provider: str,
    provider_ref: str,
    user_id: str,
    db: Any = None,
) -> bool:
    payment = get_payment_by_provider_ref(
        provider=provider,
        provider_ref=provider_ref,
        user_id=user_id,
        db=db,
    )
    return bool(payment and str(payment.get("status") or "").lower() in {"paid", "captured", "authorized"})
