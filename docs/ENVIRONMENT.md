# Shree Lakshmi Astro Environment Setup

Shree Lakshmi Astro uses strict backend startup validation when `APP_ENV=production`.
Local defaults exist only for development.

## Environments

Use one of:

- `APP_ENV=development` for local machines.
- `APP_ENV=staging` for pre-production deployments.
- `APP_ENV=production` for live customer traffic.

Production rejects localhost service URLs, wildcard CORS, placeholder secrets, mock admin tokens, and legacy unauthenticated WebSockets.

## Backend Variables

Required in production:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `CORS_ORIGINS`
- `PUBLIC_SITE_URL`
- `REDIS_URL`
- `ASTROLOGY_ENGINE_URL`
- `LLM_ENGINE_URL`
- At least one real LLM provider key unless `REQUIRE_LLM_IN_PRODUCTION=false`

Payment variables are required when `ENABLE_RAZORPAY=true` or `REQUIRE_VERIFIED_PAYMENT=true`:

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET` in production

Consultant contact values shown after verified payment:

- `FOUNDER_CONSULTANT_PHONE`
- `FOUNDER_CONSULTANT_WHATSAPP`

Backend-only secrets:

- `SUPABASE_SERVICE_ROLE_KEY`
- LLM provider keys
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- Redis credentials, database URLs, webhook tokens, and any future provider secrets

## Frontend Variables

The frontend may only use public `VITE_` values:

- `VITE_API_URL`, optional for split frontend/API hosting
- `VITE_SUPABASE_URL`, optional public Supabase URL
- `VITE_SUPABASE_ANON_KEY`, optional public Supabase anon key

If Supabase `VITE_` values are omitted, the app loads public Supabase config from `/api/config`.
Do not add service-role, LLM, payment, database, or webhook secrets to frontend env files.

## CORS

Set exact browser origins:

```ini
CORS_ORIGINS=https://app.example.com,https://staging.example.com
```

Do not use `*` in production. Do not include paths, trailing slashes, or localhost origins in production.

## Local Development

Backend:

```bash
cp .env.example .env
python3 -m pip install -r requirements.txt
python3 scripts/download_ephemeris.py
python3 main.py
```

Frontend:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

For same-origin local backend testing, leave `VITE_API_URL` empty. For Vite dev server calling FastAPI directly, set:

```ini
VITE_API_URL=http://127.0.0.1:8000
```

## Production Checklist

- Set `APP_ENV=production`.
- Use deployed HTTPS frontend origins in `CORS_ORIGINS`.
- Set `PUBLIC_SITE_URL` to the deployed customer-facing frontend URL.
- Point `REDIS_URL`, `ASTROLOGY_ENGINE_URL`, and `LLM_ENGINE_URL` to production/private infrastructure.
- Disable `ALLOW_MOCK_ADMIN_TOKEN`.
- Disable `ENABLE_LEGACY_UNAUTHENTICATED_WS`.
- Set `CONSULTATION_PRICE_INR` to the intended production consultation price before enabling verified payments.
- Rotate any keys that were ever committed, logged, pasted into frontend env files, or shared outside the secret manager.
- Verify Supabase RLS policies before exposing admin/community/consultation features.
