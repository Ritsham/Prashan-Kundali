-- Community Profiles
CREATE TABLE IF NOT EXISTS public.community_profiles (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT,
    bio TEXT,
    state TEXT,
    country TEXT,
    experience_years TEXT,
    specializations JSONB DEFAULT '[]'::jsonb,
    languages JSONB DEFAULT '[]'::jsonb,
    systems_practiced JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Community Channels (add UUID, slug, description, category, channel_type)
-- If community_channels exists without an id column, we might need to recreate or alter it.
-- We assume it currently has just 'name'. We'll try to add columns.
ALTER TABLE public.community_channels ADD COLUMN IF NOT EXISTS id UUID PRIMARY KEY DEFAULT gen_random_uuid();
ALTER TABLE public.community_channels ADD COLUMN IF NOT EXISTS slug TEXT UNIQUE;
ALTER TABLE public.community_channels ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.community_channels ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE public.community_channels ADD COLUMN IF NOT EXISTS channel_type TEXT DEFAULT 'PUBLIC';
ALTER TABLE public.community_channels ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES public.users(id);
ALTER TABLE public.community_channels ADD COLUMN IF NOT EXISTS member_count INT DEFAULT 0;
ALTER TABLE public.community_channels ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now());

-- Channel Memberships
CREATE TABLE IF NOT EXISTS public.channel_memberships (
    channel_id UUID REFERENCES public.community_channels(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'MEMBER',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    PRIMARY KEY (channel_id, user_id)
);

-- Make sure RLS is enabled and policies are setup if needed (skipped for now, assuming anon/authenticated usage is handled by Supabase default or existing policies)

