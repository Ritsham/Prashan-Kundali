import json
import sqlite3
from pathlib import Path
from typing import Optional
from uuid import uuid4

DB_PATH = Path("kundali.db")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prashna_charts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                question TEXT NOT NULL,
                asked_at_utc TEXT NOT NULL,
                place_name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                chart_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS geocode_cache (
                query TEXT PRIMARY KEY,
                results_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_chart(chart: dict) -> str:
    chart_id = f"chart_{uuid4().hex[:12]}"
    question = chart["question"]
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO prashna_charts
            (id, name, question, asked_at_utc, place_name, latitude, longitude, chart_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chart_id,
                question["name"],
                question["text"],
                question["asked_at_utc"],
                question["place_name"],
                question["latitude"],
                question["longitude"],
                json.dumps(chart),
            ),
        )
    return chart_id


def get_chart(chart_id: str) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, chart_json, created_at FROM prashna_charts WHERE id = ?",
            (chart_id,),
        ).fetchone()
    if not row:
        return None
    chart = json.loads(row["chart_json"])
    chart["id"] = row["id"]
    chart["created_at"] = row["created_at"]
    return chart


def get_geocode_cache(query: str) -> Optional[list[dict]]:
    with connect() as conn:
        row = conn.execute(
            "SELECT results_json FROM geocode_cache WHERE query = ?",
            (query,),
        ).fetchone()
    if not row:
        return None
    return json.loads(row["results_json"])


def save_geocode_cache(query: str, results: list[dict]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO geocode_cache (query, results_json)
            VALUES (?, ?)
            ON CONFLICT(query) DO UPDATE SET
                results_json = excluded.results_json,
                created_at = CURRENT_TIMESTAMP
            """,
            (query, json.dumps(results)),
        )
