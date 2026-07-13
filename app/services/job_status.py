from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.storage.cache import get_cache, set_cache


JOB_TTL_SECONDS = 60 * 60 * 24
_memory_jobs: dict[str, dict[str, Any]] = {}
_memory_counters: dict[str, int] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


def create_job(kind: str, user_id: str, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    job_id = f"job_{uuid4().hex[:16]}"
    job = {
        "job_id": job_id,
        "kind": kind,
        "user_id": user_id,
        "status": "queued",
        "progress": 0,
        "message": "Queued",
        "metadata": metadata or {},
        "chart_id": None,
        "error": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    save_job(job)
    return job


def save_job(job: dict[str, Any]) -> dict[str, Any]:
    job["updated_at"] = _now_iso()
    _memory_jobs[job["job_id"]] = job
    set_cache(_job_key(job["job_id"]), job, expiration_seconds=JOB_TTL_SECONDS)
    return job


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    job = get_cache(_job_key(job_id))
    if isinstance(job, dict):
        return job
    return _memory_jobs.get(job_id)


def update_job(job_id: str, **updates: Any) -> Optional[dict[str, Any]]:
    job = get_job(job_id)
    if not job:
        return None
    job.update(updates)
    return save_job(job)


def increment_job_metric(name: str, amount: int = 1) -> int:
    key = f"job_metric:{name}"
    try:
        from app.storage.cache import redis_client
        if redis_client:
            return int(redis_client.incrby(key, amount))
    except Exception:
        pass
    _memory_counters[name] = _memory_counters.get(name, 0) + amount
    return _memory_counters[name]


def job_metrics_snapshot() -> dict[str, int]:
    names = [
        "prashna_done",
        "prashna_failed",
        "matchmaking_done",
        "matchmaking_failed",
        "consultation_snapshot_done",
        "consultation_snapshot_failed",
        "paid_snapshot_done",
        "paid_snapshot_failed",
    ]
    snapshot: dict[str, int] = {}
    for name in names:
        key = f"job_metric:{name}"
        try:
            from app.storage.cache import redis_client
            if redis_client:
                value = redis_client.get(key)
                snapshot[name] = int(value or 0)
                continue
        except Exception:
            pass
        snapshot[name] = int(_memory_counters.get(name, 0))
    return snapshot
