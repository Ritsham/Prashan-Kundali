# Backend Production Hardening

This pass standardizes core FastAPI production behavior without changing successful response contracts for existing feature routes.

## Implemented

- Global error envelope:
  - `{"error": {"code", "message", "request_id", "details?"}}`
  - Handles `HTTPException`, validation errors, and unhandled exceptions.
- Request IDs:
  - Accepts `x-request-id` or generates `req_<id>`.
  - Adds `x-request-id` to responses.
  - Includes request IDs in JSON request logs.
- Health/readiness:
  - `GET /health` and `GET /api/health`
  - `GET /readyz` and `GET /api/readyz`
- Input validation:
  - Shared strict request base model with `extra="forbid"` and control-character rejection.
  - Bounded coordinates, IDs, dates, times, phone numbers, emails, text fields, chat payloads, and payment IDs on high-risk write paths.
- Consultation and booking lifecycle:
  - Canonical statuses are `requested`, `pending_payment`, `confirmed`, `active`, `completed`, `cancelled`, and `refunded`.
  - Legacy statuses are normalized at API/storage boundaries for compatibility.
  - Active booking conflict checks prevent duplicate active consultation requests for the same user/astrologer slot.
  - `CONSULTATION_PRICE_INR` is validated server-side and prepares paid bookings for gateway integration without enabling a gateway.
- Rate limiting:
  - Redis-backed sliding window with hashed identity keys.
  - In-memory fallback if Redis is temporarily unavailable.
  - Limits added for auth, public analytics/geocode/profile/status, LLM/chart-heavy routes, booking/application routes, payment routes, REST chat writes, and WebSocket connection attempts.
- Safe logging:
  - API traceback responses removed.
  - Raw upstream response bodies are no longer logged from public consultation snapshot generation.
  - Warnings use event names rather than personal request payloads.
- External service timeout handling:
  - `httpx.Timeout` with explicit connect limits on newly touched astrology, LLM, Razorpay, and panchang calls.
- OpenAPI cleanup:
  - API title/version updated.
  - OpenAPI generation smoke-tested.

## Remaining Risks

- Several storage modules still use `print(...)`; they should be converted to structured logging in a follow-up pass.
- Some legacy success responses remain untyped `dict` responses for frontend compatibility; full response-model coverage should be rolled out endpoint-by-endpoint.
- Rate limits are process-local fallback when Redis is unavailable. Multi-instance production needs Redis healthy for globally consistent limits.
- WebSocket message-level throttling is still basic; current hardening limits connection attempts and REST chat writes.
- Legacy static/frontend fallback routes remain in `main.py`; deployment should confirm whether `frontend_old` is still intentionally served.
