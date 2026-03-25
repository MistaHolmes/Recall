-- db/schema.sql — Canonical PostgreSQL DDL

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ──────────────────────────────────────────
-- Users
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id  BIGINT UNIQUE NOT NULL,
    username    TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────
-- Study Sessions
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guild_id    BIGINT NOT NULL,
    channel_id  BIGINT NOT NULL,
    topic       TEXT NOT NULL,
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,                -- NULL = still active
    summary     TEXT,
    creator_id  UUID REFERENCES users(id)
);

-- ──────────────────────────────────────────
-- Quiz Scores
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_scores (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID REFERENCES sessions(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id),
    question    TEXT NOT NULL,
    correct     BOOLEAN NOT NULL,
    points      INTEGER DEFAULT 0,
    answered_at TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────
-- Streaks
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS streaks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    guild_id        BIGINT NOT NULL,
    current_streak  INTEGER DEFAULT 0,
    longest_streak  INTEGER DEFAULT 0,
    last_active     DATE DEFAULT CURRENT_DATE,
    UNIQUE(user_id, guild_id)
);

-- ──────────────────────────────────────────
-- Leaderboard View
-- ──────────────────────────────────────────
CREATE OR REPLACE VIEW leaderboard AS
SELECT
    u.discord_id,
    u.username,
    s.guild_id,
    COALESCE(SUM(q.points), 0)                                          AS total_points,
    COUNT(q.id)                                                          AS total_quizzes,
    ROUND(AVG(CASE WHEN q.correct THEN 1.0 ELSE 0.0 END) * 100, 1)     AS accuracy_pct,
    COALESCE(st.current_streak, 0)                                       AS current_streak,
    COALESCE(st.longest_streak, 0)                                       AS longest_streak
FROM users u
LEFT JOIN quiz_scores q  ON u.id = q.user_id
LEFT JOIN sessions s     ON q.session_id = s.id
LEFT JOIN streaks st     ON u.id = st.user_id AND s.guild_id = st.guild_id
GROUP BY u.discord_id, u.username, s.guild_id, st.current_streak, st.longest_streak
ORDER BY total_points DESC;
