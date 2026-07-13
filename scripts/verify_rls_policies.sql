-- Shree Lakshmi Astro RLS verification checklist.
-- Run in Supabase SQL editor after applying migrations through 006.
-- Expected result: the issue queries should return zero rows.

-- 1. Sensitive public tables must have RLS enabled.
SELECT
  'rls_disabled' AS issue,
  schemaname,
  tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
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
  )
  AND NOT rowsecurity
ORDER BY tablename;

-- 2. No anon policies should exist on private/sensitive tables.
SELECT
  'anon_policy_on_sensitive_table' AS issue,
  schemaname,
  tablename,
  policyname,
  roles,
  cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
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
  )
  AND 'anon' = ANY (roles)
ORDER BY tablename, policyname;

-- 3. Broad community application/storage policies must be gone.
SELECT
  'legacy_permissive_policy_present' AS issue,
  schemaname,
  tablename,
  policyname,
  roles,
  cmd
FROM pg_policies
WHERE (schemaname = 'public' AND policyname IN (
    'Allow users to manage their own application',
    'Allow users to manage their own systems',
    'Allow users to manage their own proofs',
    'Allow users to read their own reviews'
  ))
  OR (schemaname = 'storage' AND policyname IN (
    'Allow authenticated users to upload proofs',
    'Allow authenticated users to read proofs'
  ))
ORDER BY schemaname, tablename, policyname;

-- 4. Required auth helper functions and privilege trigger must exist.
SELECT
  'missing_required_auth_object' AS issue,
  required_object
FROM (
  VALUES
    ('function:public.is_admin'),
    ('function:public.is_verified_astrologer'),
    ('function:public.prevent_user_privilege_escalation'),
    ('trigger:public.users.prevent_user_privilege_escalation')
) AS required(required_object)
WHERE NOT EXISTS (
  SELECT 1
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE required_object = 'function:' || n.nspname || '.' || p.proname
)
AND NOT EXISTS (
  SELECT 1
  FROM pg_trigger t
  JOIN pg_class c ON c.oid = t.tgrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE required_object = 'trigger:' || n.nspname || '.' || c.relname || '.' || t.tgname
);

-- 5. Snapshot policies for manual review.
SELECT
  schemaname,
  tablename,
  policyname,
  roles,
  cmd,
  permissive,
  qual,
  with_check
FROM pg_policies
WHERE schemaname IN ('public', 'storage')
  AND (
    tablename IN (
      'users',
      'consultation_requests',
      'paid_consultations',
      'payments',
      'community_applications',
      'community_application_reviews',
      'community_messages',
      'community_reports'
    )
    OR (schemaname = 'storage' AND tablename = 'objects')
  )
ORDER BY schemaname, tablename, policyname;
