-- Realtime Astro Community chat features.
-- Run in Supabase SQL Editor.

ALTER TABLE public.community_channels
  ADD COLUMN IF NOT EXISTS slug TEXT,
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS category TEXT,
  ADD COLUMN IF NOT EXISTS channel_type TEXT NOT NULL DEFAULT 'PUBLIC',
  ADD COLUMN IF NOT EXISTS is_read_only BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS allow_threads BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS allow_reactions BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS topic TEXT,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE public.community_channels
SET slug = lower(regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g'))
WHERE slug IS NULL;

ALTER TABLE public.community_messages
  ADD COLUMN IF NOT EXISTS sender_id TEXT,
  ADD COLUMN IF NOT EXISTS client_id TEXT,
  ADD COLUMN IF NOT EXISTS content_type TEXT NOT NULL DEFAULT 'STANDARD',
  ADD COLUMN IF NOT EXISTS chart_id TEXT,
  ADD COLUMN IF NOT EXISTS reply_to_message_id TEXT REFERENCES public.community_messages(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS edited_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_community_messages_channel_created
ON public.community_messages (channel_name, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_community_messages_client_id
ON public.community_messages (client_id)
WHERE client_id IS NOT NULL;

ALTER TABLE public.community_threads
  ADD COLUMN IF NOT EXISTS sender_id TEXT,
  ADD COLUMN IF NOT EXISTS channel_name TEXT,
  ADD COLUMN IF NOT EXISTS edited_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS public.message_reactions (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL REFERENCES public.community_messages(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  reaction_type TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(message_id, user_id, reaction_type)
);

CREATE TABLE IF NOT EXISTS public.community_saved_messages (
  message_id TEXT NOT NULL REFERENCES public.community_messages(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (message_id, user_id)
);

CREATE TABLE IF NOT EXISTS public.community_read_states (
  channel_name TEXT NOT NULL,
  user_id TEXT NOT NULL,
  last_read_message_id TEXT,
  last_read_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (channel_name, user_id)
);

INSERT INTO public.community_channels (
  id,
  name,
  slug,
  description,
  category,
  channel_type,
  is_read_only,
  allow_threads,
  allow_reactions,
  topic
)
VALUES
  ('announcements', 'announcements', 'announcements', 'Admin updates and platform notices.', 'Important', 'PUBLIC', TRUE, TRUE, TRUE, 'Official announcements for the verified astrologer community.'),
  ('community-guidelines', 'community-guidelines', 'community-guidelines', 'Shared norms for respectful learning and case privacy.', 'Important', 'PUBLIC', TRUE, TRUE, TRUE, 'Rules, ethics, privacy, and posting standards.'),
  ('general', 'general', 'general', 'Daily discussion for verified astrologers.', 'General Community', 'PUBLIC', FALSE, TRUE, TRUE, 'Open daily professional conversation.'),
  ('introductions', 'introductions', 'introductions', 'Meet practitioners and share your background.', 'General Community', 'PUBLIC', FALSE, TRUE, TRUE, 'New member introductions.'),
  ('general-discussion', 'general-discussion', 'general-discussion', 'Open questions, observations, and peer review.', 'General Community', 'PUBLIC', FALSE, TRUE, TRUE, 'General astrology discussion and peer learning.'),
  ('parashar-astrology', 'parashar-astrology', 'parashar-astrology', 'Classical principles, yogas, dashas, and house judgement.', 'Astrology Systems', 'PUBLIC', FALSE, TRUE, TRUE, 'Parashar astrology practice and interpretation.'),
  ('kp-astrology', 'kp-astrology', 'kp-astrology', 'KP significators, ruling planets, and cuspal analysis.', 'Astrology Systems', 'PUBLIC', FALSE, TRUE, TRUE, 'KP astrology methods and case work.'),
  ('jaimini-astrology', 'jaimini-astrology', 'jaimini-astrology', 'Karakas, rashi drishti, padas, and chara dashas.', 'Astrology Systems', 'PUBLIC', FALSE, TRUE, TRUE, 'Jaimini principles and research.'),
  ('nadi-astrology', 'nadi-astrology', 'nadi-astrology', 'Nadi combinations and research notes.', 'Astrology Systems', 'PUBLIC', FALSE, TRUE, TRUE, 'Nadi techniques and combinations.'),
  ('tajika-astrology', 'tajika-astrology', 'tajika-astrology', 'Varshaphal, muntha, saham, and tajika yogas.', 'Astrology Systems', 'PUBLIC', FALSE, TRUE, TRUE, 'Tajika and annual chart discussions.'),
  ('prashna-astrology', 'prashna-astrology', 'prashna-astrology', 'Question charts, timing, and event judgement.', 'Kundali and Prediction', 'PUBLIC', FALSE, TRUE, TRUE, 'Prashna chart judgement and timing.'),
  ('lagna-kundali', 'lagna-kundali', 'lagna-kundali', 'Birth chart analysis and rectification support.', 'Kundali and Prediction', 'PUBLIC', FALSE, TRUE, TRUE, 'Natal chart analysis and lagna-focused interpretation.'),
  ('chart-discussions', 'chart-discussions', 'chart-discussions', 'Share charts, compare methods, and discuss outcomes.', 'Kundali and Prediction', 'PUBLIC', FALSE, TRUE, TRUE, 'Anonymized chart discussion and peer review.'),
  ('marriage-matching', 'marriage-matching', 'marriage-matching', 'Compatibility, guna milan, and relationship timing.', 'Kundali and Prediction', 'PUBLIC', FALSE, TRUE, TRUE, 'Marriage matching and relationship astrology.'),
  ('muhurta', 'muhurta', 'muhurta', 'Electional astrology and auspicious timings.', 'Kundali and Prediction', 'PUBLIC', FALSE, TRUE, TRUE, 'Muhurta selection and electional methods.'),
  ('case-studies', 'case-studies', 'case-studies', 'Anonymized cases, peer review, and documented predictions.', 'Learning and Research', 'PUBLIC', FALSE, TRUE, TRUE, 'Case studies with privacy-safe details.'),
  ('techniques-and-learning', 'techniques-and-learning', 'techniques-and-learning', 'Frameworks, lessons, and guided learning notes.', 'Learning and Research', 'PUBLIC', FALSE, TRUE, TRUE, 'Learning material, methods, and debates.'),
  ('research-and-books', 'research-and-books', 'research-and-books', 'Texts, references, translations, and research papers.', 'Learning and Research', 'PUBLIC', FALSE, TRUE, TRUE, 'Books, references, and research resources.')
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  slug = EXCLUDED.slug,
  description = EXCLUDED.description,
  category = EXCLUDED.category,
  channel_type = EXCLUDED.channel_type,
  is_read_only = EXCLUDED.is_read_only,
  allow_threads = EXCLUDED.allow_threads,
  allow_reactions = EXCLUDED.allow_reactions,
  topic = EXCLUDED.topic,
  updated_at = NOW();
