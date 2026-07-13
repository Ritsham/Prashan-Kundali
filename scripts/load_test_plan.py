#!/usr/bin/env python3
"""
Small standard-library load-test harness for pre-launch checks.

It is intentionally dependency-free and does not run unless invoked manually.

Examples:
  BASE_URL=http://localhost:8000 python3 scripts/load_test_plan.py health --users 50 --requests 500
  BASE_URL=http://localhost:8000 TOKEN=... python3 scripts/load_test_plan.py geocode --users 50 --requests 500

Use paid/external-provider scenarios only against staging with test keys.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.getenv("TOKEN", "")


@dataclass
class Result:
    ok: bool
    status: int
    elapsed_ms: float
    error: str = ""


def request(method: str, path: str, body: dict | None = None, auth: bool = False) -> Result:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if auth and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
            elapsed = (time.perf_counter() - started) * 1000
            return Result(200 <= resp.status < 400, resp.status, elapsed)
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - started) * 1000
        return Result(False, exc.code, elapsed, str(exc))
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        return Result(False, 0, elapsed, str(exc))


def scenario_health() -> Result:
    return request("GET", "/health")


def scenario_geocode() -> Result:
    query = urllib.parse.urlencode({"query": "Delhi", "limit": "3"})
    return request("GET", f"/api/geocode?{query}", auth=bool(TOKEN))


SCENARIOS = {
    "health": scenario_health,
    "geocode": scenario_geocode,
}


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1)))
    return ordered[idx]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--users", type=int, default=25)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()

    fn = SCENARIOS[args.scenario]
    started = time.perf_counter()
    results: list[Result] = []
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        futures = [pool.submit(fn) for _ in range(args.requests)]
        for future in as_completed(futures):
            results.append(future.result())

    elapsed_s = time.perf_counter() - started
    latencies = [r.elapsed_ms for r in results]
    ok = [r for r in results if r.ok]
    errors = [r for r in results if not r.ok]
    status_counts: dict[int, int] = {}
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1

    print(json.dumps({
        "base_url": BASE_URL,
        "scenario": args.scenario,
        "requests": len(results),
        "users": args.users,
        "duration_seconds": round(elapsed_s, 2),
        "requests_per_second": round(len(results) / elapsed_s, 2) if elapsed_s else 0,
        "success_count": len(ok),
        "error_count": len(errors),
        "status_counts": status_counts,
        "avg_ms": round(statistics.mean(latencies), 2) if latencies else 0,
        "p50_ms": round(percentile(latencies, 50), 2),
        "p95_ms": round(percentile(latencies, 95), 2),
        "p99_ms": round(percentile(latencies, 99), 2),
        "max_ms": round(max(latencies), 2) if latencies else 0,
        "sample_errors": [e.error for e in errors[:5]],
    }, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
