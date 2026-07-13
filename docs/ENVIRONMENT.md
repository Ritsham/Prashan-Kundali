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

## Frontend Configuration

The frontend is served from `frontend_old/` by FastAPI in both local development and production.

The browser loads public Supabase config from `/api/config`. Do not add service-role, LLM, payment, database, or webhook secrets to browser-side files.

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
open http://127.0.0.1:8000/index.html
```

## Production Checklist

- Set `APP_ENV=production`.
- Use deployed HTTPS site origins in `CORS_ORIGINS`.
- Set `PUBLIC_SITE_URL` to the deployed customer-facing frontend URL.
- Point `REDIS_URL`, `ASTROLOGY_ENGINE_URL`, and `LLM_ENGINE_URL` to production/private infrastructure.
- Disable `ALLOW_MOCK_ADMIN_TOKEN`.
- Disable `ENABLE_LEGACY_UNAUTHENTICATED_WS`.
- Set `CONSULTATION_PRICE_INR` to the intended production consultation price before enabling verified payments.
- Rotate any keys that were ever committed, logged, pasted into frontend env files, or shared outside the secret manager.
- Verify Supabase RLS policies before exposing admin/community/consultation features.
