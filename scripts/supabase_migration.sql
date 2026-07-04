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
    'Founder astrologer at Prashna Astro, focused on practical guidance through Birth Chart, Prashna Kundali, prediction analysis, and case-based consultation.',
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
