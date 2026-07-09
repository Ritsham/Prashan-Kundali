-- Thread Follows (Phase 3)
CREATE TABLE IF NOT EXISTS public.thread_follows (
    message_id UUID REFERENCES public.community_messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    PRIMARY KEY (message_id, user_id)
);
