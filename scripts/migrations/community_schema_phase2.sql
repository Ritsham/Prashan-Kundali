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
