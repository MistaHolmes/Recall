"""
cogs/rag.py — /ask command
"""

import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands
from ai.rag_pipeline import query
from ai.gemini_client import ask
from utils import embeds

log = logging.getLogger("cog.rag")

SYSTEM_PROMPT = """You are a knowledgeable study assistant.
Answer the student's question using ONLY the provided context.
Keep your answer to 3-5 sentences. Cite the source page if mentioned in context.
If the context doesn't contain the answer, say so honestly."""


class RAGCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ask", description="Ask a question about your uploaded course material")
    @app_commands.describe(question="Your question")
    async def ask_command(self, interaction: discord.Interaction, question: str):
        try:
            await interaction.response.defer(thinking=True)
        except discord.NotFound:
            log.warning(f"ask: interaction expired before defer in guild {interaction.guild_id}")

        loop = asyncio.get_event_loop()
        try:
            rag = await loop.run_in_executor(None, query, interaction.guild_id, question)
        except RuntimeError as e:
            return await interaction.followup.send(embed=embeds.error(str(e)))

        prompt = f"Context:\n{rag['context']}\n\nQuestion: {question}"
        try:
            answer = await ask(prompt, system=SYSTEM_PROMPT)
        except Exception as e:
            log.error(f"Gemini error: {e}")
            return await interaction.followup.send(embed=embeds.error("AI is temporarily unavailable. Try again in a moment."))

        # Log to session chat if active
        session = self.bot.active_sessions.get(interaction.guild_id)
        if session:
            session["chat_log"].append(f"[Q] {question}")
            session["chat_log"].append(f"[A] {answer}")

        await interaction.followup.send(embed=embeds.rag_answer(question, answer, rag["citations"]))


async def setup(bot):
    await bot.add_cog(RAGCog(bot))
