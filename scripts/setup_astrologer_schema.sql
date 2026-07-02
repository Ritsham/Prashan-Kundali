-- Run this script in the Supabase SQL Editor

-- 1. Update users table to include role and verification_status
-- Note: Assuming the `users` table exists. If it was created from `database.py` sync_user, it might just have id, email, name, last_sign_in.
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'unverified';

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
