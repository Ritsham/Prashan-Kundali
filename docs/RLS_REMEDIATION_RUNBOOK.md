# Live Supabase RLS Remediation

The live anon check currently fails if sensitive REST tables return `200` to the public anon key.

## Apply

Use an admin/direct Supabase Postgres connection string. Do not use the anon key.

```bash
export DATABASE_URL='postgresql://...'
bash scripts/apply_live_rls_hardening.sh
```

The script applies `scripts/migrations/006_rls_policy_hardening.sql`, runs `scripts/verify_rls_policies.sql`, and then probes the live REST API with `scripts/verify_supabase_anon_denial.py`.

## Manual Supabase SQL Editor Path

1. Open the Supabase project SQL editor.
2. Run `scripts/migrations/006_rls_policy_hardening.sql`.
3. Run `scripts/verify_rls_policies.sql`.
4. From this repo, run:

```bash
python3 scripts/verify_supabase_anon_denial.py
```

Production is not ready until the anon-denial script prints `supabase_anon_denial_ok`.
