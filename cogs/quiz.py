"""
cogs/quiz.py — /quiz command, reaction listener, scoring
"""

import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands
from db.database import upsert_user, record_quiz_answer
from ai.quiz_engine import generate_quiz
from utils import embeds
from config import config

log = logging.getLogger("cog.quiz")

EMOJI_MAP = {"🇦": 0, "🇧": 1, "🇨": 2, "🇩": 3}
REACTION_EMOJIS = list(EMOJI_MAP.keys())


class QuizCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # guild_id -> {message_id, question, options, correct_index, explanation, citations, votes, session_id}
        self.active_quizzes: dict = {}

    @app_commands.command(name="quiz", description="Generate a quiz question from course material")
    async def quiz_command(self, interaction: discord.Interaction):
        session = self.bot.active_sessions.get(interaction.guild_id)
        topic = session["topic"] if session else "General Knowledge"

        await interaction.response.defer(thinking=True)
        channel = interaction.channel
        await interaction.delete_original_response()
        await self.dispatch_quiz(interaction.guild_id, channel, topic)

    async def dispatch_quiz(self, guild_id: int, channel: discord.TextChannel, topic: str | None = None):
        """Called by Pomodoro loop or /quiz command."""
        if guild_id in self.active_quizzes:
            return  # Quiz already running

        session = self.bot.active_sessions.get(guild_id)
        if not topic:
            topic = session["topic"] if session else "General Knowledge"

        try:
            quiz_data = await generate_quiz(guild_id, topic)
        except Exception as e:
            log.error(f"Quiz generation failed: {e}")
            await channel.send(embed=embeds.error("Failed to generate quiz. Try again later."))
            return

        embed = embeds.quiz_question(quiz_data["question"], quiz_data["options"], config.QUIZ_TIMEOUT_SECS)
        msg = await channel.send(embed=embed)

        for emoji in REACTION_EMOJIS:
            await msg.add_reaction(emoji)

        self.active_quizzes[guild_id] = {
            "message_id": msg.id,
            "channel_id": channel.id,
            "question": quiz_data["question"],
            "options": quiz_data["options"],
            "correct_index": quiz_data["correct_index"],
            "explanation": quiz_data.get("explanation", ""),
            "citations": quiz_data.get("citations", []),
            "votes": {},  # user_id -> emoji_index
            "session_id": session["id"] if session else None,
        }

        # Auto-close after timeout
        await asyncio.sleep(config.QUIZ_TIMEOUT_SECS)
        await self._close_quiz(guild_id)

    async def _close_quiz(self, guild_id: int):
        quiz = self.active_quizzes.pop(guild_id, None)
        if not quiz:
            return

        channel = self.bot.get_channel(quiz["channel_id"])
        if not channel:
            return

        correct_idx = quiz["correct_index"]
        correct_option = quiz["options"][correct_idx]
        awarded: dict[str, int] = {}

        for user_id, chosen_idx in quiz["votes"].items():
            member = channel.guild.get_member(user_id)
            if not member:
                continue
            correct = chosen_idx == correct_idx
            pts = 0
            if quiz["session_id"]:
                pts = await record_quiz_answer(quiz["session_id"], user_id, quiz["question"], correct)

            # Update in-session score tracker
            session = self.bot.active_sessions.get(guild_id)
            if session and pts > 0:
                session["quiz_scores"][member.display_name] = session["quiz_scores"].get(member.display_name, 0) + pts

            if pts > 0:
                awarded[member.display_name] = pts

        await channel.send(embed=embeds.quiz_result(quiz["question"], correct_option, quiz["explanation"], awarded))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        quiz = self.active_quizzes.get(payload.guild_id)
        if not quiz or payload.message_id != quiz["message_id"]:
            return

        emoji = str(payload.emoji)
        if emoji not in EMOJI_MAP:
            return

        # Only count users in the active session
        session = self.bot.active_sessions.get(payload.guild_id)
        if session:
            quiz["votes"][payload.user_id] = EMOJI_MAP[emoji]
        else:
            # Allow voting without a session too (manual /quiz)
            quiz["votes"][payload.user_id] = EMOJI_MAP[emoji]

        # Register user
        member = payload.member
        if member:
            await upsert_user(member.id, member.display_name)

    @app_commands.command(name="leaderboard", description="Show the top scorers for this server")
    async def leaderboard(self, interaction: discord.Interaction):
        from db.database import get_leaderboard
        rows = await get_leaderboard(interaction.guild_id)
        await interaction.response.send_message(
            embed=embeds.leaderboard(rows, interaction.guild.name)
        )


async def setup(bot):
    await bot.add_cog(QuizCog(bot))
