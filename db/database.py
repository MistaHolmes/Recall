"""
db/database.py — asyncpg connection pool and all DB helpers
"""

import asyncpg
import logging
from contextlib import asynccontextmanager
from config import config

log = logging.getLogger("db")

_pool: asyncpg.Pool | None = None


async def init_db():
    """Create connection pool and ensure schema exists."""
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=config.DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    # Apply schema
    schema = open("db/schema.sql").read()
    async with _pool.acquire() as conn:
        await conn.execute(schema)
    log.info("Database pool initialized")


async def close_db():
    global _pool
    if _pool:
        await _pool.close()


@asynccontextmanager
async def get_conn():
    async with _pool.acquire() as conn:
        yield conn


# ── Users ────────────────────────────────────────────────────────────────────

async def upsert_user(discord_id: int, username: str) -> str:
    """Create user if not exists, return internal UUID."""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (discord_id, username)
            VALUES ($1, $2)
            ON CONFLICT (discord_id) DO UPDATE SET username = EXCLUDED.username
            RETURNING id
            """,
            discord_id, username,
        )
        return str(row["id"])


async def get_user_id(discord_id: int) -> str | None:
    async with get_conn() as conn:
        row = await conn.fetchrow("SELECT id FROM users WHERE discord_id = $1", discord_id)
        return str(row["id"]) if row else None


# ── Sessions ─────────────────────────────────────────────────────────────────

async def create_session(guild_id: int, channel_id: int, topic: str, creator_discord_id: int) -> str:
    user_id = await get_user_id(creator_discord_id)
    async with get_conn() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO sessions (guild_id, channel_id, topic, creator_id)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            guild_id, channel_id, topic, user_id,
        )
        return str(row["id"])


async def end_session(session_id: str, summary: str | None = None):
    async with get_conn() as conn:
        await conn.execute(
            "UPDATE sessions SET ended_at = NOW(), summary = $1 WHERE id = $2",
            summary, session_id,
        )


async def get_active_session(guild_id: int) -> dict | None:
    async with get_conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM sessions WHERE guild_id = $1 AND ended_at IS NULL",
            guild_id,
        )
        return dict(row) if row else None


# ── Quiz Scores ───────────────────────────────────────────────────────────────

async def record_quiz_answer(session_id: str, discord_id: int, question: str, correct: bool):
    points = 10 if correct else 0
    user_id = await get_user_id(discord_id)
    async with get_conn() as conn:
        await conn.execute(
            """
            INSERT INTO quiz_scores (session_id, user_id, question, correct, points)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT DO NOTHING
            """,
            session_id, user_id, question, correct, points,
        )
    return points


# ── Streaks ──────────────────────────────────────────────────────────────────

async def update_streak(discord_id: int, guild_id: int):
    user_id = await get_user_id(discord_id)
    async with get_conn() as conn:
        row = await conn.fetchrow(
            "SELECT current_streak, longest_streak, last_active FROM streaks WHERE user_id = $1 AND guild_id = $2",
            user_id, guild_id,
        )
        from datetime import date, timedelta
        today = date.today()

        if not row:
            await conn.execute(
                "INSERT INTO streaks (user_id, guild_id, current_streak, longest_streak, last_active) VALUES ($1, $2, 1, 1, $3)",
                user_id, guild_id, today,
            )
        else:
            last = row["last_active"]
            cur = row["current_streak"]
            lng = row["longest_streak"]

            if last == today:
                return  # Already counted today
            elif last == today - timedelta(days=1):
                cur += 1
            else:
                cur = 1

            lng = max(lng, cur)
            await conn.execute(
                "UPDATE streaks SET current_streak=$1, longest_streak=$2, last_active=$3 WHERE user_id=$4 AND guild_id=$5",
                cur, lng, today, user_id, guild_id,
            )


# ── Leaderboard ───────────────────────────────────────────────────────────────

async def get_leaderboard(guild_id: int, limit: int = 10) -> list[dict]:
    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT username, total_points, total_quizzes, accuracy_pct, current_streak
            FROM leaderboard
            WHERE guild_id = $1
            ORDER BY total_points DESC
            LIMIT $2
            """,
            guild_id, limit,
        )
        return [dict(r) for r in rows]
