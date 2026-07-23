-- Revoke direct anon/public table privileges left by earlier permissive grants.
-- RLS policies still govern authenticated users; service_role continues to bypass
-- RLS for backend-only operations.

DO $$
DECLARE
  table_name text;
  sensitive_tables text[] := ARRAY[
    'users',
    'prashna_charts',
    'lagna_charts',
    'consultation_requests',
    'paid_consultations',
    'consultant_bookings',
    'consultant_messages',
    'match_requests',
    'match_participants',
    'match_reports',
    'consultation_attachments',
    'payments',
    'admin_logs',
    'app_visit_events',
    'consultant_platform_stats',
    'astrologer_profiles',
    'community_applications',
    'community_application_systems',
    'community_application_proofs',
    'community_application_reviews',
    'community_memberships',
    'community_application_status_history',
    'community_channels',
    'community_messages',
    'community_threads',
    'message_reactions',
    'community_saved_messages',
    'community_read_states',
    'thread_follows',
    'community_profiles',
    'channel_memberships',
    'community_reports',
    'community_notifications'
  ];
BEGIN
  FOREACH table_name IN ARRAY sensitive_tables LOOP
    IF to_regclass(format('public.%I', table_name)) IS NOT NULL THEN
      EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE public.%I FROM anon', table_name);
      EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE public.%I FROM PUBLIC', table_name);
      EXECUTE format('REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLE public.%I FROM authenticated', table_name);
      EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO authenticated', table_name);
    END IF;
  END LOOP;

  IF to_regclass('public.consultation_requests') IS NOT NULL THEN
    DROP POLICY IF EXISTS "Allow public inserts" ON public.consultation_requests;
  END IF;
END;
$$;
