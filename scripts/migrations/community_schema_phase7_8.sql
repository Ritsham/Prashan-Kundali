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
