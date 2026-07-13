# Shree Lakshmi Astro Database Security Review

This review documents the intended Supabase RLS model after applying `scripts/migrations/006_rls_policy_hardening.sql`.

Roles:

- `user`: authenticated customer.
- `astrologer_pending`: applicant or unverified astrologer.
- `astrologer_verified`: verified community astrologer.
- `admin`: operational administrator.
- Service role: backend only; never exposed to browser code.

## Table-by-Table RLS Matrix

| Table | Select | Insert | Update | Delete | Admin-only | Owner-only | Participant-only |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `users` | Own row, admins | Own row with `role='user'` only | Own non-privileged profile fields, admins | Admins | Role, verification, community access fields | Profile self-management | No |
| `prashna_charts` | Owner, admins | Owner | Owner, admins | Owner, admins | Cross-user reads/management | User charts | No |
| `lagna_charts` | Owner, admins | Owner | Owner, admins | Owner, admins | Cross-user reads/management | User charts | No |
| `consultation_requests` | Owner, matching auth email, assigned astrologer, admins | Owner | Admins | Admins | Status, assignment, schedule, admin notes | Case creation/read | Yes |
| `paid_consultations` | Owner by `user_id`/email, admins | Backend/service | Admins/service | Admins/service | Queue/SLA/answer/payment state | User read | Yes, user side only |
| `consultant_bookings` | Booking owner/email, admins | Booking owner | Admins | Admins | Operational changes | Booking creation/read | Yes, booking owner |
| `consultant_messages` | Booking owner/email, admins | Booking owner as `sender_role='user'`, admins | Admins | Admins | Astrologer/admin messages and moderation | User-authored message creation | Yes |
| `match_requests` | Owner, admins | Owner | Admins | Admins | Status/report changes | Match request creation/read | No |
| `match_participants` | Parent match owner, admins | Parent match owner | Admins | Admins | Cross-match management | Parent match owner | No |
| `match_reports` | Parent match owner, admins | Backend/service | Admins | Admins | Report generation/publishing | Parent match owner read | No |
| `consultation_attachments` | Consultation participant, parent match owner, admins | Backend/service | Admins | Admins | Attachment writes | Parent owner read | Yes |
| `payments` | Owner, admins | Owner with initial unpaid/created status | Admins/service | Admins/service | Payment status/provider reconciliation | Payment creation/read | No |
| `admin_logs` | Admins | Admins/service | No normal updates | No normal deletes | All access | No | No |
| `app_visit_events` | Admins | Authenticated own/null user event, backend/service | No normal updates | No normal deletes | Analytics reads | Own event insert only | No |
| `consultant_platform_stats` | Admins/service | Admins/service | Admins/service | Admins/service | All access | No | No |
| `astrologer_profiles` | Owner, admins | Owner | Owner, admins | Admins | Cross-user profile review | Own profile | No |
| `community_applications` | Admins direct; applicant status is served by backend redacted API | Applicant may insert own pending application; backend/service for full workflow | Admins/service | Admins/service | Approval/rejection/review fields | Application creation | No |
| `community_application_systems` | Admins direct | Applicant may insert systems linked to own application; backend/service | Admins/service | Admins/service | Review workflow | Own application systems | No |
| `community_application_proofs` | Admins direct | Applicant may insert proofs linked to own application; backend/service | Admins/service | Admins/service | Review workflow | Own application proofs | No |
| `community_application_reviews` | Admins direct | Applicant may add more-info response only while application needs info; admins/service | Admins/service | Admins/service | Review history and internal notes | More-info response insert only | No |
| `community_memberships` | Own membership, admins | Admins/service | Admins/service | Admins/service | Grant/suspend membership | Own status read | No |
| `community_application_status_history` | Own history, admins | Admins/service | Admins/service | Admins/service | Status history writes | Own status read | No |
| `community_channels` | Verified astrologers, admins | Admins | Admins | Admins | Channel configuration | No | Verified community only |
| `community_messages` | Verified astrologers, admins | Verified astrologer/admin as self | Message owner, admins | Message owner, admins | Moderation/pinning/cross-user changes | Own messages | Verified community only |
| `community_threads` | Verified astrologers, admins | Verified astrologer/admin as self | Thread owner, admins | Thread owner, admins | Moderation | Own thread replies | Verified community only |
| `message_reactions` | Verified astrologers, admins | Own reaction as verified/admin | Own reaction, admins | Own reaction, admins | Cross-user reaction cleanup | Own reactions | Verified community only |
| `community_saved_messages` | Own saved rows, admins | Own saved rows | Own saved rows, admins | Own saved rows, admins | Cross-user saved rows | Own saved rows | Verified community only |
| `community_read_states` | Own read states, admins | Own read states | Own read states, admins | Own read states, admins | Cross-user read state | Own read state | Verified community only |
| `thread_follows` | Own follows, admins | Own follows | Own follows, admins | Own follows, admins | Cross-user follows | Own follows | Verified community only |
| `community_profiles` | Verified astrologers, admins | Own profile as verified/admin | Own profile, admins | Own profile, admins | Moderation/cross-user management | Own community profile | Verified community only |
| `channel_memberships` | Verified astrologers, admins | Admins/service | Admins/service | Admins/service | Channel membership changes | No direct self-grant | Verified community only |
| `community_reports` | Admins | Verified astrologer/admin as reporter | Admins | Admins | Moderation queue | Own report creation | Verified community only |
| `community_notifications` | Notification owner, admins | Admins/service | Notification owner marks read, admins | Admins/service | Cross-user notification creation | Own notifications | No |
| `community-proofs` storage bucket | File owner by first path segment, admins | File owner by first path segment | File owner by first path segment | File owner by first path segment | Admin review reads | Own proof files | No |

## Key Fixes

- Broad community application policies that allowed applicants to manage whole rows are replaced.
- Broad storage policies that allowed any authenticated user to read/upload proof files are replaced with owner-folder policies.
- User role and verification fields are protected by a database trigger.
- Consultation and matchmaking rows are owner/participant scoped.
- Payment status updates are reserved for admin/service flows after backend verification.
- Community content is limited to verified astrologers and admins.

## Known Deployment Checks

Run `scripts/verify_rls_policies.sql` after applying migrations. The first four result sets should return zero issue rows, and the final result set is a policy snapshot for manual review.

Supabase RLS cannot hide individual columns within a table policy. Applicant-facing application status is therefore served through the backend, which redacts internal review fields before returning data to users.
