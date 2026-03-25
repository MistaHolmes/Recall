"""
Discord AI Study Bot — Entry Point
"""

import asyncio
import logging
import discord
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
        await init_db()
        log.info("Database pool initialized")
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
