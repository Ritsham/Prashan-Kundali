from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx

from app.config import get_settings
from app.insight_engine import build_interpretation
from app.services.chart_calculator import calculate_prashna_chart
from app.services.timezone_service import timezone_at


class AstrologyEngineHTTPError(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _should_use_local_engine(astrology_url: str) -> bool:
    host = (urlparse(astrology_url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0"}


def _resolve_asked_at_utc(payload: dict) -> datetime:
    if payload.get("chart_type") == "lagna":
        location = payload["location"]
        tz_name = timezone_at(float(location["latitude"]), float(location["longitude"]))
        local_dt = datetime.fromisoformat(payload["birth_datetime_local"])
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_name))
        return local_dt.astimezone(timezone.utc)

    if payload.get("asked_at_utc"):
        return datetime.fromisoformat(payload["asked_at_utc"]).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


async def _calculate_locally(payload: dict) -> dict:
    location = payload["location"]
    asked_at_utc = _resolve_asked_at_utc(payload)
    chart = await calculate_prashna_chart(
        question=payload.get("question", ""),
        name=payload["name"],
        asked_at_utc=asked_at_utc,
        latitude=float(location["latitude"]),
        longitude=float(location["longitude"]),
        place_name=location["place_name"],
        chart_type=payload.get("chart_type", "prashna"),
        gender=payload.get("gender") or "",
        question_domain=payload.get("question_domain", ""),
        question_subdomain=payload.get("question_subdomain", ""),
    )
    interpretation = build_interpretation(chart)
    if interpretation:
        chart["interpretation"] = interpretation
    return {"chart": chart, "interpretation": interpretation}


async def calculate_chart(payload: dict, *, timeout: float = 30.0) -> dict:
    astrology_url = get_settings().astrology_engine_url
    if _should_use_local_engine(astrology_url):
        return await _calculate_locally(payload)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{astrology_url}/calculate", json=payload, timeout=timeout)
    except httpx.RequestError:
        return await _calculate_locally(payload)

    if resp.status_code == 200:
        result = resp.json()
        chart = result["chart"]
        interpretation = result.get("interpretation") or chart.get("interpretation")
        if not interpretation:
            interpretation = build_interpretation(chart)
        if interpretation:
            chart["interpretation"] = interpretation
        return {"chart": chart, "interpretation": interpretation}

    try:
        detail = resp.json().get("detail", "Failed to calculate chart")
    except Exception:
        detail = resp.text or "Failed to calculate chart"
    raise AstrologyEngineHTTPError(resp.status_code, detail)
