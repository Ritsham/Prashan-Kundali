from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any


_lock = threading.Lock()
_started_at = time.time()
_routes: dict[str, dict[str, Any]] = defaultdict(
    lambda: {
        "count": 0,
        "errors": 0,
        "total_ms": 0.0,
        "max_ms": 0.0,
        "recent_ms": deque(maxlen=200),
    }
)


def record_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    route_key = f"{method.upper()} {path}"
    with _lock:
        item = _routes[route_key]
        item["count"] += 1
        if status_code >= 500:
            item["errors"] += 1
        item["total_ms"] += duration_ms
        item["max_ms"] = max(item["max_ms"], duration_ms)
        item["recent_ms"].append(duration_ms)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((percentile / 100) * (len(ordered) - 1))))
    return round(ordered[index], 2)


def metrics_snapshot() -> dict[str, Any]:
    with _lock:
        routes = {}
        for route, item in _routes.items():
            recent = list(item["recent_ms"])
            count = item["count"]
            routes[route] = {
                "count": count,
                "errors": item["errors"],
                "avg_ms": round(item["total_ms"] / count, 2) if count else 0.0,
                "p95_recent_ms": _percentile(recent, 95),
                "max_ms": round(item["max_ms"], 2),
            }
    return {
        "uptime_seconds": round(time.time() - _started_at, 2),
        "routes": routes,
    }
