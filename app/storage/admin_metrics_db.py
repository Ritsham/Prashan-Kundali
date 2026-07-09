from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.storage.database import supabase


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def record_visit_event(
    visitor_key: str,
    path: str,
    referrer: str = "",
    user_agent: str = "",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    event = {
        "id": f"visit_{uuid4().hex[:12]}",
        "visitor_key": visitor_key[:160],
        "user_id": user_id,
        "path": path[:500],
        "referrer": referrer[:500],
        "user_agent": user_agent[:500],
        "created_at": _iso(_now()),
    }
    try:
        if supabase:
            supabase.table("app_visit_events").insert(event).execute()
    except Exception as exc:
        print(f"Warning: record_visit_event failed: {exc}")
    return {"status": "recorded"}


def admin_metrics() -> Dict[str, Any]:
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=6)
    live_cutoff = now - timedelta(minutes=5)

    visits = _visit_metrics(today_start, yesterday_start, week_start, live_cutoff)
    community = _community_metrics(today_start)
    consultations = _consultation_metrics(today_start)
    earnings = _earnings_metrics(today_start)

    return {
        "generated_at": _iso(now),
        "traffic": visits,
        "community": community,
        "consultations": consultations,
        "earnings": earnings,
    }


def _select_all(table: str, columns: str = "*") -> List[Dict[str, Any]]:
    if not supabase:
        return []
    try:
        res = supabase.table(table).select(columns).execute()
        return [dict(row) for row in (res.data or [])]
    except Exception as exc:
        print(f"Warning: metrics select failed for {table}: {exc}")
        return []


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _unique_count(rows: List[Dict[str, Any]], key: str) -> int:
    return len({row.get(key) for row in rows if row.get(key)})


def _visit_metrics(today_start: datetime, yesterday_start: datetime, week_start: datetime, live_cutoff: datetime) -> Dict[str, Any]:
    rows = _select_all("app_visit_events", "visitor_key, path, created_at")
    with_dt = [(row, _parse_dt(row.get("created_at"))) for row in rows]
    today = [row for row, dt in with_dt if dt and dt >= today_start]
    yesterday = [row for row, dt in with_dt if dt and yesterday_start <= dt < today_start]
    week = [row for row, dt in with_dt if dt and dt >= week_start]
    live = [row for row, dt in with_dt if dt and dt >= live_cutoff]

    return {
        "visits_today": len(today),
        "visits_yesterday": len(yesterday),
        "visits_7d": len(week),
        "dau": _unique_count(today, "visitor_key"),
        "live_users": _unique_count(live, "visitor_key"),
        "top_paths_today": _top_paths(today),
    }


def _top_paths(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for row in rows:
        path = row.get("path") or "/"
        counts[path] = counts.get(path, 0) + 1
    return [
        {"path": path, "visits": count}
        for path, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]


def _community_metrics(today_start: datetime) -> Dict[str, Any]:
    user_rows = _select_all("users", "id, role, verification_status, community_access, created_at")
    application_rows = _select_all("community_applications", "user_id, status, submitted_at")
    membership_rows = _select_all("community_memberships", "user_id, status, approved_at")
    legacy_pending = [row for row in user_rows if row.get("verification_status") == "pending"]
    today_apps = [
        row for row in application_rows
        if (dt := _parse_dt(row.get("submitted_at"))) and dt >= today_start
    ]

    return {
        "applications_total": len(application_rows) or len([row for row in user_rows if row.get("role") == "astrologer"]),
        "applications_today": len(today_apps),
        "pending_applications": len([row for row in application_rows if row.get("status") in {"SUBMITTED", "UNDER_REVIEW"}]) or len(legacy_pending),
        "approved_members": len([row for row in membership_rows if row.get("status") == "ACTIVE"]) or len([row for row in user_rows if row.get("community_access") is True]),
        "rejected_applications": len([row for row in application_rows if row.get("status") == "REJECTED"]),
    }


def _consultation_metrics(today_start: datetime) -> Dict[str, Any]:
    public_requests = _select_all("consultation_requests", "id, status, payment_status, created_at")
    paid = _select_all("paid_consultations", "id, status, amount, created_at, answered_at")
    today_public = [
        row for row in public_requests
        if (dt := _parse_dt(row.get("created_at"))) and dt >= today_start
    ]
    today_paid = [
        row for row in paid
        if (dt := _parse_dt(row.get("created_at"))) and dt >= today_start
    ]

    return {
        "consultant_applications_total": len(public_requests),
        "consultant_applications_today": len(today_public),
        "consultant_applications_pending": len([row for row in public_requests if row.get("status") in {"pending", "waiting_queue", "accepted", "in_progress"}]),
        "paid_consultations_total": len(paid),
        "paid_consultations_today": len(today_paid),
        "paid_consultations_queued": len([row for row in paid if row.get("status") == "QUEUED"]),
        "paid_consultations_answered": len([row for row in paid if row.get("status") == "ANSWERED"]),
    }


def _earnings_metrics(today_start: datetime) -> Dict[str, Any]:
    paid = _select_all("paid_consultations", "status, amount, created_at")
    stats = _select_all("consultant_platform_stats", "total_platform_earnings, consultant_earnings")
    paid_total = sum(float(row.get("amount") or 0) for row in paid)
    paid_today = sum(
        float(row.get("amount") or 0)
        for row in paid
        if (dt := _parse_dt(row.get("created_at"))) and dt >= today_start
    )
    platform_earnings = paid_total * 0.4
    consultant_earnings = paid_total * 0.6
    if stats:
        platform_earnings = float(stats[0].get("total_platform_earnings") or platform_earnings)
        consultant_earnings = float(stats[0].get("consultant_earnings") or consultant_earnings)

    return {
        "gross_revenue_total": paid_total,
        "gross_revenue_today": paid_today,
        "platform_earnings_total": platform_earnings,
        "consultant_earnings_total": consultant_earnings,
    }
