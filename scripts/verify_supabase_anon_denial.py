from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_TABLES = [
    "users",
    "prashna_charts",
    "lagna_charts",
    "consultation_requests",
    "paid_consultations",
    "payments",
    "community_applications",
    "community_messages",
]


def _load_env() -> dict[str, str]:
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    return {key: str(value) for key, value in values.items() if value is not None}


def _request_status(url: str, anon_key: str) -> int:
    req = Request(
        url,
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=12) as response:
            response.read(512)
            return response.status
    except HTTPError as exc:
        return exc.code
    except URLError as exc:
        raise RuntimeError(f"Supabase network check failed: {exc.reason}") from exc


def main() -> None:
    env = _load_env()
    supabase_url = (env.get("SUPABASE_URL") or "").rstrip("/")
    anon_key = env.get("SUPABASE_ANON_KEY") or ""
    if not supabase_url or not anon_key:
        raise AssertionError("SUPABASE_URL and SUPABASE_ANON_KEY are required for anon denial verification")

    exposed: list[str] = []
    for table in SENSITIVE_TABLES:
        status = _request_status(f"{supabase_url}/rest/v1/{table}?select=*&limit=1", anon_key)
        if status == 200:
            exposed.append(table)
        elif status in {401, 403, 404}:
            continue
        else:
            raise AssertionError(f"unexpected Supabase table status: {table}:{status}")

    if exposed:
        raise AssertionError(f"anonymous REST access exposed sensitive tables: {', '.join(exposed)}")

    print("supabase_anon_denial_ok")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
