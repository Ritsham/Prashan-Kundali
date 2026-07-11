-- Moderation (Phase 6)
CREATE TABLE IF NOT EXISTS public.community_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES public.community_messages(id) ON DELETE CASCADE,
    reporter_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING', -- PENDING, REVIEWED, DISMISSED, ACTIONED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
