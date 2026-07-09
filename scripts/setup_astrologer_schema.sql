-- Run this script in the Supabase SQL Editor

-- 1. Update users table to include role and verification_status
-- Note: Assuming the `users` table exists. If it was created from `database.py` sync_user, it might just have id, email, name, last_sign_in.
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'none';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS community_access BOOLEAN DEFAULT FALSE;

-- 2. Create astrologer_profiles table
CREATE TABLE IF NOT EXISTS public.astrologer_profiles (
    user_id UUID PRIMARY KEY, -- Should ideally reference auth.users or public.users, depending on setup
    experience_years INTEGER NOT NULL,
    expertise_areas TEXT[] NOT NULL,
    social_links JSONB,
    bio TEXT,
    reputation_score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Set RLS policies (Optional but recommended)
-- ALTER TABLE public.astrologer_profiles ENABLE ROW LEVEL SECURITY;

-- 4. Community-specific application and membership tables.
-- These keep Astro Community access separate from the generic users table.
CREATE TABLE IF NOT EXISTS public.community_applications (
    user_id UUID PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    display_name TEXT,
    professional_headline TEXT,
    short_biography TEXT,
    years_of_experience INTEGER,
    astrology_systems TEXT[] DEFAULT ARRAY[]::TEXT[],
    specializations TEXT[] DEFAULT ARRAY[]::TEXT[],
    techniques_practiced TEXT[] DEFAULT ARRAY[]::TEXT[],
    languages TEXT[] DEFAULT ARRAY[]::TEXT[],
    reason_for_joining TEXT,
    sample_astrology_analysis TEXT,
    professional_links JSONB DEFAULT '{}'::JSONB,
    supporting_document_name TEXT,
    supporting_document_link TEXT,
    submitted_at TIMESTAMPTZ,
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.community_memberships (
    user_id UUID PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    suspended_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.community_application_status_history (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    status TEXT NOT NULL,
    changed_by UUID,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.app_visit_events (
    id TEXT PRIMARY KEY,
    visitor_key TEXT NOT NULL,
    user_id UUID,
    path TEXT NOT NULL,
    referrer TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
