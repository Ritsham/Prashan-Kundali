-- Phase 2: Database Migration for Community Applications

CREATE TABLE IF NOT EXISTS public.community_applications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL, -- references auth.users(id)
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    mobile_number TEXT NOT NULL,
    state TEXT NOT NULL,
    country TEXT NOT NULL,
    applicant_type TEXT NOT NULL,
    experience_range TEXT NOT NULL,
    background_description TEXT NOT NULL,
    additional_information TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING', -- NOT_APPLIED, PENDING, NEEDS_MORE_INFORMATION, APPROVED, REJECTED, SUSPENDED
    admin_internal_notes TEXT,
    applicant_facing_message TEXT,
    reviewed_by UUID, -- references auth.users(id)
    reviewed_at TIMESTAMP WITH TIME ZONE,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_at TIMESTAMP WITH TIME ZONE,
    suspended_at TIMESTAMP WITH TIME ZONE,
    reapply_allowed BOOLEAN DEFAULT false,
    reapply_after TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS public.community_application_systems (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    application_id UUID NOT NULL REFERENCES public.community_applications(id) ON DELETE CASCADE,
    system_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS public.community_application_proofs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    application_id UUID NOT NULL REFERENCES public.community_applications(id) ON DELETE CASCADE,
    proof_type TEXT NOT NULL,
    file_url TEXT,
    external_url TEXT,
    original_file_name TEXT,
    mime_type TEXT,
    file_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS public.community_application_reviews (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    application_id UUID NOT NULL REFERENCES public.community_applications(id) ON DELETE CASCADE,
    admin_id UUID NOT NULL, -- references auth.users(id)
    previous_status TEXT,
    new_status TEXT NOT NULL,
    internal_note TEXT,
    applicant_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- RLS Policies (Assuming Row Level Security is enabled)
ALTER TABLE public.community_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_application_systems ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_application_proofs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_application_reviews ENABLE ROW LEVEL SECURITY;

-- Update users table with community access fields if they don't exist
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS community_verification_status TEXT DEFAULT 'NOT_APPLIED';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS community_access BOOLEAN DEFAULT false;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS community_verified_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS community_suspended_at TIMESTAMP WITH TIME ZONE;
