"""
cogs/study.py — /study start, /study end, Pomodoro loop
"""

import asyncio
import logging
import discord
from datetime import datetime
from discord import app_commands
from discord.ext import commands
from db.database import create_session, end_session, update_streak, get_leaderboard
from ai.summarizer import generate_summary
from utils import embeds
from config import config

log = logging.getLogger("cog.study")


class StudyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /study ────────────────────────────────────────────────────────────────

    study_group = app_commands.Group(name="study", description="Study session commands")

    @study_group.command(name="start", description="Start a new study session with Pomodoro timer")
    @app_commands.describe(topic="What are you studying today?")
    async def study_start(self, interaction: discord.Interaction, topic: str):
        guild_id = interaction.guild_id

        if guild_id in self.bot.active_sessions:
            return await interaction.response.send_message(
                embed=embeds.error("A session is already running. Use `/study end` first."),
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True)

        # Register user and create DB session
        from db.database import upsert_user
        await upsert_user(interaction.user.id, interaction.user.display_name)
        session_id = await create_session(guild_id, interaction.channel_id, topic, interaction.user.id)

        # Store in-memory session
        self.bot.active_sessions[guild_id] = {
            "id": session_id,
            "topic": topic,
            "channel_id": interaction.channel_id,
            "started_at": datetime.utcnow(),
            "voice_transcript": "",
            "chat_log": [],
            "quiz_scores": {},  # {username: total_points}
            "pomodoro_task": None,
        }

        await interaction.followup.send(
            embed=embeds.session_start(topic, config.POMODORO_FOCUS_MINS, config.POMODORO_BREAK_MINS)
        )

        # Start Pomodoro loop
        task = asyncio.create_task(self._pomodoro_loop(guild_id, interaction.channel))
        self.bot.active_sessions[guild_id]["pomodoro_task"] = task

        log.info(f"Session started in guild {guild_id}: {topic}")

    @study_group.command(name="end", description="End the current study session and generate summary")
    async def study_end(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id

        if guild_id not in self.bot.active_sessions:
            return await interaction.response.send_message(
                embed=embeds.error("No active session. Use `/study start` first."),
                ephemeral=True,
            )

        try:
            await interaction.response.defer(thinking=True)
        except discord.NotFound:
            # Interaction token expired (>3 s elapsed, usually because a
            # prior synchronous operation blocked the event loop).  The
            # session teardown should still complete; responses will be
            # sent via channel.send() as a fallback.
            log.warning(f"study end: interaction expired for guild {guild_id}, continuing without defer")
        session = self.bot.active_sessions.pop(guild_id)

        # Cancel Pomodoro
        if session["pomodoro_task"]:
            session["pomodoro_task"].cancel()

        # Calculate duration
        duration = int((datetime.utcnow() - session["started_at"]).total_seconds() / 60)

        # Generate summary
        summary_text = ""
        try:
            summary_text = await generate_summary(
                topic=session["topic"],
                transcript=session["voice_transcript"],
                chat_log=session["chat_log"],
                quiz_scores=session["quiz_scores"],
            )
        except Exception as e:
            log.warning(f"Summary generation failed: {e}")
            summary_text = "Summary unavailable."

        # Persist to DB
        await end_session(session["id"], summary_text)

        # Update streaks for all quiz participants
        for username in session["quiz_scores"]:
            try:
                # Look up discord_id by username — best effort
                pass
            except Exception:
                pass
        await update_streak(interaction.user.id, guild_id)

        try:
            await interaction.followup.send(embed=embeds.session_end(session["topic"], duration))
        except (discord.NotFound, discord.HTTPException):
            await interaction.channel.send(embed=embeds.session_end(session["topic"], duration))

        if summary_text and summary_text != "Summary unavailable.":
            await interaction.channel.send(embed=embeds.session_summary(session["topic"], summary_text))

        log.info(f"Session ended in guild {guild_id}, duration {duration}min")

    @study_group.command(name="status", description="Check the current session status")
    async def study_status(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if guild_id not in self.bot.active_sessions:
            return await interaction.response.send_message(embed=embeds.info("No active session."), ephemeral=True)

        session = self.bot.active_sessions[guild_id]
        duration = int((datetime.utcnow() - session["started_at"]).total_seconds() / 60)
        await interaction.response.send_message(
            embed=embeds.info(f"📚 **{session['topic']}** — running for {duration} min")
        )

    # ── Pomodoro Loop ─────────────────────────────────────────────────────────

    async def _pomodoro_loop(self, guild_id: int, channel: discord.TextChannel):
        cycle = 0
        try:
            while guild_id in self.bot.active_sessions:
                cycle += 1
                # Focus block
                await channel.send(embed=embeds.pomodoro_focus(cycle))
                await asyncio.sleep(config.POMODORO_FOCUS_MINS * 60)

                if guild_id not in self.bot.active_sessions:
                    break

                # Break block — trigger quiz from quiz cog
                await channel.send(embed=embeds.pomodoro_break(cycle))
                quiz_cog = self.bot.cogs.get("QuizCog")
                if quiz_cog:
                    await quiz_cog.dispatch_quiz(guild_id, channel)

                await asyncio.sleep(config.POMODORO_BREAK_MINS * 60)
        except asyncio.CancelledError:
            log.info(f"Pomodoro loop cancelled for guild {guild_id}")

    # ── Chat log listener ─────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        session = self.bot.active_sessions.get(message.guild.id)
        if session and message.channel.id == session["channel_id"]:
            line = f"[{message.author.display_name}]: {message.content}"
            session["chat_log"].append(line)


async def setup(bot):
    await bot.add_cog(StudyCog(bot))
