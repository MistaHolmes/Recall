"""
cogs/schedule.py — Phase 5: Study session scheduling with APScheduler

Commands:
  /schedule create <topic> <iso_time>  — book a future session (sends a reminder when it starts)
  /schedule list                        — list upcoming scheduled sessions for this guild
  /schedule cancel <job_id>             — cancel a pending session
"""

import logging
import discord
from datetime import datetime, timezone
from discord import app_commands
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from utils import embeds

log = logging.getLogger("cog.schedule")


# Module-level scheduler (shared across cog reloads)
_scheduler = AsyncIOScheduler(
    jobstores={"default": MemoryJobStore()},
    job_defaults={"coalesce": True, "max_instances": 1},
    timezone="UTC",
)


def _ensure_scheduler_running():
    if not _scheduler.running:
        _scheduler.start()
        log.info("APScheduler started")


# ── Reminder callback (must be a top-level function for APScheduler pickling) ──

async def _send_session_reminder(
    bot_ref,
    guild_id: int,
    channel_id: int,
    topic: str,
    scheduled_by: str,
):
    """Fired by APScheduler at the scheduled time."""
    try:
        channel = bot_ref.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="📅 Scheduled Study Session Starting!",
                description=(
                    f"**Topic:** {topic}\n"
                    f"**Scheduled by:** {scheduled_by}\n\n"
                    f"Use `/study start` to begin the session."
                ),
                color=discord.Color.green(),
            )
            embed.set_footer(text="AI Study Group Facilitator • Scheduled session")
            await channel.send(embed=embed)
            log.info(f"Sent session reminder in guild {guild_id} channel {channel_id}")
    except Exception as e:
        log.error(f"Failed to send session reminder: {e}")


class ScheduleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _ensure_scheduler_running()

    def cog_unload(self):
        # Don't stop the scheduler on cog reload — leave it running
        pass

    # ── Commands ──────────────────────────────────────────────────────────────

    schedule_group = app_commands.Group(
        name="schedule",
        description="Schedule and manage future study sessions",
    )

    @schedule_group.command(
        name="create",
        description="Schedule a study session reminder (ISO 8601 time, e.g. 2026-03-26T18:00:00)",
    )
    @app_commands.describe(
        topic="What will the session cover?",
        iso_time="When to send the reminder, in ISO 8601 UTC format (e.g. 2026-03-26T18:00:00)",
    )
    async def schedule_create(
        self,
        interaction: discord.Interaction,
        topic: str,
        iso_time: str,
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Parse the time
        try:
            run_at = datetime.fromisoformat(iso_time).replace(tzinfo=timezone.utc)
        except ValueError:
            return await interaction.followup.send(
                embed=embeds.error(
                    "Invalid time format. Use ISO 8601 UTC, e.g. `2026-03-26T18:00:00`"
                ),
                ephemeral=True,
            )

        now = datetime.now(timezone.utc)
        if run_at <= now:
            return await interaction.followup.send(
                embed=embeds.error("Scheduled time must be in the future."),
                ephemeral=True,
            )

        job_id = f"session_{interaction.guild_id}_{int(run_at.timestamp())}"

        _scheduler.add_job(
            _send_session_reminder,
            trigger="date",
            run_date=run_at,
            kwargs={
                "bot_ref":       self.bot,
                "guild_id":      interaction.guild_id,
                "channel_id":    interaction.channel_id,
                "topic":         topic,
                "scheduled_by":  interaction.user.display_name,
            },
            id=job_id,
            replace_existing=True,
        )

        delta_mins = int((run_at - now).total_seconds() / 60)
        hours, mins = divmod(delta_mins, 60)
        time_label = f"{hours}h {mins}m" if hours else f"{mins}m"

        embed = discord.Embed(
            title="✅ Session Scheduled",
            description=(
                f"**Topic:** {topic}\n"
                f"**Time (UTC):** `{run_at.strftime('%Y-%m-%d %H:%M')}`\n"
                f"**Reminder in:** {time_label}\n"
                f"**Job ID:** `{job_id}`"
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Use /schedule list to see upcoming sessions")
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Scheduled session '{topic}' in guild {interaction.guild_id} at {run_at}")

    @schedule_group.command(
        name="list",
        description="List all upcoming scheduled study sessions for this server",
    )
    async def schedule_list(self, interaction: discord.Interaction):
        jobs = [
            j for j in _scheduler.get_jobs()
            if str(interaction.guild_id) in j.id
        ]

        if not jobs:
            return await interaction.response.send_message(
                embed=embeds.info("No upcoming sessions scheduled. Use `/schedule create` to add one."),
                ephemeral=True,
            )

        lines = []
        for job in sorted(jobs, key=lambda j: j.next_run_time):
            run_str = job.next_run_time.strftime("%Y-%m-%d %H:%M UTC") if job.next_run_time else "unknown"
            topic = job.kwargs.get("topic", "Unknown topic")
            by    = job.kwargs.get("scheduled_by", "Unknown")
            lines.append(f"• **{topic}** — {run_str} (by {by})\n  ID: `{job.id}`")

        embed = discord.Embed(
            title=f"📅 Upcoming Sessions ({len(jobs)})",
            description="\n\n".join(lines),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @schedule_group.command(
        name="cancel",
        description="Cancel a scheduled session by its Job ID",
    )
    @app_commands.describe(job_id="The Job ID shown in /schedule list")
    async def schedule_cancel(self, interaction: discord.Interaction, job_id: str):
        # Only allow cancelling jobs belonging to this guild
        if str(interaction.guild_id) not in job_id:
            return await interaction.response.send_message(
                embed=embeds.error("Job not found or not in this server."),
                ephemeral=True,
            )

        try:
            _scheduler.remove_job(job_id)
            await interaction.response.send_message(
                embed=embeds.info(f"✅ Cancelled scheduled session `{job_id}`."),
                ephemeral=True,
            )
        except Exception:
            await interaction.response.send_message(
                embed=embeds.error(f"Job `{job_id}` not found."),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleCog(bot))
