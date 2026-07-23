from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "scripts" / "migrations" / "006_rls_policy_hardening.sql"
GRANT_HARDENING = ROOT / "scripts" / "migrations" / "007_revoke_anon_sensitive_table_grants.sql"
VERIFY_SQL = ROOT / "scripts" / "verify_rls_policies.sql"


def _connect():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    try:
        import psycopg2

        parsed = urlparse(database_url)
        if parsed.scheme.startswith("postgres") and parsed.hostname:
            return psycopg2.connect(
                dbname=(parsed.path or "/postgres").lstrip("/") or "postgres",
                user=unquote(parsed.username or ""),
                password=unquote(parsed.password or ""),
                host=parsed.hostname,
                port=parsed.port or 5432,
                sslmode="require",
            )
        return psycopg2.connect(database_url, sslmode="require")
    except Exception as exc:
        raise RuntimeError("Could not connect to the Supabase Postgres database") from exc


def _run_sql_file(conn, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)


def main() -> None:
    with _connect() as conn:
        _run_sql_file(conn, MIGRATION)
        _run_sql_file(conn, GRANT_HARDENING)
        conn.commit()
        _run_sql_file(conn, VERIFY_SQL)
        conn.commit()
    print("live_rls_hardening_applied")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
