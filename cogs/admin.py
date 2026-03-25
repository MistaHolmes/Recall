"""
cogs/admin.py — Admin commands: /upload, /files, /clearfiles
"""

import os
import io
import discord
import logging
from discord import app_commands
from discord.ext import commands
from ai.rag_pipeline import ingest_pdf, list_files, delete_guild_collection
from utils import embeds

log = logging.getLogger("cog.admin")


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="upload", description="Upload a PDF to the study bot knowledge base")
    @app_commands.describe(file="The PDF file to upload")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def upload(self, interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer(thinking=True)

        if not file.filename.lower().endswith(".pdf"):
            return await interaction.followup.send(embed=embeds.error("Only PDF files are supported."))

        if file.size > 25 * 1024 * 1024:
            return await interaction.followup.send(embed=embeds.error("PDF must be under 25MB."))

        # Download file to a temp path
        tmp_path = f"/tmp/{interaction.guild_id}_{file.filename}"
        data = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(data)

        try:
            count = ingest_pdf(interaction.guild_id, tmp_path, file.filename)
        except Exception as e:
            log.error(f"Ingestion error: {e}")
            return await interaction.followup.send(embed=embeds.error(f"Failed to process PDF: {e}"))
        finally:
            os.remove(tmp_path)

        await interaction.followup.send(
            embed=embeds.info(f"✅ Uploaded **{file.filename}** — {count} chunks indexed into the knowledge base.")
        )

    @app_commands.command(name="files", description="List all PDFs uploaded to this server")
    async def files(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        files = list_files(interaction.guild_id)
        if not files:
            return await interaction.followup.send(embed=embeds.info("No files uploaded yet. Use /upload to add course material."))
        await interaction.followup.send(
            embed=embeds.info("📁 **Uploaded Files:**\n" + "\n".join(f"• {f}" for f in files))
        )

    @app_commands.command(name="clearfiles", description="Remove all uploaded PDFs for this server (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearfiles(self, interaction: discord.Interaction):
        delete_guild_collection(interaction.guild_id)
        await interaction.response.send_message(
            embed=embeds.info("🗑️ All course material for this server has been removed.")
        )

    @upload.error
    @clearfiles.error
    async def permission_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(embed=embeds.error("You need **Manage Server** permission for this command."), ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
