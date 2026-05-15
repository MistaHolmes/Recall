"""
Discord AI Study Bot — Entry Point
"""

import asyncio
import logging
import time
import discord
from discord import app_commands
from discord.ext import commands
from config import config
from db.database import init_db, close_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("StudyBot")


class _CryptoErrorRateLimiter(logging.Filter):
    """Suppress the flood of CryptoError records from discord-ext-voice-recv.

    Discord rotates the voice session key periodically.  During the brief
    re-key window a handful of RTP packets arrive encrypted with the old key
    and fail to decrypt — this is normal and non-fatal.  The library logs
    every such packet at ERROR level, which can produce hundreds of lines per
    second.  We allow the first 3 messages through (so operators know it
    happened), then silence subsequent messages for 30 seconds.
    """

    _WINDOW = 30        # seconds between bursts
    _MAX_PER_WINDOW = 3

    def __init__(self):
        super().__init__()
        self._count = 0
        self._window_start = 0.0

    def filter(self, record: logging.LogRecord) -> bool:  # True = emit
        if "CryptoError" not in record.getMessage():
            return True
        now = time.monotonic()
        if now - self._window_start > self._WINDOW:
            # Start a fresh window
            self._window_start = now
            self._count = 0
        self._count += 1
        if self._count <= self._MAX_PER_WINDOW:
            return True
        if self._count == self._MAX_PER_WINDOW + 1:
            # Emit one final "suppressed" notice
            record.msg = (
                "CryptoError flood suppressed — Discord key rotation in progress "
                "(further errors silenced for %ds)"
            )
            record.args = (self._WINDOW,)
            return True
        return False


# Attach the rate-limiter to the voice_recv reader logger
logging.getLogger("discord.ext.voice_recv.reader").addFilter(_CryptoErrorRateLimiter())


class StudyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = False   # Enable in Dev Portal later for chat logging
        intents.members = False           # Enable in Dev Portal later for member lookups
        intents.voice_states = True       # Non-privileged, already on by default

        super().__init__(
            command_prefix=config.BOT_PREFIX,
            intents=intents,
            application_id=int(config.DISCORD_APPLICATION_ID),
        )

        # In-memory session store: guild_id -> session dict
        self.active_sessions: dict = {}

    async def setup_hook(self):
        """Called once before the bot connects. Load all cogs and sync commands."""
        await self.setup_app_command_error_handler()

        await init_db()
        log.info("Database pool initialized")

        # Pre-load the embedding model in a thread so the first /ask or
        # /upload doesn't block the event loop for several seconds.
        from ai.embeddings import preload_model
        await asyncio.get_event_loop().run_in_executor(None, preload_model)
        log.info("Embedding model pre-loaded")

        cogs = [
            "cogs.admin",
            "cogs.study",
            "cogs.rag",
            "cogs.quiz",
            "cogs.voice",
            "cogs.schedule",   # Phase 5 — session scheduling
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info(f"Loaded cog: {cog}")
            except Exception as e:
                log.error(f"Failed to load cog {cog}: {e}")

        # Sync slash commands to the test guild instantly (no 1hr global delay)
        if config.COMMAND_SYNC_GUILDS:
            guild = discord.Object(id=int(config.COMMAND_SYNC_GUILDS))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info(f"Synced {len(synced)} commands to guild {config.COMMAND_SYNC_GUILDS}")
        else:
            synced = await self.tree.sync()
            log.info(f"Synced {len(synced)} commands globally")

    async def on_ready(self):
        log.info(f"Bot online: {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📚 /study start to begin",
            )
        )

    async def on_command_error(self, ctx, error):
        log.error(f"Command error: {error}")

    async def setup_app_command_error_handler(self):
        """Register a global handler that catches 'Unknown interaction'
        (10062) errors from expired interaction tokens.  These happen when the
        event loop was briefly blocked and Discord's 3-second response window
        was missed.  Without this handler every occurrence produces an ugly
        multi-line traceback in the log that obscures real errors."""

        @self.tree.error
        async def _on_app_command_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError,
        ):
            original = getattr(error, "original", error)

            # Discord error 10062 = "Unknown interaction" — token expired.
            if isinstance(original, discord.NotFound) and original.code == 10062:
                cmd = getattr(interaction.command, "qualified_name", "?")
                log.warning(
                    f"Interaction expired for /{cmd} in guild "
                    f"{interaction.guild_id} (Discord error 10062) — "
                    "the bot likely took >3 s to respond."
                )
                # Don't spam the channel with a "timed out" message — most
                # commands now handle defer-failure gracefully and will
                # deliver their result via channel.send() on their own.
                return

            # Discord error 40060 = "Interaction has already been
            # acknowledged" — two things tried to defer/respond to the same
            # interaction.  This is harmless (the user already saw a reply).
            if isinstance(original, discord.HTTPException) and original.code == 40060:
                cmd = getattr(interaction.command, "qualified_name", "?")
                log.debug(
                    f"Double-acknowledge on /{cmd} in guild "
                    f"{interaction.guild_id} (Discord error 40060) — ignored."
                )
                return

            # Any other app-command error — log with full traceback.
            cmd = getattr(interaction.command, "qualified_name", "?")
            log.error(f"Unhandled error in /{cmd}: {error}", exc_info=error)

    async def close(self):
        """Override close() to cancel active tasks before disconnecting."""
        log.info("Shutting down — cancelling active sessions and voice tasks…")
        for guild_id, session in list(self.active_sessions.items()):
            task = session.get("pomodoro_task")
            if task and not task.done():
                task.cancel()
        await super().close()


async def main():
    config.validate_config()
    bot = StudyBot()
    try:
        async with bot:
            await bot.start(config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        # Swallow the interrupt — cleanup already handled by bot.close()
        pass
    finally:
        await close_db()
        log.info("Bot shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # silence the top-level traceback on Ctrl+C
