-- Shree Lakshmi Astro RLS and authorization policy hardening.
-- Apply after 005_production_security_hardening.sql.
-- This migration is additive/defensive: it enables RLS where missing, replaces
-- broad policies, and keeps service-role backend operations available.

ALTER TABLE IF EXISTS public.users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user';
ALTER TABLE IF EXISTS public.users ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'none';
ALTER TABLE IF EXISTS public.users ADD COLUMN IF NOT EXISTS community_access BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE IF EXISTS public.users ADD COLUMN IF NOT EXISTS community_verification_status TEXT DEFAULT 'NOT_APPLIED';
ALTER TABLE IF EXISTS public.users ADD COLUMN IF NOT EXISTS community_verified_at TIMESTAMPTZ;
ALTER TABLE IF EXISTS public.users ADD COLUMN IF NOT EXISTS community_suspended_at TIMESTAMPTZ;

ALTER TABLE IF EXISTS public.paid_consultations ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE IF EXISTS public.consultation_requests ADD COLUMN IF NOT EXISTS assigned_astrologer UUID;
ALTER TABLE IF EXISTS public.community_messages ADD COLUMN IF NOT EXISTS sender_id TEXT;
ALTER TABLE IF EXISTS public.community_threads ADD COLUMN IF NOT EXISTS sender_id TEXT;

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

CREATE OR REPLACE FUNCTION public.is_verified_astrologer()
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
      AND (
        role = 'astrologer_verified'
        OR (role = 'astrologer' AND verification_status = 'verified')
        OR community_access IS TRUE
      )
  );
$$;

CREATE OR REPLACE FUNCTION public.prevent_user_privilege_escalation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF auth.role() = 'service_role' OR public.is_admin() THEN
    RETURN NEW;
  END IF;

  IF NEW.role IS DISTINCT FROM OLD.role
    OR NEW.verification_status IS DISTINCT FROM OLD.verification_status
    OR NEW.community_access IS DISTINCT FROM OLD.community_access
    OR NEW.community_verification_status IS DISTINCT FROM OLD.community_verification_status
    OR NEW.community_verified_at IS DISTINCT FROM OLD.community_verified_at
    OR NEW.community_suspended_at IS DISTINCT FROM OLD.community_suspended_at THEN
    RAISE EXCEPTION 'Only admins can change authorization fields';
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS prevent_user_privilege_escalation ON public.users;
CREATE TRIGGER prevent_user_privilege_escalation
BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION public.prevent_user_privilege_escalation();

DO $$
BEGIN
  IF to_regclass('public.users') IS NOT NULL THEN
    ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own profile" ON public.users;
    DROP POLICY IF EXISTS "Users insert own profile" ON public.users;
    DROP POLICY IF EXISTS "Users update own non-privileged profile" ON public.users;
    DROP POLICY IF EXISTS "Admins manage users" ON public.users;
    CREATE POLICY "Users read own profile"
      ON public.users FOR SELECT TO authenticated
      USING (id = auth.uid() OR public.is_admin());
    CREATE POLICY "Users insert own profile"
      ON public.users FOR INSERT TO authenticated
      WITH CHECK (id = auth.uid() AND role = 'user' AND community_access IS FALSE);
    CREATE POLICY "Users update own non-privileged profile"
      ON public.users FOR UPDATE TO authenticated
      USING (id = auth.uid())
      WITH CHECK (id = auth.uid());
    CREATE POLICY "Admins manage users"
      ON public.users FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.prashna_charts') IS NOT NULL THEN
    ALTER TABLE public.prashna_charts ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own prashna charts" ON public.prashna_charts;
    DROP POLICY IF EXISTS "Users write own prashna charts" ON public.prashna_charts;
    DROP POLICY IF EXISTS "Users update own prashna charts" ON public.prashna_charts;
    DROP POLICY IF EXISTS "Users delete own prashna charts" ON public.prashna_charts;
    DROP POLICY IF EXISTS "Admins manage prashna charts" ON public.prashna_charts;
    CREATE POLICY "Users read own prashna charts"
      ON public.prashna_charts FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Users write own prashna charts"
      ON public.prashna_charts FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Users update own prashna charts"
      ON public.prashna_charts FOR UPDATE TO authenticated
      USING (user_id = auth.uid())
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Users delete own prashna charts"
      ON public.prashna_charts FOR DELETE TO authenticated
      USING (user_id = auth.uid());
    CREATE POLICY "Admins manage prashna charts"
      ON public.prashna_charts FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.lagna_charts') IS NOT NULL THEN
    ALTER TABLE public.lagna_charts ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own lagna charts" ON public.lagna_charts;
    DROP POLICY IF EXISTS "Users write own lagna charts" ON public.lagna_charts;
    DROP POLICY IF EXISTS "Users update own lagna charts" ON public.lagna_charts;
    DROP POLICY IF EXISTS "Users delete own lagna charts" ON public.lagna_charts;
    DROP POLICY IF EXISTS "Admins manage lagna charts" ON public.lagna_charts;
    CREATE POLICY "Users read own lagna charts"
      ON public.lagna_charts FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Users write own lagna charts"
      ON public.lagna_charts FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Users update own lagna charts"
      ON public.lagna_charts FOR UPDATE TO authenticated
      USING (user_id = auth.uid())
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Users delete own lagna charts"
      ON public.lagna_charts FOR DELETE TO authenticated
      USING (user_id = auth.uid());
    CREATE POLICY "Admins manage lagna charts"
      ON public.lagna_charts FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.consultation_requests') IS NOT NULL THEN
    ALTER TABLE public.consultation_requests ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own consultation requests" ON public.consultation_requests;
    DROP POLICY IF EXISTS "Users create own consultation requests" ON public.consultation_requests;
    DROP POLICY IF EXISTS "Consultation participants read requests" ON public.consultation_requests;
    DROP POLICY IF EXISTS "Admins manage consultation requests" ON public.consultation_requests;
    CREATE POLICY "Consultation participants read requests"
      ON public.consultation_requests FOR SELECT TO authenticated
      USING (
        public.is_admin()
        OR user_id = auth.uid()
        OR email = (auth.jwt() ->> 'email')
        OR assigned_astrologer::text = auth.uid()::text
      );
    CREATE POLICY "Users create own consultation requests"
      ON public.consultation_requests FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Admins manage consultation requests"
      ON public.consultation_requests FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.paid_consultations') IS NOT NULL THEN
    ALTER TABLE public.paid_consultations ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own paid consultations" ON public.paid_consultations;
    DROP POLICY IF EXISTS "Admins manage paid consultations" ON public.paid_consultations;
    CREATE POLICY "Users read own paid consultations"
      ON public.paid_consultations FOR SELECT TO authenticated
      USING (
        public.is_admin()
        OR user_id = auth.uid()
        OR user_email = (auth.jwt() ->> 'email')
      );
    CREATE POLICY "Admins manage paid consultations"
      ON public.paid_consultations FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.consultant_bookings') IS NOT NULL THEN
    ALTER TABLE public.consultant_bookings ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own consultant bookings" ON public.consultant_bookings;
    DROP POLICY IF EXISTS "Users create own consultant bookings" ON public.consultant_bookings;
    DROP POLICY IF EXISTS "Admins manage consultant bookings" ON public.consultant_bookings;
    CREATE POLICY "Users read own consultant bookings"
      ON public.consultant_bookings FOR SELECT TO authenticated
      USING (public.is_admin() OR user_id::text = auth.uid()::text OR client_email = (auth.jwt() ->> 'email'));
    CREATE POLICY "Users create own consultant bookings"
      ON public.consultant_bookings FOR INSERT TO authenticated
      WITH CHECK (user_id::text = auth.uid()::text);
    CREATE POLICY "Admins manage consultant bookings"
      ON public.consultant_bookings FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.consultant_messages') IS NOT NULL THEN
    ALTER TABLE public.consultant_messages ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Booking participants read consultant messages" ON public.consultant_messages;
    DROP POLICY IF EXISTS "Booking participants create consultant messages" ON public.consultant_messages;
    DROP POLICY IF EXISTS "Admins manage consultant messages" ON public.consultant_messages;
    CREATE POLICY "Booking participants read consultant messages"
      ON public.consultant_messages FOR SELECT TO authenticated
      USING (
        public.is_admin()
        OR EXISTS (
          SELECT 1 FROM public.consultant_bookings b
          WHERE b.id = booking_id
            AND (b.user_id::text = auth.uid()::text OR b.client_email = (auth.jwt() ->> 'email'))
        )
      );
    CREATE POLICY "Booking participants create consultant messages"
      ON public.consultant_messages FOR INSERT TO authenticated
      WITH CHECK (
        sender_role = 'user'
        AND user_id::text = auth.uid()::text
        AND EXISTS (
          SELECT 1 FROM public.consultant_bookings b
          WHERE b.id = booking_id
            AND (b.user_id::text = auth.uid()::text OR b.client_email = (auth.jwt() ->> 'email'))
        )
      );
    CREATE POLICY "Admins manage consultant messages"
      ON public.consultant_messages FOR ALL TO authenticated
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

  IF to_regclass('public.match_participants') IS NOT NULL THEN
    ALTER TABLE public.match_participants ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own match participants" ON public.match_participants;
    DROP POLICY IF EXISTS "Users create own match participants" ON public.match_participants;
    DROP POLICY IF EXISTS "Admins manage match participants" ON public.match_participants;
    CREATE POLICY "Users read own match participants"
      ON public.match_participants FOR SELECT TO authenticated
      USING (
        public.is_admin()
        OR EXISTS (
          SELECT 1 FROM public.match_requests m
          WHERE m.id = match_request_id AND m.user_id = auth.uid()
        )
      );
    CREATE POLICY "Users create own match participants"
      ON public.match_participants FOR INSERT TO authenticated
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM public.match_requests m
          WHERE m.id = match_request_id AND m.user_id = auth.uid()
        )
      );
    CREATE POLICY "Admins manage match participants"
      ON public.match_participants FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.match_reports') IS NOT NULL THEN
    ALTER TABLE public.match_reports ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own match reports" ON public.match_reports;
    DROP POLICY IF EXISTS "Admins manage match reports" ON public.match_reports;
    CREATE POLICY "Users read own match reports"
      ON public.match_reports FOR SELECT TO authenticated
      USING (
        public.is_admin()
        OR EXISTS (
          SELECT 1 FROM public.match_requests m
          WHERE m.id = match_request_id AND m.user_id = auth.uid()
        )
      );
    CREATE POLICY "Admins manage match reports"
      ON public.match_reports FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.consultation_attachments') IS NOT NULL THEN
    ALTER TABLE public.consultation_attachments ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Consultation participants read attachments" ON public.consultation_attachments;
    DROP POLICY IF EXISTS "Admins manage consultation attachments" ON public.consultation_attachments;
    CREATE POLICY "Consultation participants read attachments"
      ON public.consultation_attachments FOR SELECT TO authenticated
      USING (
        public.is_admin()
        OR EXISTS (
          SELECT 1 FROM public.consultation_requests c
          WHERE c.id = consultation_id
            AND (c.user_id = auth.uid() OR c.email = (auth.jwt() ->> 'email') OR c.assigned_astrologer::text = auth.uid()::text)
        )
        OR EXISTS (
          SELECT 1 FROM public.match_requests m
          WHERE m.id = match_request_id AND m.user_id = auth.uid()
        )
      );
    CREATE POLICY "Admins manage consultation attachments"
      ON public.consultation_attachments FOR ALL TO authenticated
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
      WITH CHECK (user_id = auth.uid() AND status IN ('created', 'not_paid'));
    CREATE POLICY "Admins manage payments"
      ON public.payments FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.admin_logs') IS NOT NULL THEN
    ALTER TABLE public.admin_logs ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Admins read admin logs" ON public.admin_logs;
    DROP POLICY IF EXISTS "Admins insert admin logs" ON public.admin_logs;
    CREATE POLICY "Admins read admin logs"
      ON public.admin_logs FOR SELECT TO authenticated
      USING (public.is_admin());
    CREATE POLICY "Admins insert admin logs"
      ON public.admin_logs FOR INSERT TO authenticated
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.app_visit_events') IS NOT NULL THEN
    ALTER TABLE public.app_visit_events ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Admins read app visit events" ON public.app_visit_events;
    DROP POLICY IF EXISTS "Users create own visit events" ON public.app_visit_events;
    CREATE POLICY "Admins read app visit events"
      ON public.app_visit_events FOR SELECT TO authenticated
      USING (public.is_admin());
    CREATE POLICY "Users create own visit events"
      ON public.app_visit_events FOR INSERT TO authenticated
      WITH CHECK (user_id IS NULL OR user_id = auth.uid());
  END IF;

  IF to_regclass('public.consultant_platform_stats') IS NOT NULL THEN
    ALTER TABLE public.consultant_platform_stats ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Admins manage consultant platform stats" ON public.consultant_platform_stats;
    CREATE POLICY "Admins manage consultant platform stats"
      ON public.consultant_platform_stats FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.astrologer_profiles') IS NOT NULL THEN
    ALTER TABLE public.astrologer_profiles ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own astrologer profile" ON public.astrologer_profiles;
    DROP POLICY IF EXISTS "Users create own astrologer profile" ON public.astrologer_profiles;
    DROP POLICY IF EXISTS "Users update own astrologer profile" ON public.astrologer_profiles;
    DROP POLICY IF EXISTS "Admins manage astrologer profiles" ON public.astrologer_profiles;
    CREATE POLICY "Users read own astrologer profile"
      ON public.astrologer_profiles FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Users create own astrologer profile"
      ON public.astrologer_profiles FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Users update own astrologer profile"
      ON public.astrologer_profiles FOR UPDATE TO authenticated
      USING (user_id = auth.uid())
      WITH CHECK (user_id = auth.uid());
    CREATE POLICY "Admins manage astrologer profiles"
      ON public.astrologer_profiles FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_applications') IS NOT NULL THEN
    ALTER TABLE public.community_applications ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Allow users to manage their own application" ON public.community_applications;
    DROP POLICY IF EXISTS "Applicants read own community application" ON public.community_applications;
    DROP POLICY IF EXISTS "Applicants submit own community application" ON public.community_applications;
    DROP POLICY IF EXISTS "Admins manage community applications" ON public.community_applications;
    CREATE POLICY "Applicants submit own community application"
      ON public.community_applications FOR INSERT TO authenticated
      WITH CHECK (user_id = auth.uid() AND status IN ('DRAFT', 'PENDING', 'NOT_APPLIED'));
    CREATE POLICY "Admins manage community applications"
      ON public.community_applications FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_application_systems') IS NOT NULL THEN
    ALTER TABLE public.community_application_systems ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Allow users to manage their own systems" ON public.community_application_systems;
    DROP POLICY IF EXISTS "Applicants add own application systems" ON public.community_application_systems;
    DROP POLICY IF EXISTS "Admins manage application systems" ON public.community_application_systems;
    CREATE POLICY "Applicants add own application systems"
      ON public.community_application_systems FOR INSERT TO authenticated
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM public.community_applications a
          WHERE a.id = application_id AND a.user_id = auth.uid()
        )
      );
    CREATE POLICY "Admins manage application systems"
      ON public.community_application_systems FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_application_proofs') IS NOT NULL THEN
    ALTER TABLE public.community_application_proofs ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Allow users to manage their own proofs" ON public.community_application_proofs;
    DROP POLICY IF EXISTS "Applicants add own application proofs" ON public.community_application_proofs;
    DROP POLICY IF EXISTS "Admins manage application proofs" ON public.community_application_proofs;
    CREATE POLICY "Applicants add own application proofs"
      ON public.community_application_proofs FOR INSERT TO authenticated
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM public.community_applications a
          WHERE a.id = application_id AND a.user_id = auth.uid()
        )
      );
    CREATE POLICY "Admins manage application proofs"
      ON public.community_application_proofs FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_application_reviews') IS NOT NULL THEN
    ALTER TABLE public.community_application_reviews ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Allow users to read their own reviews" ON public.community_application_reviews;
    DROP POLICY IF EXISTS "Applicants add more-info response reviews" ON public.community_application_reviews;
    DROP POLICY IF EXISTS "Admins manage application reviews" ON public.community_application_reviews;
    CREATE POLICY "Applicants add more-info response reviews"
      ON public.community_application_reviews FOR INSERT TO authenticated
      WITH CHECK (
        new_status = 'PENDING'
        AND EXISTS (
          SELECT 1 FROM public.community_applications a
          WHERE a.id = application_id
            AND a.user_id = auth.uid()
            AND a.status = 'NEEDS_MORE_INFORMATION'
        )
      );
    CREATE POLICY "Admins manage application reviews"
      ON public.community_application_reviews FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_memberships') IS NOT NULL THEN
    ALTER TABLE public.community_memberships ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own community membership" ON public.community_memberships;
    DROP POLICY IF EXISTS "Admins manage community memberships" ON public.community_memberships;
    CREATE POLICY "Users read own community membership"
      ON public.community_memberships FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Admins manage community memberships"
      ON public.community_memberships FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_application_status_history') IS NOT NULL THEN
    ALTER TABLE public.community_application_status_history ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own application status history" ON public.community_application_status_history;
    DROP POLICY IF EXISTS "Admins manage application status history" ON public.community_application_status_history;
    CREATE POLICY "Users read own application status history"
      ON public.community_application_status_history FOR SELECT TO authenticated
      USING (user_id = auth.uid() OR public.is_admin());
    CREATE POLICY "Admins manage application status history"
      ON public.community_application_status_history FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.community_channels') IS NOT NULL THEN
    ALTER TABLE public.community_channels ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Verified astrologers read community channels" ON public.community_channels;
    DROP POLICY IF EXISTS "Admins manage community channels" ON public.community_channels;
    CREATE POLICY "Verified astrologers read community channels"
      ON public.community_channels FOR SELECT TO authenticated
      USING (public.is_verified_astrologer() OR public.is_admin());
    CREATE POLICY "Admins manage community channels"
      ON public.community_channels FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_messages') IS NOT NULL THEN
    ALTER TABLE public.community_messages ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Verified astrologers read community messages" ON public.community_messages;
    DROP POLICY IF EXISTS "Verified astrologers create community messages" ON public.community_messages;
    DROP POLICY IF EXISTS "Message owners update community messages" ON public.community_messages;
    DROP POLICY IF EXISTS "Message owners delete community messages" ON public.community_messages;
    DROP POLICY IF EXISTS "Admins manage community messages" ON public.community_messages;
    CREATE POLICY "Verified astrologers read community messages"
      ON public.community_messages FOR SELECT TO authenticated
      USING (public.is_verified_astrologer() OR public.is_admin());
    CREATE POLICY "Verified astrologers create community messages"
      ON public.community_messages FOR INSERT TO authenticated
      WITH CHECK ((public.is_verified_astrologer() OR public.is_admin()) AND sender_id = auth.uid()::text);
    CREATE POLICY "Message owners update community messages"
      ON public.community_messages FOR UPDATE TO authenticated
      USING (sender_id = auth.uid()::text)
      WITH CHECK (sender_id = auth.uid()::text);
    CREATE POLICY "Message owners delete community messages"
      ON public.community_messages FOR DELETE TO authenticated
      USING (sender_id = auth.uid()::text);
    CREATE POLICY "Admins manage community messages"
      ON public.community_messages FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_threads') IS NOT NULL THEN
    ALTER TABLE public.community_threads ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Verified astrologers read community threads" ON public.community_threads;
    DROP POLICY IF EXISTS "Verified astrologers create community threads" ON public.community_threads;
    DROP POLICY IF EXISTS "Thread owners update community threads" ON public.community_threads;
    DROP POLICY IF EXISTS "Thread owners delete community threads" ON public.community_threads;
    DROP POLICY IF EXISTS "Admins manage community threads" ON public.community_threads;
    CREATE POLICY "Verified astrologers read community threads"
      ON public.community_threads FOR SELECT TO authenticated
      USING (public.is_verified_astrologer() OR public.is_admin());
    CREATE POLICY "Verified astrologers create community threads"
      ON public.community_threads FOR INSERT TO authenticated
      WITH CHECK ((public.is_verified_astrologer() OR public.is_admin()) AND sender_id = auth.uid()::text);
    CREATE POLICY "Thread owners update community threads"
      ON public.community_threads FOR UPDATE TO authenticated
      USING (sender_id = auth.uid()::text)
      WITH CHECK (sender_id = auth.uid()::text);
    CREATE POLICY "Thread owners delete community threads"
      ON public.community_threads FOR DELETE TO authenticated
      USING (sender_id = auth.uid()::text);
    CREATE POLICY "Admins manage community threads"
      ON public.community_threads FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.message_reactions') IS NOT NULL THEN
    ALTER TABLE public.message_reactions ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Verified astrologers read message reactions" ON public.message_reactions;
    DROP POLICY IF EXISTS "Users manage own message reactions" ON public.message_reactions;
    DROP POLICY IF EXISTS "Admins manage message reactions" ON public.message_reactions;
    CREATE POLICY "Verified astrologers read message reactions"
      ON public.message_reactions FOR SELECT TO authenticated
      USING (public.is_verified_astrologer() OR public.is_admin());
    CREATE POLICY "Users manage own message reactions"
      ON public.message_reactions FOR ALL TO authenticated
      USING (user_id::text = auth.uid()::text)
      WITH CHECK ((public.is_verified_astrologer() OR public.is_admin()) AND user_id::text = auth.uid()::text);
    CREATE POLICY "Admins manage message reactions"
      ON public.message_reactions FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_saved_messages') IS NOT NULL THEN
    ALTER TABLE public.community_saved_messages ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users manage own saved messages" ON public.community_saved_messages;
    DROP POLICY IF EXISTS "Admins manage saved messages" ON public.community_saved_messages;
    CREATE POLICY "Users manage own saved messages"
      ON public.community_saved_messages FOR ALL TO authenticated
      USING (user_id::text = auth.uid()::text)
      WITH CHECK ((public.is_verified_astrologer() OR public.is_admin()) AND user_id::text = auth.uid()::text);
    CREATE POLICY "Admins manage saved messages"
      ON public.community_saved_messages FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_read_states') IS NOT NULL THEN
    ALTER TABLE public.community_read_states ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users manage own read states" ON public.community_read_states;
    DROP POLICY IF EXISTS "Admins manage read states" ON public.community_read_states;
    CREATE POLICY "Users manage own read states"
      ON public.community_read_states FOR ALL TO authenticated
      USING (user_id::text = auth.uid()::text)
      WITH CHECK ((public.is_verified_astrologer() OR public.is_admin()) AND user_id::text = auth.uid()::text);
    CREATE POLICY "Admins manage read states"
      ON public.community_read_states FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.thread_follows') IS NOT NULL THEN
    ALTER TABLE public.thread_follows ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users manage own thread follows" ON public.thread_follows;
    DROP POLICY IF EXISTS "Admins manage thread follows" ON public.thread_follows;
    CREATE POLICY "Users manage own thread follows"
      ON public.thread_follows FOR ALL TO authenticated
      USING (user_id::text = auth.uid()::text)
      WITH CHECK ((public.is_verified_astrologer() OR public.is_admin()) AND user_id::text = auth.uid()::text);
    CREATE POLICY "Admins manage thread follows"
      ON public.thread_follows FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_profiles') IS NOT NULL THEN
    ALTER TABLE public.community_profiles ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Verified astrologers read community profiles" ON public.community_profiles;
    DROP POLICY IF EXISTS "Users manage own community profile" ON public.community_profiles;
    DROP POLICY IF EXISTS "Admins manage community profiles" ON public.community_profiles;
    CREATE POLICY "Verified astrologers read community profiles"
      ON public.community_profiles FOR SELECT TO authenticated
      USING (public.is_verified_astrologer() OR public.is_admin());
    CREATE POLICY "Users manage own community profile"
      ON public.community_profiles FOR ALL TO authenticated
      USING (user_id::text = auth.uid()::text)
      WITH CHECK ((public.is_verified_astrologer() OR public.is_admin()) AND user_id::text = auth.uid()::text);
    CREATE POLICY "Admins manage community profiles"
      ON public.community_profiles FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.channel_memberships') IS NOT NULL THEN
    ALTER TABLE public.channel_memberships ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Verified astrologers read channel memberships" ON public.channel_memberships;
    DROP POLICY IF EXISTS "Admins manage channel memberships" ON public.channel_memberships;
    CREATE POLICY "Verified astrologers read channel memberships"
      ON public.channel_memberships FOR SELECT TO authenticated
      USING (public.is_verified_astrologer() OR public.is_admin());
    CREATE POLICY "Admins manage channel memberships"
      ON public.channel_memberships FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_reports') IS NOT NULL THEN
    ALTER TABLE public.community_reports ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Verified astrologers create reports" ON public.community_reports;
    DROP POLICY IF EXISTS "Admins manage community reports" ON public.community_reports;
    CREATE POLICY "Verified astrologers create reports"
      ON public.community_reports FOR INSERT TO authenticated
      WITH CHECK ((public.is_verified_astrologer() OR public.is_admin()) AND reporter_id::text = auth.uid()::text);
    CREATE POLICY "Admins manage community reports"
      ON public.community_reports FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;

  IF to_regclass('public.community_notifications') IS NOT NULL THEN
    ALTER TABLE public.community_notifications ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users read own community notifications" ON public.community_notifications;
    DROP POLICY IF EXISTS "Users update own community notifications" ON public.community_notifications;
    DROP POLICY IF EXISTS "Admins manage community notifications" ON public.community_notifications;
    CREATE POLICY "Users read own community notifications"
      ON public.community_notifications FOR SELECT TO authenticated
      USING (user_id::text = auth.uid()::text OR public.is_admin());
    CREATE POLICY "Users update own community notifications"
      ON public.community_notifications FOR UPDATE TO authenticated
      USING (user_id::text = auth.uid()::text)
      WITH CHECK (user_id::text = auth.uid()::text);
    CREATE POLICY "Admins manage community notifications"
      ON public.community_notifications FOR ALL TO authenticated
      USING (public.is_admin())
      WITH CHECK (public.is_admin());
  END IF;
END $$;

INSERT INTO storage.buckets (id, name, public)
VALUES ('community-proofs', 'community-proofs', false)
ON CONFLICT (id) DO UPDATE SET public = false;

DROP POLICY IF EXISTS "Allow authenticated users to upload proofs" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated users to read proofs" ON storage.objects;
DROP POLICY IF EXISTS "Allow users to update their own proofs" ON storage.objects;
DROP POLICY IF EXISTS "Allow users to delete their own proofs" ON storage.objects;
DROP POLICY IF EXISTS "Users upload own community proofs" ON storage.objects;
DROP POLICY IF EXISTS "Users read own community proofs" ON storage.objects;
DROP POLICY IF EXISTS "Users update own community proofs" ON storage.objects;
DROP POLICY IF EXISTS "Users delete own community proofs" ON storage.objects;
DROP POLICY IF EXISTS "Admins read community proofs" ON storage.objects;

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

CREATE POLICY "Admins read community proofs"
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'community-proofs'
  AND public.is_admin()
);
