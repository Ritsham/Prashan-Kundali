-- Migration script for Prashna Kundali Backend (SQLite -> PostgreSQL)
-- Run this in your Supabase SQL Editor

-- ==========================================
-- COMMUNITY SCHEMA
-- ==========================================

CREATE TABLE IF NOT EXISTS community_channels (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS community_messages (
    id TEXT PRIMARY KEY,
    channel_name TEXT NOT NULL,
    user_name TEXT NOT NULL,
    content TEXT NOT NULL,
    image_base64 TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    stars INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS community_threads (
    id TEXT PRIMARY KEY,
    parent_message_id TEXT NOT NULL REFERENCES community_messages(id) ON DELETE CASCADE,
    user_name TEXT NOT NULL,
    content TEXT NOT NULL,
    image_base64 TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Astro Community access is managed separately from generic users.
CREATE TABLE IF NOT EXISTS community_applications (
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

CREATE TABLE IF NOT EXISTS community_memberships (
    user_id UUID PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    suspended_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS astrologer_community_profiles (
    user_id UUID PRIMARY KEY,
    username TEXT UNIQUE,
    display_name TEXT,
    professional_headline TEXT,
    biography TEXT,
    profile_photo_url TEXT,
    years_of_experience INTEGER,
    astrology_systems TEXT[] DEFAULT ARRAY[]::TEXT[],
    specializations TEXT[] DEFAULT ARRAY[]::TEXT[],
    techniques_practiced TEXT[] DEFAULT ARRAY[]::TEXT[],
    languages TEXT[] DEFAULT ARRAY[]::TEXT[],
    professional_links JSONB DEFAULT '{}'::JSONB,
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS community_application_status_history (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    status TEXT NOT NULL,
    changed_by UUID,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_community_applications_status
ON community_applications (status, submitted_at);

-- Seed default channels
INSERT INTO community_channels (id, name) VALUES 
('chan_default_general', 'general'),
('chan_default_case_study', 'case study'),
('chan_default_kp_astro', 'kp astrology'),
('chan_default_prashar', 'prashar astrology')
ON CONFLICT (name) DO NOTHING;


-- ==========================================
-- CONSULTATION SCHEMA
-- ==========================================

CREATE TABLE IF NOT EXISTS paid_consultations (
    id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    user_email TEXT NOT NULL,
    question_text TEXT NOT NULL,
    astrological_snapshot TEXT NOT NULL,
    whatsapp_no TEXT,
    gender TEXT,
    birth_date TEXT,
    birth_time TEXT,
    birth_place TEXT,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    payment_ref TEXT,
    amount REAL NOT NULL DEFAULT 299.0,
    created_at TIMESTAMPTZ NOT NULL,
    sla_deadline TIMESTAMPTZ NOT NULL,
    answered_at TIMESTAMPTZ,
    answer_text TEXT
);

CREATE TABLE IF NOT EXISTS consultant_platform_stats (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_queue_size INTEGER NOT NULL DEFAULT 0,
    max_capacity INTEGER NOT NULL DEFAULT 20,
    total_platform_earnings REAL NOT NULL DEFAULT 0.0,
    consultant_earnings REAL NOT NULL DEFAULT 0.0
);

-- Seed default stats
INSERT INTO consultant_platform_stats (id, current_queue_size, max_capacity, total_platform_earnings, consultant_earnings)
VALUES (1, 0, 20, 0.0, 0.0)
ON CONFLICT (id) DO NOTHING;

-- ==========================================
-- ADMIN ANALYTICS
-- ==========================================

CREATE TABLE IF NOT EXISTS app_visit_events (
    id TEXT PRIMARY KEY,
    visitor_key TEXT NOT NULL,
    user_id UUID,
    path TEXT NOT NULL,
    referrer TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_visit_events_created
ON app_visit_events (created_at);

CREATE INDEX IF NOT EXISTS idx_app_visit_events_visitor_created
ON app_visit_events (visitor_key, created_at);

-- ==========================================
-- FOUNDER CONSULTATION REQUEST MVP
-- ==========================================

CREATE TABLE IF NOT EXISTS consultants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    photo_url TEXT,
    bio TEXT,
    experience TEXT,
    systems TEXT[],
    languages TEXT[],
    consultation_fee REAL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS consultation_requests (
    id TEXT PRIMARY KEY,
    user_id UUID,
    consultant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    time_of_birth TEXT NOT NULL,
    place_of_birth TEXT NOT NULL,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    preferred_time TEXT,
    payment_status TEXT NOT NULL DEFAULT 'not_paid',
    status TEXT NOT NULL DEFAULT 'pending',
    queue_number INTEGER,
    meeting_link TEXT,
    scheduled_at TEXT,
    admin_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consultation_requests_status_created
ON consultation_requests (status, created_at);

-- ==========================================
-- KUNDALI MATCH MAKING
-- ==========================================

CREATE TABLE IF NOT EXISTS birth_profiles (
    id TEXT PRIMARY KEY,
    user_id UUID,
    name TEXT NOT NULL,
    gender TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    time_of_birth TEXT,
    birth_time_accuracy TEXT NOT NULL DEFAULT 'exact',
    birth_place TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    timezone TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS match_requests (
    id TEXT PRIMARY KEY,
    user_id UUID,
    status TEXT NOT NULL DEFAULT 'calculated',
    boy_name TEXT NOT NULL,
    girl_name TEXT NOT NULL,
    guna_score REAL NOT NULL DEFAULT 0,
    max_score REAL NOT NULL DEFAULT 36,
    result_category TEXT NOT NULL,
    report_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS match_participants (
    id TEXT PRIMARY KEY,
    match_request_id TEXT NOT NULL REFERENCES match_requests(id) ON DELETE CASCADE,
    birth_profile_id TEXT REFERENCES birth_profiles(id),
    role TEXT NOT NULL,
    details_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kundali_charts (
    id TEXT PRIMARY KEY,
    match_request_id TEXT REFERENCES match_requests(id) ON DELETE CASCADE,
    participant_role TEXT,
    chart_type TEXT NOT NULL,
    chart_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS planetary_positions (
    id BIGSERIAL PRIMARY KEY,
    chart_id TEXT NOT NULL REFERENCES kundali_charts(id) ON DELETE CASCADE,
    planet_name TEXT NOT NULL,
    longitude DOUBLE PRECISION,
    sign TEXT,
    sign_index INTEGER,
    house INTEGER,
    nakshatra TEXT,
    pada INTEGER,
    retrograde BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS ashtakoota_results (
    id BIGSERIAL PRIMARY KEY,
    match_request_id TEXT NOT NULL REFERENCES match_requests(id) ON DELETE CASCADE,
    koota_name TEXT NOT NULL,
    score REAL NOT NULL,
    max_score REAL NOT NULL,
    status TEXT NOT NULL,
    interpretation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dosha_results (
    id BIGSERIAL PRIMARY KEY,
    match_request_id TEXT NOT NULL REFERENCES match_requests(id) ON DELETE CASCADE,
    dosha_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    review_recommended BOOLEAN NOT NULL DEFAULT FALSE,
    explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS match_reports (
    id TEXT PRIMARY KEY,
    match_request_id TEXT NOT NULL REFERENCES match_requests(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL DEFAULT 'basic',
    report_json JSONB NOT NULL,
    pdf_url TEXT,
    status TEXT NOT NULL DEFAULT 'ready',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS consultation_attachments (
    id TEXT PRIMARY KEY,
    consultation_id TEXT NOT NULL,
    match_request_id TEXT REFERENCES match_requests(id),
    attachment_type TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    consultation_id TEXT,
    user_id UUID,
    consultant_id TEXT NOT NULL,
    booking_type TEXT NOT NULL DEFAULT 'matchmaking',
    scheduled_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    user_id UUID,
    booking_id TEXT,
    match_request_id TEXT,
    amount REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'not_paid',
    provider TEXT,
    provider_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS astrologer_reviews (
    id TEXT PRIMARY KEY,
    match_request_id TEXT REFERENCES match_requests(id),
    consultation_id TEXT,
    astrologer_id TEXT NOT NULL,
    notes TEXT,
    final_opinion TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_logs (
    id BIGSERIAL PRIMARY KEY,
    actor_user_id UUID,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    before_json JSONB,
    after_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_match_requests_user_created
ON match_requests (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_match_requests_status_created
ON match_requests (status, created_at DESC);

INSERT INTO consultants (
    id,
    name,
    photo_url,
    bio,
    experience,
    systems,
    languages,
    consultation_fee,
    is_active
) VALUES (
    'founder-rupesh-kumar',
    'Rupesh Kumar',
    'https://www.shanitemple.com/index_images/astrology-puja/janamkundli.png',
    'Founder astrologer at Shree Lakshmi Astro, focused on practical guidance through Birth Chart, Prashna Kundali, prediction analysis, and case-based consultation.',
    '3+ years',
    ARRAY['Vedic Astrology', 'Prashna Kundali', 'Lagna Kundali', 'KP-oriented analysis'],
    ARRAY['Hindi', 'English'],
    NULL,
    TRUE
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    photo_url = EXCLUDED.photo_url,
    bio = EXCLUDED.bio,
    experience = EXCLUDED.experience,
    systems = EXCLUDED.systems,
    languages = EXCLUDED.languages,
    consultation_fee = EXCLUDED.consultation_fee,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();
