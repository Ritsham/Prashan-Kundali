# Production Scale And Distribution Plan

Created on 2026-07-13.

## Capacity Target

Target before broad public launch:
- 500-1,000 simultaneous normal users.
- 100-250 concurrent chart/report jobs through queues.
- 1,000-5,000 realtime connections across scaled instances.
- Normal API P95 under 500ms.
- Job submission P95 under 2s.
- Error rate under 1%.

## Engineering Roadmap

### Chunk 1: Queue-First Prashna

Status: started.

Done:
- Added Redis-backed job status helpers.
- Added Celery task for full Prashna chart + LLM generation.
- `/api/prashna` now returns `job_id` by default.
- Added `/api/prashna/jobs/{job_id}` for polling.
- Frontend now polls queued Prashna jobs and renders when ready.
- Added basic admin ops metrics.
- Tuned Celery acknowledgement, prefetch, and time limits.

Next:
- Persist active job ID in more result pages where needed.
- Add cancellation and expired-job UX.

### Chunk 2: Queue Consultation And Matchmaking

Status: started.

Done:
- Matchmaking report generation now queues by default.
- Added `/api/matchmaking/jobs/{job_id}` for polling.
- Matchmaking frontend now polls progress and renders when ready.
- Public consultation requests now save immediately.
- Public consultation chart snapshot enrichment now runs in the background when birth/place data is available.
- Paid consultation bookings now save immediately and queue chart snapshot enrichment.
- Celery tasks now retry transient network errors with backoff.
- Added local storage resume for pending Prashna and matchmaking jobs.
- Added a dependency-free local load-test harness at `scripts/load_test_plan.py`.

Still to do:
- Add user-facing "snapshot still processing" state in consultation detail views.
- Queue any future PDF/report generation.

Expected result:
- Booking and payment flows stay responsive under traffic.
- Users see job progress instead of request timeouts.

### Chunk 3: Split Runtime Roles

Recommended services:
- `api_gateway`: auth, reads, bookings, static/legal fallback.
- `astrology_engine`: internal chart service.
- `llm_engine`: internal LLM orchestration API.
- `llm_worker`: background LLM/Prashna/report jobs.
- `realtime_gateway`: WebSocket/community presence.
- `redis`: broker, cache, pub/sub, job state.

Deployment starting point:
- API gateway: 2-4 workers.
- Astrology engine: 2 replicas, 2 workers each.
- LLM worker: 2 replicas, concurrency 4 each.
- Realtime gateway: 1-2 replicas after Redis presence is global.

Local scale overlay:
- `docker-compose.scale.yml` contains resource limits and worker concurrency knobs.
- Use it with `docker compose -f docker-compose.yml -f docker-compose.scale.yml up --build`.
- For real multi-replica API scaling, remove fixed `container_name`/host-port conflicts or put the gateway behind a reverse proxy/load balancer.

### Chunk 4: Observability

Started:
- In-process route count, error, average latency, recent P95.
- Admin endpoint: `/api/admin/ops-metrics`.
- Celery queue depth in admin ops metrics.
- Background job success/failure counters by workflow.

Next:
- Add Celery task duration histograms.
- Add LLM provider timeout/failure counters.
- Add Supabase query latency wrappers.
- Add external error tracking.
- Export Prometheus-compatible metrics.

### Chunk 5: Load Testing

Add scripted scenarios:
- Login/config bootstrap.
- Geocode search.
- Prashna submit and poll.
- Consultation request.
- Payment order and verification with mocked Razorpay.
- Community messages and WebSocket fanout.

Traffic steps:
- 50 virtual users.
- 100 virtual users.
- 250 virtual users.
- 500 virtual users.

Pass criteria:
- No 5xx spike.
- Queue depth drains after traffic stops.
- P95 job submission under 2s.
- Normal read APIs under 500ms P95.

### Chunk 6: Frontend Performance

Immediate:
- Avoid blocking the initial page on heavy chart widgets.
- Lazy render divisional charts and KP tables after first result paint.
- Add loading/progress states for queued jobs.
- Cache static assets aggressively.

Next:
- Move from `frontend_old` static scripts to a bundled frontend.
- Split code by route.
- CDN-host static assets.
- Track Core Web Vitals.

## Distribution Plan

### Positioning

Primary wedge:
> Ask one urgent life question and get a structured Prashna answer with timing, reasoning, and next step.

Avoid broad generic positioning like "another astrology app." Lead with urgent use cases:
- Marriage decision.
- Job/career timing.
- Money/business decision.
- Foreign travel/visa timing.
- Health caution with clear professional-advice disclaimer.

### First 7 Days

- Launch one main page for free Prashna.
- Launch three intent pages:
  - Marriage timing.
  - Career/job change.
  - Money/business decision.
- Add WhatsApp share and follow-up CTA.
- Recruit first 10-20 astrologers manually.
- Publish 20 short videos:
  - 5 marriage.
  - 5 career.
  - 5 money.
  - 5 "how Prashna works."
- Offer first 100 detailed readings at an early-user price.

### Days 8-30

- Daily Instagram Reels and YouTube Shorts.
- WhatsApp broadcast list for daily Panchang + question prompt.
- SEO tools:
  - Prashna chart calculator.
  - Kundali calculator.
  - Matchmaking compatibility.
  - Today's Panchang.
- Referral loop:
  - Invite 3 people, unlock one detailed reading.
- Astrologer profile pages:
  - Each astrologer gets a shareable profile.
  - Their audience becomes supply-led acquisition.

### Days 31-90

- Paid acquisition only after conversion is measured.
- Micro-influencer partnerships with revenue share.
- Launch weekly live Prashna sessions.
- Publish anonymized case studies.
- Add subscription:
  - Daily personalized guidance.
  - Saved charts.
  - Community access.
  - Discounted consultations.

## Metrics To Watch

Product:
- Visitor to signup.
- Signup to first question.
- First question to paid reading.
- Day-1 and day-7 retention.
- Referral invites per user.

Revenue:
- Paid conversion.
- Average revenue per paid user.
- Refund rate.
- Consultation completion rate.
- CAC payback period.

Engineering:
- API P95 latency.
- Job queue depth.
- Job completion time P95.
- LLM failure rate.
- Redis availability.
- Supabase error rate.
- WebSocket connections.
