#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATION="$ROOT/scripts/migrations/006_rls_policy_hardening.sql"
VERIFY_SQL="$ROOT/scripts/verify_rls_policies.sql"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required. Use a Supabase admin/direct Postgres URL; never use the anon key here." >&2
  exit 2
fi

if ! command -v psql >/dev/null 2>&1; then
  python3 "$ROOT/scripts/apply_live_rls_hardening.py"
  python3 "$ROOT/scripts/verify_supabase_anon_denial.py"
  exit 0
fi

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$MIGRATION"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$VERIFY_SQL"
python3 "$ROOT/scripts/verify_supabase_anon_denial.py"
