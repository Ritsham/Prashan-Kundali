-- Production security hardening for Shree Lakshmi Astro.
-- Non-destructive: enables RLS and adds owner/admin policies for sensitive tables.
-- Review in Supabase SQL editor before applying to production.

ALTER TABLE IF EXISTS public.users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';

CREATE TABLE IF NOT EXISTS public.payments (
  id TEXT PRIMARY KEY,
  user_id UUID,
  booking_id TEXT,
  match_request_id TEXT,
  amount REAL NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'INR',
  status TEXT NOT NULL DEFAULT 'not_paid',
  provider TEXT,
  provider_ref TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_provider_ref
ON public.payments (provider, provider_ref)
WHERE provider IS NOT NULL AND provider_ref IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.admin_logs (
  id BIGSERIAL PRIMARY KEY,
  actor_user_id UUID,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  before_json JSONB,
  after_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_logs_entity_created
ON public.admin_logs (entity_type, entity_id, created_at DESC);

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
      AND role = 'admin'
  );
$$;

DO $$
BEGIN
  IF to_regclass('public.prashna_charts') IS NOT NULL THEN
    ALTER TABLE public.prashna_charts ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own prashna charts" ON public.prashna_charts;
    DROP POLICY IF EXISTS "Users write own prashna charts" ON public.prashna_charts;
    DROP POLICY IF EXISTS "Admins manage prashna charts" ON public.prashna_charts;
    CREATE POLICY "Users read own prashna charts"
      ON public.prashna_charts FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Users write own prashna charts"
      ON public.prashna_charts FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Admins manage prashna charts"
      ON public.prashna_charts FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.lagna_charts') IS NOT NULL THEN
    ALTER TABLE public.lagna_charts ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own lagna charts" ON public.lagna_charts;
    DROP POLICY IF EXISTS "Users write own lagna charts" ON public.lagna_charts;
    DROP POLICY IF EXISTS "Admins manage lagna charts" ON public.lagna_charts;
    CREATE POLICY "Users read own lagna charts"
      ON public.lagna_charts FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Users write own lagna charts"
      ON public.lagna_charts FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Admins manage lagna charts"
      ON public.lagna_charts FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.consultation_requests') IS NOT NULL THEN
    ALTER TABLE public.consultation_requests ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own consultation requests" ON public.consultation_requests;
    DROP POLICY IF EXISTS "Users create own consultation requests" ON public.consultation_requests;
    DROP POLICY IF EXISTS "Admins manage consultation requests" ON public.consultation_requests;
    CREATE POLICY "Users read own consultation requests"
      ON public.consultation_requests FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Users create own consultation requests"
      ON public.consultation_requests FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Admins manage consultation requests"
      ON public.consultation_requests FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.match_requests') IS NOT NULL THEN
    ALTER TABLE public.match_requests ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own match requests" ON public.match_requests;
    DROP POLICY IF EXISTS "Users create own match requests" ON public.match_requests;
    DROP POLICY IF EXISTS "Admins manage match requests" ON public.match_requests;
    CREATE POLICY "Users read own match requests"
      ON public.match_requests FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Users create own match requests"
      ON public.match_requests FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Admins manage match requests"
      ON public.match_requests FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.paid_consultations') IS NOT NULL THEN
    ALTER TABLE public.paid_consultations ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Admins manage paid consultations" ON public.paid_consultations;
    CREATE POLICY "Admins manage paid consultations"
      ON public.paid_consultations FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.payments') IS NOT NULL THEN
    ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own payments" ON public.payments;
    DROP POLICY IF EXISTS "Users create own payments" ON public.payments;
    DROP POLICY IF EXISTS "Admins manage payments" ON public.payments;
    CREATE POLICY "Users read own payments"
      ON public.payments FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Users create own payments"
      ON public.payments FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Admins manage payments"
      ON public.payments FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;
END $$;

INSERT INTO storage.buckets (id, name, public)
VALUES ('community-proofs', 'community-proofs', false)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "Allow authenticated users to read proofs" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated users to upload proofs" ON storage.objects;
DROP POLICY IF EXISTS "Allow users to update their own proofs" ON storage.objects;
DROP POLICY IF EXISTS "Allow users to delete their own proofs" ON storage.objects;

CREATE POLICY "Users upload own community proofs"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'community-proofs'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users read own community proofs"
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'community-proofs'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users update own community proofs"
ON storage.objects FOR UPDATE TO authenticated
USING (
  bucket_id = 'community-proofs'
  AND (storage.foldername(name))[1] = auth.uid()::text
)
WITH CHECK (
  bucket_id = 'community-proofs'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users delete own community proofs"
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'community-proofs'
  AND (storage.foldername(name))[1] = auth.uid()::text
);
