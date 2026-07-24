from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse
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
    db: Any = None,
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
        client = db or supabase
        if client:
            client.table("app_visit_events").insert(event).execute()
    except Exception as exc:
        print(f"Warning: record_visit_event failed: {exc}")
    return {"status": "recorded"}


def admin_metrics(db: Any = None) -> Dict[str, Any]:
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=6)
    month_start = today_start - timedelta(days=29)
    live_cutoff = now - timedelta(minutes=5)

    visit_rows = _select_all("app_visit_events", db=db)
    user_rows = _select_all("users", db=db)
    consultation_rows = _select_all("consultation_requests", db=db)
    paid_rows = _select_all("paid_consultations", db=db)
    match_rows = _select_all("match_requests", db=db)
    community_app_rows = _select_all("community_applications", db=db)
    membership_rows = _select_all("community_memberships", db=db)
    message_rows = _select_all("community_messages", db=db)
    report_rows = _select_all("community_reports", db=db)

    visits = _visit_metrics(today_start, yesterday_start, week_start, live_cutoff, visit_rows)
    growth = _growth_metrics(today_start, week_start, month_start, live_cutoff, visit_rows, user_rows)
    retention = _retention_metrics(today_start, visit_rows, consultation_rows)
    revenue = _revenue_metrics(today_start, week_start, month_start, paid_rows, consultation_rows)
    domains = _domain_metrics(consultation_rows, match_rows)
    matchmaking = _matchmaking_metrics(match_rows, consultation_rows)
    community = _community_metrics(today_start, user_rows, community_app_rows, membership_rows, message_rows, report_rows)
    consultations = _consultation_metrics(today_start, consultation_rows, paid_rows)
    product_usage = _product_usage_metrics(visit_rows, consultation_rows, match_rows)
    acquisition = _acquisition_metrics(visit_rows)
    behavior = _behavior_metrics(visit_rows)
    funnel = _funnel_metrics(visit_rows, user_rows, consultation_rows, paid_rows, match_rows)

    return {
        "generated_at": _iso(now),
        "traffic": visits,
        "acquisition": acquisition,
        "behavior": behavior,
        "funnel": funnel,
        "growth": growth,
        "retention": retention,
        "revenue": revenue,
        "domains": domains,
        "matchmaking": matchmaking,
        "community": community,
        "consultations": consultations,
        "earnings": revenue,
        "product_usage": product_usage,
        "revenue_generated": revenue["total_revenue"],
        "total_signups": growth["total_signups"],
        "dau": growth["daily_active_users"],
        "active_users": growth["live_users"],
        "consultation_applications": consultations["consultant_applications_total"],
        "matchmaking_applications": matchmaking["total_reports"],
        "top_domains": domains["top_domains"],
    }


def _select_all(table: str, columns: str = "*", db: Any = None) -> List[Dict[str, Any]]:
    client = db or supabase
    if not client:
        return []
    try:
        res = client.table(table).select(columns).execute()
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


def _visit_metrics(today_start: datetime, yesterday_start: datetime, week_start: datetime, live_cutoff: datetime, rows: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    rows = rows if rows is not None else _select_all("app_visit_events", "visitor_key, path, created_at")
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
        "daily_visits": _daily_visit_series(rows),
        "top_paths_today": _top_paths(today),
    }


def _daily_visit_series(rows: List[Dict[str, Any]], days: int = 30) -> List[Dict[str, Any]]:
    today = _now().date()
    start = today - timedelta(days=days - 1)
    buckets: Dict[str, Dict[str, Any]] = {
        (start + timedelta(days=offset)).isoformat(): {"date": (start + timedelta(days=offset)).isoformat(), "visits": 0, "unique_visitors": 0, "_visitors": set()}
        for offset in range(days)
    }
    for row in rows:
        dt = _parse_dt(row.get("created_at"))
        if not dt:
            continue
        day = dt.date()
        if day < start or day > today:
            continue
        key = day.isoformat()
        bucket = buckets[key]
        bucket["visits"] += 1
        if row.get("visitor_key"):
            bucket["_visitors"].add(row.get("visitor_key"))
    series = []
    for bucket in buckets.values():
        series.append({
            "date": bucket["date"],
            "visits": bucket["visits"],
            "unique_visitors": len(bucket["_visitors"]),
        })
    return series


def _top_paths(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for row in rows:
        path = row.get("path") or "/"
        counts[path] = counts.get(path, 0) + 1
    return [
        {"path": path, "visits": count}
        for path, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]


def _clean_path(value: Any) -> str:
    path = str(value or "/").strip() or "/"
    if path.startswith("http"):
        parsed = urlparse(path)
        path = parsed.path or "/"
    return path.split("?")[0] or "/"


def _referrer_domain(referrer: Any) -> str:
    text = str(referrer or "").strip()
    if not text:
        return "direct"
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "direct"


def _source_channel(row: Dict[str, Any]) -> str:
    path = str(row.get("path") or "")
    ref = _referrer_domain(row.get("referrer"))
    parsed = urlparse(path if path.startswith("http") else f"https://local{path}")
    query = parse_qs(parsed.query)
    utm_source = (query.get("utm_source") or [""])[0].lower()
    utm_medium = (query.get("utm_medium") or [""])[0].lower()
    source_text = f"{utm_source} {utm_medium} {ref}"
    if ref == "direct" and not utm_source:
        return "direct"
    if any(term in source_text for term in ("google", "bing", "yahoo", "duckduckgo")):
        return "organic/search"
    if any(term in source_text for term in ("instagram", "facebook", "fb", "youtube", "twitter", "x.com", "linkedin", "social")):
        return "social"
    if any(term in source_text for term in ("whatsapp", "telegram", "sms")):
        return "messaging"
    if any(term in source_text for term in ("email", "newsletter")):
        return "email"
    if utm_source or utm_medium:
        return "campaign"
    return "referral"


def _device_type(user_agent: Any) -> str:
    text = str(user_agent or "").lower()
    if any(bot in text for bot in ("bot", "crawler", "spider", "preview")):
        return "bot"
    if any(tablet in text for tablet in ("ipad", "tablet")):
        return "tablet"
    if any(mobile in text for mobile in ("mobile", "iphone", "android")):
        return "mobile"
    return "desktop"


def _top_named_counts(names: List[str], limit: int = 8) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for name in names:
        counts[name or "unknown"] = counts.get(name or "unknown", 0) + 1
    total = sum(counts.values())
    return [
        {"name": name, "count": count, "percentage": _percent(count, total)}
        for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def _acquisition_metrics(visits: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "source_channels": _top_named_counts([_source_channel(row) for row in visits]),
        "referrer_domains": _top_named_counts([_referrer_domain(row.get("referrer")) for row in visits if _referrer_domain(row.get("referrer")) != "direct"]),
        "device_mix": _top_named_counts([_device_type(row.get("user_agent")) for row in visits]),
        "campaign_paths": _top_paths([row for row in visits if "utm_" in str(row.get("path") or "")]),
    }


def _first_touch_rows(visits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    first: Dict[str, Dict[str, Any]] = {}
    for row in sorted(visits, key=lambda item: str(item.get("created_at") or "")):
        identity = _row_identity(row)
        if identity and identity not in first:
            first[identity] = row
    return list(first.values())


def _behavior_metrics(visits: List[Dict[str, Any]]) -> Dict[str, Any]:
    paths = [_clean_path(row.get("path")) for row in visits]
    first_touch = _first_touch_rows(visits)
    visitor_path_counts: Dict[str, int] = {}
    for row in visits:
        identity = _row_identity(row)
        if identity:
            visitor_path_counts[identity] = visitor_path_counts.get(identity, 0) + 1
    single_page_visitors = len([identity for identity, count in visitor_path_counts.items() if count == 1])
    return {
        "top_pages": _top_named_counts(paths, 10),
        "landing_pages": _top_named_counts([_clean_path(row.get("path")) for row in first_touch], 10),
        "single_page_visitors": single_page_visitors,
        "estimated_bounce_rate": _percent(single_page_visitors, len(visitor_path_counts)),
        "avg_events_per_visitor": round((len(visits) / len(visitor_path_counts)), 2) if visitor_path_counts else 0,
    }


def _funnel_metrics(
    visits: List[Dict[str, Any]],
    users: List[Dict[str, Any]],
    consultations: List[Dict[str, Any]],
    paid: List[Dict[str, Any]],
    matches: List[Dict[str, Any]],
) -> Dict[str, Any]:
    visitors = len(_unique_identity(visits))
    signups = len(users)
    consultation_requests = len(consultations)
    paid_events = len(paid) + len([row for row in consultations if str(row.get("payment_status") or "").lower() == "paid"])
    matchmaking_reports = len(matches)
    steps = [
        {"name": "Visitors", "count": visitors, "conversion_from_previous": 100},
        {"name": "Signups", "count": signups, "conversion_from_previous": _percent(signups, visitors)},
        {"name": "Consultation Requests", "count": consultation_requests, "conversion_from_previous": _percent(consultation_requests, signups or visitors)},
        {"name": "Paid Actions", "count": paid_events, "conversion_from_previous": _percent(paid_events, consultation_requests or visitors)},
        {"name": "Matchmaking Reports", "count": matchmaking_reports, "conversion_from_previous": _percent(matchmaking_reports, visitors)},
    ]
    return {
        "steps": steps,
        "visitor_to_signup_rate": _percent(signups, visitors),
        "visitor_to_consultation_rate": _percent(consultation_requests, visitors),
        "visitor_to_paid_rate": _percent(paid_events, visitors),
    }


def _growth_metrics(today_start: datetime, week_start: datetime, month_start: datetime, live_cutoff: datetime, visits: List[Dict[str, Any]], users: List[Dict[str, Any]]) -> Dict[str, Any]:
    today_visits = _since(visits, today_start)
    week_visits = _since(visits, week_start)
    month_visits = _since(visits, month_start)
    live_visits = _since(visits, live_cutoff)
    today_users = _since(users, today_start)
    week_users = _since(users, week_start)
    month_users = _since(users, month_start)
    unique_visitors = _unique_identity(visits)
    returning = _returning_identity_count(visits)

    return {
        "total_visits": len(visits),
        "unique_visitors": len(unique_visitors),
        "signups_today": len(today_users),
        "signups_week": len(week_users),
        "signups_month": len(month_users),
        "total_signups": len(users),
        "signup_conversion_rate": _percent(len(users), len(unique_visitors)),
        "returning_users": returning,
        "daily_active_users": len(_unique_identity(today_visits)),
        "weekly_active_users": len(_unique_identity(week_visits)),
        "monthly_active_users": len(_unique_identity(month_visits)),
        "live_users": len(_unique_identity(live_visits)),
    }


def _retention_metrics(today_start: datetime, visits: List[Dict[str, Any]], consultations: List[Dict[str, Any]]) -> Dict[str, Any]:
    identities_with_consult = {_row_identity(row) for row in consultations if _row_identity(row)}
    came_back_after_consult = 0
    for identity in identities_with_consult:
        request_times = [_parse_dt(row.get("created_at") or row.get("submitted_at")) for row in consultations if _row_identity(row) == identity]
        visit_times = [_parse_dt(row.get("created_at")) for row in visits if _row_identity(row) == identity]
        if any(v and r and v > r for r in request_times for v in visit_times):
            came_back_after_consult += 1

    return {
        "came_back_after_consultation": came_back_after_consult,
        "retention_1_day": _retention_rate(visits, 1),
        "retention_7_day": _retention_rate(visits, 7),
        "retention_30_day": _retention_rate(visits, 30),
        "repeat_consultation_requests": _repeat_identity_count(consultations),
    }


def _revenue_metrics(today_start: datetime, week_start: datetime, month_start: datetime, paid: List[Dict[str, Any]], consultations: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = _sum_amount(paid)
    paid_users = len(_unique_identity(paid))
    completed_paid = [
        row for row in paid
        if str(row.get("status") or "").lower() in {"answered", "completed", "complete"}
    ]
    paid_consultations = [row for row in consultations if str(row.get("payment_status") or "").lower() == "paid"]

    return {
        "total_paid_users": paid_users,
        "total_revenue": total,
        "revenue_today": _sum_amount(_since(paid, today_start)),
        "revenue_week": _sum_amount(_since(paid, week_start)),
        "revenue_month": _sum_amount(_since(paid, month_start)),
        "paid_consultations_count": len(paid) + len(paid_consultations),
        "matchmaking_consultation_bookings": len([row for row in consultations if _source_group(row) == "matchmaking"]),
        "average_revenue_per_user": round(total / paid_users, 2) if paid_users else 0,
        "completed_paid_cases": len(completed_paid) + len([row for row in paid_consultations if str(row.get("status") or "").lower() == "completed"]),
    }


def _domain_metrics(consultations: List[Dict[str, Any]], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    domain_counts: Dict[str, int] = {}
    source_split: Dict[str, Dict[str, int]] = {}
    for row in consultations:
        domain = _detect_domain(row)
        source = _source_group(row)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        source_split.setdefault(source, {})
        source_split[source][domain] = source_split[source].get(domain, 0) + 1
    for row in matches:
        domain = _detect_domain(row)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        source_split.setdefault("matchmaking", {})
        source_split["matchmaking"][domain] = source_split["matchmaking"].get(domain, 0) + 1
    total = sum(domain_counts.values())
    top_domains = [
        {"name": name, "count": count, "percentage": _percent(count, total)}
        for name, count in sorted(domain_counts.items(), key=lambda item: item[1], reverse=True)
    ]
    return {
        "most_asked_domains": top_domains,
        "top_domains": top_domains[:6],
        "domain_split": source_split,
    }


def _matchmaking_metrics(matches: List[Dict[str, Any]], consultations: List[Dict[str, Any]]) -> Dict[str, Any]:
    bookings = len([row for row in consultations if _source_group(row) == "matchmaking"])
    requested = bookings + len([row for row in matches if str(row.get("status") or "").lower() in {"consultation_booked", "accepted", "scheduled", "completed"}])
    return {
        "total_reports": len(matches),
        "consultation_requested": requested,
        "free_report_to_consultation_rate": _percent(requested, len(matches)),
    }


def _community_metrics(
    today_start: datetime,
    user_rows: Optional[List[Dict[str, Any]]] = None,
    application_rows: Optional[List[Dict[str, Any]]] = None,
    membership_rows: Optional[List[Dict[str, Any]]] = None,
    message_rows: Optional[List[Dict[str, Any]]] = None,
    report_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    user_rows = user_rows if user_rows is not None else _select_all("users", "id, role, verification_status, community_access, created_at")
    application_rows = application_rows if application_rows is not None else _select_all("community_applications", "user_id, status, submitted_at")
    membership_rows = membership_rows if membership_rows is not None else _select_all("community_memberships", "user_id, status, approved_at")
    message_rows = message_rows if message_rows is not None else _select_all("community_messages")
    report_rows = report_rows if report_rows is not None else _select_all("community_reports")
    legacy_pending = [row for row in user_rows if row.get("verification_status") == "pending"]
    today_apps = [
        row for row in application_rows
        if (dt := _parse_dt(row.get("submitted_at"))) and dt >= today_start
    ]
    today_messages = _since(message_rows, today_start)

    return {
        "applications_total": len(application_rows) or len([row for row in user_rows if row.get("role") == "astrologer"]),
        "applications_today": len(today_apps),
        "pending_applications": len([row for row in application_rows if row.get("status") in {"SUBMITTED", "UNDER_REVIEW"}]) or len(legacy_pending),
        "approved_members": len([row for row in membership_rows if row.get("status") == "ACTIVE"]) or len([row for row in user_rows if row.get("community_access") is True]),
        "rejected_applications": len([row for row in application_rows if row.get("status") == "REJECTED"]),
        "total_astrologers": len([row for row in user_rows if row.get("role") == "astrologer"]) or len(membership_rows),
        "verified_astrologers": len([row for row in user_rows if row.get("verification_status") in {"verified", "APPROVED", "approved"}]) or len([row for row in membership_rows if row.get("status") == "ACTIVE"]),
        "active_community_users": len(_unique_identity(today_messages)),
        "messages_per_day": len(today_messages),
        "most_active_channels": _top_counts(message_rows, "channel_name", 6),
        "reported_deleted_posts": len(report_rows) + len([row for row in message_rows if row.get("is_deleted") is True or row.get("deleted_at")]),
        "engagement_by_user": _top_counts(message_rows, "sender_id", 6),
    }


def _consultation_metrics(today_start: datetime, public_requests: Optional[List[Dict[str, Any]]] = None, paid: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    public_requests = public_requests if public_requests is not None else _select_all("consultation_requests", "id, status, payment_status, created_at")
    paid = paid if paid is not None else _select_all("paid_consultations", "id, status, amount, created_at, answered_at")
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


def _product_usage_metrics(visits: List[Dict[str, Any]], consultations: List[Dict[str, Any]], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    features = {
        "prashna": _feature_count(visits, consultations, "prashna"),
        "lagna": _feature_count(visits, consultations, "lagna"),
        "matchmaking": len(matches),
        "consultation": len(consultations),
    }
    return {
        "prashna_charts_generated": features["prashna"],
        "lagna_charts_generated": features["lagna"],
        "matchmaking_reports_generated": len(matches),
        "chart_downloads_shares": 0,
        "most_used_features": [{"name": key, "count": value} for key, value in sorted(features.items(), key=lambda item: item[1], reverse=True)],
        "drop_off_points": _top_paths(visits),
        "failed_chart_generations": 0,
        "api_errors_by_feature": [],
    }


def _since(rows: List[Dict[str, Any]], start: datetime) -> List[Dict[str, Any]]:
    return [
        row for row in rows
        if (dt := _parse_dt(row.get("created_at") or row.get("submitted_at") or row.get("approved_at"))) and dt >= start
    ]


def _row_identity(row: Dict[str, Any]) -> Optional[str]:
    return row.get("user_id") or row.get("visitor_key") or row.get("email") or row.get("sender_id")


def _unique_identity(rows: List[Dict[str, Any]]) -> set[str]:
    return {identity for row in rows if (identity := _row_identity(row))}


def _returning_identity_count(rows: List[Dict[str, Any]]) -> int:
    counts: Dict[str, int] = {}
    for row in rows:
        identity = _row_identity(row)
        if identity:
            counts[identity] = counts.get(identity, 0) + 1
    return len([identity for identity, count in counts.items() if count > 1])


def _repeat_identity_count(rows: List[Dict[str, Any]]) -> int:
    return _returning_identity_count(rows)


def _retention_rate(visits: List[Dict[str, Any]], days: int) -> int:
    first_seen: Dict[str, datetime] = {}
    retained: set[str] = set()
    for row in sorted(visits, key=lambda item: str(item.get("created_at") or "")):
        identity = _row_identity(row)
        dt = _parse_dt(row.get("created_at"))
        if not identity or not dt:
            continue
        if identity not in first_seen:
            first_seen[identity] = dt
        elif dt >= first_seen[identity] + timedelta(days=days):
            retained.add(identity)
    return _percent(len(retained), len(first_seen))


def _sum_amount(rows: List[Dict[str, Any]]) -> float:
    total = 0.0
    for row in rows:
        try:
            total += float(row.get("amount") or row.get("price") or row.get("total") or 0)
        except Exception:
            continue
    return round(total, 2)


def _percent(value: int, total: int) -> int:
    return int(round((value / total) * 100)) if total else 0


def _source_group(row: Dict[str, Any]) -> str:
    text = " ".join(str(row.get(key) or "") for key in ("source_type", "chart_type", "type", "category", "question")).lower()
    if "match" in text:
        return "matchmaking"
    if "prashna" in text:
        return "prashna"
    if "lagna" in text or "birth" in text:
        return "lagna"
    return "consultation"


def _detect_domain(row: Dict[str, Any]) -> str:
    text = " ".join(str(row.get(key) or "") for key in ("domain", "topic", "question", "category", "source_type", "chart_type")).lower()
    keyword_map = {
        "marriage": ("marriage", "shaadi", "match", "spouse", "wedding"),
        "career": ("career", "job", "promotion", "work", "profession"),
        "wealth": ("wealth", "money", "finance", "income", "loan"),
        "health": ("health", "disease", "medical", "illness"),
        "education": ("education", "exam", "study", "college", "school"),
        "legal": ("legal", "court", "case", "law"),
        "foreign travel": ("foreign", "travel", "visa", "abroad"),
        "property": ("property", "land", "house", "home"),
        "relationship": ("relationship", "love", "partner", "breakup"),
        "business": ("business", "startup", "company", "trade"),
    }
    for domain, keywords in keyword_map.items():
        if any(keyword in text for keyword in keywords):
            return domain
    return "other"


def _top_counts(rows: List[Dict[str, Any]], key: str, limit: int = 5) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for row in rows:
        name = row.get(key) or "unknown"
        counts[str(name)] = counts.get(str(name), 0) + 1
    return [
        {"name": name, "count": count}
        for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def _feature_count(visits: List[Dict[str, Any]], consultations: List[Dict[str, Any]], keyword: str) -> int:
    visit_count = len([row for row in visits if keyword in str(row.get("path") or "").lower()])
    consultation_count = len([
        row for row in consultations
        if keyword in " ".join(str(row.get(key) or "") for key in ("source_type", "chart_type", "question")).lower()
    ])
    return max(visit_count, consultation_count)
