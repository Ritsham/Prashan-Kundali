# Production Readiness Report

Generated from the current codebase on 2026-07-13.

## Executive Summary

This codebase is close to an MVP-plus backend, not yet a fully proven high-scale production system. It has useful production foundations: FastAPI services, Supabase-backed persistence, RLS/security migration scripts, JWT-based auth, role checks, Pydantic request validation, Redis-backed rate limiting, Dockerized microservices, and payment hardening switches.

The largest real-world bottlenecks are synchronous chart and LLM calls in user-facing request paths, Supabase/API latency, Redis availability for realtime, and the current static frontend architecture. For production, deploy the Docker/microservice topology behind a real load balancer. Do not rely on the Vercel Python serverless path for WebSockets or long-running requests.

## Current Architecture

- Gateway: `main.py`, FastAPI, static frontend serving, API routers, health/readiness checks.
- Astrology engine: `services/astrology_engine/main.py`, internal chart calculation and rule interpretation.
- LLM engine: `services/llm_engine_service/main.py`, synchronous and Celery-backed narrative generation.
- Persistence: Supabase/Postgres via `supabase-py`, with service-role usage for admin flows.
- Realtime: WebSockets plus Redis pub/sub helper in `app/services/realtime.py`; community chat also has its own authenticated WebSocket manager.
- Cache/rate limit: Redis for cache and rate limiting, with in-memory fallback for rate limiting.
- Deployment: Docker Compose includes Redis, astrology engine, LLM engine, worker, and API gateway. Vercel config rewrites everything to the Python app.

## Production Readiness Level

Practical level: beta production / controlled launch.

Suitable for:
- A small invite-only or early paid launch.
- Tens of concurrent active users.
- Hundreds to low thousands of daily users if usage is not bursty and LLM calls are rate-limited.

Not yet suitable for:
- Open public launch with unbounded traffic.
- High-volume realtime chat.
- Strong uptime guarantees.
- Heavy concurrent LLM/chart generation without queue-first flow and load testing.

## Capacity Estimate

These numbers are estimates from code structure, not load-test results.

Assumptions:
- Docker `api_gateway` runs `uvicorn` with 2 workers.
- Each chart request waits up to 30 seconds for astrology calculation.
- Prashna additionally waits up to 25 seconds for synchronous LLM generation.
- Redis and Supabase are healthy and close enough geographically.
- LLM provider latency is stable.

Estimated safe starting capacity:
- Normal API reads/light writes: 50-150 concurrent users per small 2-worker API instance.
- Chart generation: about 4-12 concurrent active chart requests per API instance before latency becomes painful, depending on astrology engine CPU time.
- LLM generation: about 2-8 concurrent sync generations unless provider latency and rate limits are very favorable.
- Community WebSocket users: 100-300 connected sockets per API instance can be a reasonable starting target, but only after Redis pub/sub is stable and file descriptor limits are configured.
- Celery LLM worker: current compose uses `--concurrency=4`, so about 4 background LLM jobs per worker container at a time.

Hard user-cap answer:
- Without load testing, do not claim more than 50 concurrent real users for the full experience.
- For a controlled launch, plan for 25-50 simultaneous active users and 100-300 realtime connections.
- Scale horizontally only after adding metrics and testing the chart/LLM endpoints under realistic traffic.

## Current Rate Limits

- Public endpoints: 60 requests/minute per identity/IP.
- Auth endpoint: 30 requests/minute.
- LLM endpoints: 10 requests/minute.
- Booking/payment: 8-12 requests/minute.
- Prashna/Lagna creation: 10 requests/minute.
- Community chat: 30 requests/minute.

These limits protect abuse but do not guarantee capacity. Internal downstream concurrency still needs queueing, worker scaling, and provider quotas.

## Where It Can Break

1. Synchronous expensive requests
   - `/api/prashna`, `/api/lagna`, and consultation snapshot enrichment call internal services during the HTTP request.
   - If astrology or LLM slows down, gateway workers stay occupied and users see timeouts.

2. WebSockets on serverless
   - The Vercel Python rewrite path is not appropriate for durable WebSocket workloads.
   - Use the Docker deployment or another long-running ASGI host for realtime.

3. Redis dependency
   - Redis is required for cross-worker realtime and reliable rate limiting.
   - The in-memory fallback is per-process and weak under horizontal scaling.

4. Supabase service-role blast radius
   - Some server flows intentionally use service role.
   - A leaked backend environment or accidental frontend exposure would be severe.

5. LLM provider quotas and latency
   - Real throughput is capped by provider rate limits, timeout behavior, and retry strategy.
   - Sync LLM generation is the most user-visible bottleneck.

6. Static frontend coupling
   - `frontend_old` is served directly by FastAPI with catch-all routing.
   - This is workable, but harder to cache, version, test, and deploy independently.

7. Observability gaps
   - There is limited structured logging, metrics, request tracing, error aggregation, and queue depth monitoring.
   - Production incidents will be harder to diagnose quickly.

8. Realtime online count
   - The community router's online count is per-process, not globally accurate across multiple API workers/instances.

9. File upload scanning
   - Upload validation checks MIME/signature/size, which is good.
   - It does not include antivirus/malware scanning or image/PDF sanitization.

10. Load-test gap
   - No benchmark scripts or CI load tests are present.
   - Capacity numbers need verification before a public launch.

## Hardening Done In This Pass

- Gateway now uses central `get_settings().cors_origins` instead of a permissive wildcard default.
- Gateway startup now validates production environment settings.
- Added `/health` and `/ready` endpoints.
- Readiness checks Redis and fails in production if it is missing.
- Legacy root WebSocket routes are disabled unless `ENABLE_LEGACY_UNAUTHENTICATED_WS=true`.
- Legacy root WebSocket routes now require a valid Supabase JWT when enabled.
- Panchang in-memory cache is bounded to 512 entries.
- Redis pub/sub helper no longer runs blocking Redis operations directly in the event loop.
- Internal astrology and LLM services now validate startup settings.

## Recommended Next Improvements

1. Move chart + LLM generation to an async job-first workflow.
   - Return `202 Accepted` with a job ID.
   - Stream or poll for status.
   - Keep sync mode only for admin/internal diagnostics.

2. Add production metrics.
   - Request latency by route.
   - Error rates by status code.
   - Redis availability.
   - Supabase latency.
   - Celery queue depth and job duration.
   - WebSocket connection count.

3. Load test before launch.
   - Test login, chart creation, consultation booking, payment verify, community message send, and WebSocket fanout.
   - Start with 25, 50, 100, and 250 virtual users.

4. Improve realtime scaling.
   - Use Redis for global online count/presence.
   - Add heartbeat/ping and idle disconnects.
   - Enforce message size limits at WebSocket receive.

5. Add CI checks.
   - `python -m compileall`.
   - Unit tests for auth/role checks and request validation.
   - Integration tests with mocked Supabase/Redis/internal services.

6. Separate frontend deployment.
   - Build a modern frontend bundle and serve via CDN.
   - Keep FastAPI as API only, except for legal/static fallbacks if needed.

7. Secure file uploads further.
   - Add malware scanning.
   - Generate short-lived signed URLs only.
   - Add stricter bucket policies and admin audit logs for document access.

8. Add deployment runbooks.
   - Required environment checklist.
   - Rollback steps.
   - Redis/Supabase outage handling.
   - LLM provider failover procedure.

