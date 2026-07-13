-- Standardized consultation case pipeline.
-- This extends the existing consultation_requests table without deleting or renaming data.

ALTER TABLE consultation_requests
  ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'direct_consultation',
  ADD COLUMN IF NOT EXISTS chart_type TEXT NOT NULL DEFAULT 'lagna',
  ADD COLUMN IF NOT EXISTS gender TEXT,
  ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS timezone TEXT,
  ADD COLUMN IF NOT EXISTS additional_message TEXT,
  ADD COLUMN IF NOT EXISTS preferred_date TEXT,
  ADD COLUMN IF NOT EXISTS consultation_mode TEXT,
  ADD COLUMN IF NOT EXISTS quoted_price NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'INR',
  ADD COLUMN IF NOT EXISTS assigned_astrologer TEXT,
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT,
  ADD COLUMN IF NOT EXISTS astrology_snapshot JSONB;

ALTER TABLE consultation_requests
  ADD COLUMN IF NOT EXISTS astrological_snapshot TEXT;

UPDATE consultation_requests
SET
  source_type = CASE WHEN topic = 'Prashna' THEN 'prashna' ELSE source_type END,
  chart_type = CASE WHEN topic = 'Prashna' THEN 'prashna' ELSE chart_type END
WHERE source_type = 'direct_consultation'
  AND chart_type = 'lagna'
  AND topic = 'Prashna';

UPDATE consultation_requests
SET astrology_snapshot = astrological_snapshot::jsonb
WHERE astrology_snapshot IS NULL
  AND astrological_snapshot IS NOT NULL
  AND astrological_snapshot ~ '^\s*[\{\[]';

CREATE UNIQUE INDEX IF NOT EXISTS idx_consultation_requests_idempotency
ON consultation_requests (idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_consultation_requests_case_filters
ON consultation_requests (status, source_type, chart_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_consultation_requests_name
ON consultation_requests (name);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'consultation_requests_status_lifecycle_check'
  ) THEN
    ALTER TABLE consultation_requests
      ADD CONSTRAINT consultation_requests_status_lifecycle_check
      CHECK (
        status IN (
          'requested', 'pending_payment', 'confirmed', 'active', 'completed', 'cancelled', 'refunded',
          'pending', 'reviewed', 'accepted', 'scheduled', 'in_progress', 'rejected', 'waiting_queue'
        )
      ) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'consultation_requests_price_check'
  ) THEN
    ALTER TABLE consultation_requests
      ADD CONSTRAINT consultation_requests_price_check
      CHECK (quoted_price IS NULL OR (quoted_price > 0 AND quoted_price <= 100000)) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'consultation_requests_currency_check'
  ) THEN
    ALTER TABLE consultation_requests
      ADD CONSTRAINT consultation_requests_currency_check
      CHECK (currency ~ '^[A-Z]{3}$') NOT VALID;
  END IF;
END $$;
