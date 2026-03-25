"""
utils/embeds.py — All Discord Embed builders in one place
"""

import discord
from datetime import datetime

# Colour palette
C_TEAL    = 0x1ABC9C   # Session start
C_RED     = 0xE74C3C   # Focus / error
C_GREEN   = 0x2ECC71   # Break / success
C_BLUE    = 0x3498DB   # RAG answer
C_PURPLE  = 0x9B59B6   # Quiz
C_GOLD    = 0xF1C40F   # Leaderboard
C_DARK    = 0x2C3E50   # Summary


def session_start(topic: str, focus_mins: int, break_mins: int) -> discord.Embed:
    e = discord.Embed(
        title="📚 Study Session Started",
        description=f"**Topic:** {topic}",
        colour=C_TEAL,
        timestamp=datetime.utcnow(),
    )
    e.add_field(name="⏱ Focus", value=f"{focus_mins} min", inline=True)
    e.add_field(name="☕ Break", value=f"{break_mins} min", inline=True)
    e.set_footer(text="Use /study end to close the session")
    return e


def session_end(topic: str, duration_mins: int) -> discord.Embed:
    e = discord.Embed(
        title="✅ Session Ended",
        description=f"**Topic:** {topic}",
        colour=C_GREEN,
        timestamp=datetime.utcnow(),
    )
    e.add_field(name="Duration", value=f"{duration_mins} min")
    e.set_footer(text="Summary incoming…")
    return e


def pomodoro_focus(cycle: int) -> discord.Embed:
    e = discord.Embed(
        title=f"🔴 Focus Time — Cycle {cycle}",
        description="Stay focused. Notifications paused.",
        colour=C_RED,
    )
    return e


def pomodoro_break(cycle: int) -> discord.Embed:
    e = discord.Embed(
        title=f"🟢 Break Time — Cycle {cycle}",
        description="Take a 5-minute break. Quiz coming up!",
        colour=C_GREEN,
    )
    return e


def rag_answer(question: str, answer: str, citations: list[str]) -> discord.Embed:
    e = discord.Embed(
        title="🔍 Answer",
        description=answer,
        colour=C_BLUE,
        timestamp=datetime.utcnow(),
    )
    e.add_field(name="Question", value=question, inline=False)
    if citations:
        e.set_footer(text="Sources: " + " · ".join(citations))
    return e


def quiz_question(question: str, options: list[str], timeout: int) -> discord.Embed:
    EMOJIS = ["🇦", "🇧", "🇨", "🇩"]
    e = discord.Embed(
        title="❓ Quiz Time!",
        description=f"**{question}**",
        colour=C_PURPLE,
    )
    for emoji, opt in zip(EMOJIS, options):
        e.add_field(name=emoji, value=opt, inline=False)
    e.set_footer(text=f"React with your answer! • {timeout}s to respond")
    return e


def quiz_result(question: str, correct_option: str, explanation: str, scores: dict[str, int]) -> discord.Embed:
    e = discord.Embed(
        title="✅ Quiz Closed",
        description=f"**Q:** {question}\n**Answer:** {correct_option}",
        colour=C_GREEN,
    )
    e.add_field(name="Explanation", value=explanation, inline=False)
    if scores:
        score_text = "\n".join([f"{u}: +{p} pts" for u, p in scores.items()])
        e.add_field(name="Points Awarded", value=score_text, inline=False)
    return e


def leaderboard(rows: list[dict], guild_name: str) -> discord.Embed:
    MEDALS = ["🥇", "🥈", "🥉"]
    e = discord.Embed(
        title=f"🏆 Leaderboard — {guild_name}",
        colour=C_GOLD,
        timestamp=datetime.utcnow(),
    )
    if not rows:
        e.description = "No scores yet. Complete a quiz to appear here!"
        return e

    lines = []
    for i, row in enumerate(rows):
        medal = MEDALS[i] if i < 3 else f"{i+1}."
        acc = f"{row.get('accuracy_pct', 0):.0f}%"
        streak = f"🔥{row['current_streak']}" if row.get("current_streak", 0) > 1 else ""
        lines.append(f"{medal} **{row['username']}** — {row['total_points']} pts | {acc} acc {streak}")
    e.description = "\n".join(lines)
    return e


def session_summary(topic: str, summary_text: str) -> discord.Embed:
    e = discord.Embed(
        title=f"📋 Session Summary — {topic}",
        description=summary_text,
        colour=C_DARK,
        timestamp=datetime.utcnow(),
    )
    return e


def error(msg: str) -> discord.Embed:
    return discord.Embed(title="❌ Error", description=msg, colour=C_RED)


def info(msg: str) -> discord.Embed:
    return discord.Embed(description=msg, colour=C_TEAL)
