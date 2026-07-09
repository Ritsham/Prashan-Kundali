-- COMBINED MIGRATION SCRIPT FOR VERIFIED ASTROLOGER COMMUNITY

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



-- Update community_messages for content_type, chart references
ALTER TABLE public.community_messages ADD COLUMN IF NOT EXISTS content_type TEXT DEFAULT 'STANDARD';
ALTER TABLE public.community_messages ADD COLUMN IF NOT EXISTS chart_id UUID;
ALTER TABLE public.community_messages ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT false;
ALTER TABLE public.community_messages ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now());

-- Create message_reactions table
CREATE TABLE IF NOT EXISTS public.message_reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES public.community_messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    reaction_type TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    UNIQUE(message_id, user_id, reaction_type)
);


-- Thread Follows (Phase 3)
CREATE TABLE IF NOT EXISTS public.thread_follows (
    message_id UUID REFERENCES public.community_messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    PRIMARY KEY (message_id, user_id)
);


-- Moderation (Phase 6)
CREATE TABLE IF NOT EXISTS public.community_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES public.community_messages(id) ON DELETE CASCADE,
    reporter_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING', -- PENDING, REVIEWED, DISMISSED, ACTIONED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);


-- Notifications (Phase 7)
CREATE TABLE IF NOT EXISTS public.community_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL, -- e.g., 'THREAD_REPLY', 'REACTION', 'MENTION'
    actor_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    message_id UUID REFERENCES public.community_messages(id) ON DELETE CASCADE,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);


