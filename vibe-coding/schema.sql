-- ============================================================
-- Supabase Schema
-- Run this in: Supabase Dashboard > SQL Editor
-- ============================================================

-- 1. news_cards
CREATE TABLE IF NOT EXISTS news_cards (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    date        date        NOT NULL,
    title       text        NOT NULL,
    summary     text,
    image_url   text,
    category    text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE news_cards DISABLE ROW LEVEL SECURITY;

-- 2. ai_diary
CREATE TABLE IF NOT EXISTS ai_diary (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_name  text        NOT NULL,
    date           date        NOT NULL,
    content        text        NOT NULL,
    level          text,
    created_at     timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE ai_diary DISABLE ROW LEVEL SECURITY;
