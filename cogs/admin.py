"""
cogs/admin.py — Admin commands: /upload, /files, /clearfiles
"""

import os
import asyncio
import discord
import logging
from discord import app_commands
from discord.ext import commands
from ai.rag_pipeline import ingest_pdf, list_files, delete_guild_collection
from utils import embeds

log = logging.getLogger("cog.admin")


async def _safe_defer(interaction: discord.Interaction) -> bool:
    """Try to defer; return True on success, False if the token already expired."""
    try:
        await interaction.response.defer(thinking=True)
        return True
    except (discord.NotFound, discord.HTTPException) as e:
        log.warning(f"defer failed for /{getattr(interaction.command, 'qualified_name', '?')} "
                    f"in guild {interaction.guild_id}: {e}")
        return False


async def _reply(interaction: discord.Interaction, embed: discord.Embed, *, deferred: bool) -> None:
    """Reply via followup when deferred, fallback to channel.send otherwise."""
    if deferred:
        try:
            await interaction.followup.send(embed=embed)
            return
        except (discord.NotFound, discord.HTTPException):
            pass
    try:
        await interaction.channel.send(embed=embed)
    except Exception:
        pass


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="upload", description="Upload a PDF to the study bot knowledge base")
    @app_commands.describe(file="The PDF file to upload")
    async def upload(self, interaction: discord.Interaction, file: discord.Attachment):
        deferred = await _safe_defer(interaction)

        if not file.filename.lower().endswith(".pdf"):
            return await _reply(interaction, embeds.error("Only PDF files are supported."), deferred=deferred)

        if file.size > 25 * 1024 * 1024:
            return await _reply(interaction, embeds.error("PDF must be under 25MB."), deferred=deferred)

        # Download file to a temp path
        tmp_path = f"/tmp/{interaction.guild_id}_{file.filename}"
        try:
            data = await file.read()
        except Exception as e:
            log.error(f"File download error: {e}")
            return await _reply(interaction, embeds.error(f"Failed to download file: {e}"), deferred=deferred)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: open(tmp_path, "wb").write(data))

        try:
            count = await loop.run_in_executor(
                None, ingest_pdf, interaction.guild_id, tmp_path, file.filename
            )
        except Exception as e:
            log.error(f"Ingestion error: {e}")
            return await _reply(interaction, embeds.error(f"Failed to process PDF: {e}"), deferred=deferred)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        await _reply(
            interaction,
            embeds.info(f"✅ Uploaded **{file.filename}** — {count} chunks indexed into the knowledge base."),
            deferred=deferred,
        )

    @app_commands.command(name="files", description="List all PDFs uploaded to this server")
    async def files(self, interaction: discord.Interaction):
        deferred = await _safe_defer(interaction)

        loop = asyncio.get_event_loop()
        file_list = await loop.run_in_executor(None, list_files, interaction.guild_id)

        if not file_list:
            return await _reply(
                interaction,
                embeds.info("No files uploaded yet. Use /upload to add course material."),
                deferred=deferred,
            )
        await _reply(
            interaction,
            embeds.info("📁 **Uploaded Files:**\n" + "\n".join(f"• {f}" for f in file_list)),
            deferred=deferred,
        )

    @app_commands.command(name="clearfiles", description="Remove all uploaded PDFs for this server (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearfiles(self, interaction: discord.Interaction):
        deferred = await _safe_defer(interaction)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, delete_guild_collection, interaction.guild_id)

        await _reply(
            interaction,
            embeds.info("🗑️ All course material for this server has been removed."),
            deferred=deferred,
        )

    @clearfiles.error
    async def permission_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original = getattr(error, "original", error)
        if isinstance(original, app_commands.MissingPermissions):
            try:
                await interaction.response.send_message(
                    embed=embeds.error("You need **Manage Server** permission for this command."),
                    ephemeral=True,
                )
            except (discord.NotFound, discord.HTTPException):
                await interaction.channel.send(
                    embed=embeds.error("You need **Manage Server** permission for this command."),
                )
            return
        # For anything else, DON'T re-raise (discord.py eats it as unhandled
        # task exception instead of routing to the global tree handler).
        # Log here and return so the error isn't silently swallowed.
        cmd = getattr(interaction.command, "qualified_name", "clearfiles")
        log.error(f"Error in /{cmd}: {error}", exc_info=error)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
