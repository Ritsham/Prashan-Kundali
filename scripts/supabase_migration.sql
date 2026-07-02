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
