from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.storage.database import get_service_client


def record_admin_audit(
    *,
    actor_user_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    before_json: Optional[dict[str, Any]] = None,
    after_json: Optional[dict[str, Any]] = None,
    db: Any = None,
) -> None:
    client = db or get_service_client()
    if not client:
        return
    try:
        client.table("admin_logs").insert({
            "actor_user_id": actor_user_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "before_json": before_json,
            "after_json": after_json,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as exc:
        print(f"Warning: admin audit log failed: {exc}")


def list_admin_audit_logs(
    *,
    limit: int = 100,
    entity_type: Optional[str] = None,
    db: Any = None,
) -> list[dict[str, Any]]:
    client = db or get_service_client()
    if not client:
        return []
    query = client.table("admin_logs").select(
        "id, actor_user_id, entity_type, entity_id, action, before_json, after_json, created_at"
    ).order("created_at", desc=True).limit(limit)
    if entity_type:
        query = query.eq("entity_type", entity_type)
    try:
        res = query.execute()
        return res.data or []
    except Exception as exc:
        print(f"Warning: admin audit log fetch failed: {exc}")
        return []
