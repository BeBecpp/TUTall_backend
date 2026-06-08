-- TUTall Backend — Supabase Postgres schema
-- Run in Supabase SQL Editor or via init_db() on startup.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(120) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id VARCHAR(120) NOT NULL,
    topic VARCHAR(120) NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 0),
    total INTEGER NOT NULL CHECK (total >= 1),
    percentage INTEGER NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_progress_student_id
    ON learning_progress (student_id);

CREATE INDEX IF NOT EXISTS idx_learning_progress_created_at
    ON learning_progress (created_at DESC);

CREATE TABLE IF NOT EXISTS scholarship_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grade_level VARCHAR(80) NOT NULL,
    gpa NUMERIC(4, 2) NOT NULL CHECK (gpa >= 0 AND gpa <= 4),
    country VARCHAR(80) NOT NULL,
    intended_major VARCHAR(120) NOT NULL,
    english_level VARCHAR(80) NOT NULL,
    financial_need VARCHAR(20) NOT NULL,
    activities TEXT NOT NULL DEFAULT '',
    has_essay BOOLEAN NOT NULL DEFAULT FALSE,
    has_english_test BOOLEAN NOT NULL DEFAULT FALSE,
    readiness_score INTEGER NOT NULL CHECK (readiness_score >= 0 AND readiness_score <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scholarship_profiles_created_at
    ON scholarship_profiles (created_at DESC);

CREATE TABLE IF NOT EXISTS ai_request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint VARCHAR(120) NOT NULL,
    topic VARCHAR(200),
    source VARCHAR(40) NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_code VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_request_logs_endpoint
    ON ai_request_logs (endpoint);

CREATE INDEX IF NOT EXISTS idx_ai_request_logs_created_at
    ON ai_request_logs (created_at DESC);
