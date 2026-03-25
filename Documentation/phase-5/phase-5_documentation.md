# Phase 5 — Session Scheduler & Calendar Reminders
### Technical Implementation Report

| Field | Value |
|---|---|
| **Project** | AI Study Group Facilitator — Discord Bot |
| **Phase** | 5 — APScheduler-backed `/schedule` command, ISO 8601 date-trigger reminders |
| **Date** | 2026-03-25 |
| **Runtime** | Python 3.14.2 · discord.py 2.7.1 · APScheduler 3.11.2 |
| **Status** | ✅ Operational — create, list, cancel study session reminders with future-time validation |
| **Depends On** | Phase 1 (bot, infrastructure), Phase 3 (study session patterns the reminders reference) |

---

## Table of Contents

1. [Abstract](#1-abstract)
2. [Motivation & Design Goals](#2-motivation--design-goals)
3. [Phase 5 Architecture](#3-phase-5-architecture)
4. [Component Deep-Dives](#4-component-deep-dives)
   - 4.1 [Scheduler Singleton Initialisation](#41-scheduler-singleton-initialisation)
   - 4.2 [`/schedule create`](#42-schedule-create)
   - 4.3 [`/schedule list`](#43-schedule-list)
   - 4.4 [`/schedule cancel`](#44-schedule-cancel)
   - 4.5 [Reminder Dispatch — `_send_session_reminder()`](#45-reminder-dispatch--_send_session_reminder)
5. [Job ID Scheme](#5-job-id-scheme)
6. [APScheduler and asyncio Integration](#6-apscheduler-and-asyncio-integration)
7. [Edge Cases & Failure Modes](#7-edge-cases--failure-modes)
8. [Limitations & Phase 6 Roadmap](#8-limitations--phase-6-roadmap)
9. [Test Checklist](#9-test-checklist)
10. [Appendices](#10-appendices)

---

## 1. Abstract

Phase 5 adds a **study session scheduler** to the Discord bot, allowing users to pre-schedule study group reminders via `/schedule create`. At the specified UTC time, the bot posts a branded reminder embed in the designated text channel, pinging participants. Users can inspect pending reminders with `/schedule list` and cancel them with `/schedule cancel`. The scheduler backend is APScheduler's `AsyncIOScheduler`, which integrates natively with the bot's asyncio event loop and persists no state to disk — reminders are ephemeral and reset on bot restart.

---

## 2. Motivation & Design Goals

Study groups benefit from **advance coordination** — participants need to know when and where to gather. Without tooling, this requires manual reminders (often forgotten) or external calendar applications that are disconnected from the study workspace. Integrating a lightweight scheduler directly into the Discord bot allows groups to plan, view, and cancel sessions without leaving the platform.

Design goals:

- **Zero-friction input:** ISO 8601 UTC timestamps (`2025-05-14T18:00:00`) are familiar to technical users and unambiguous across time zones.
- **Guild-scoped isolation:** each guild can only see and cancel its own scheduled jobs.
- **No data loss on success:** APScheduler automatically removes `date`-trigger jobs after they fire.
- **Graceful bot restart handling:** since `MemoryJobStore` is used, jobs survived only by the bot process — appropriate for a development/study context where the bot is typically run by hand.

---

## 3. Phase 5 Architecture

```
User calls /schedule create
       time: 2025-05-14T18:00:00
       topic: Kubernetes Networking
  │
  ▼
cogs/schedule.py  ScheduleCog.schedule_create()
  │  1. Parse ISO 8601 → datetime (UTC-aware)
  │  2. Validate: must be in the future
  │  3. Compose job_id = "session_{guild_id}_{unix_timestamp}"
  │  4. _scheduler.add_job(
  │         _send_session_reminder,          ← top-level coroutine function
  │         trigger="date",
  │         run_date=parsed_time,
  │         args=[channel_id, topic, guild_id],
  │         id=job_id,
  │         timezone=utc,
  │     )
  │  5. Confirm embed sent to user
  │
  ├─── at run_date ────────────────────────────────────────────────────
  │    APScheduler AsyncIOScheduler fires job
  │    6. asyncio.ensure_future(_send_session_reminder(channel_id, topic, guild_id))
  │    7. bot.get_channel(channel_id).send(embed=reminder_embed)
  │    8. Job automatically removed from MemoryJobStore (date trigger, one-shot)
  │
  ▼
User calls /schedule list
  │  9. _scheduler.get_jobs()  → filter by guild_id substring in job.id
  │  10. Build embed: job topic, scheduled time
  │
User calls /schedule cancel <job_id>
  │  11. Validate job_id contains guild_id (guild scope check)
  │  12. _scheduler.remove_job(job_id)
  │  13. Confirm cancellation embed
```

---

## 4. Component Deep-Dives

### 4.1 Scheduler Singleton Initialisation

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from pytz import utc

# Module-level singleton — shared across all cog instances
_scheduler = AsyncIOScheduler(
    jobstores={"default": MemoryJobStore()},
    timezone=utc,
)

class ScheduleCog(commands.Cog, name="ScheduleCog"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ensure_scheduler_running()

    @staticmethod
    def _ensure_scheduler_running():
        if not _scheduler.running:
            _scheduler.start()
            log.info("APScheduler AsyncIOScheduler started.")
```

**Why a module-level singleton?** Discord.py cogs can be unloaded and reloaded without restarting the bot (e.g., for hot-reloading during development). If the scheduler were created inside `__init__`, it would be re-created on every cog reload, losing all queued jobs and potentially spawning multiple scheduler instances on the same event loop. The module-level singleton is created once per Python module import and survives cog reloads.

`_ensure_scheduler_running()` guards against calling `start()` twice (which raises `SchedulerAlreadyRunningError`) — safe whether called on first load or cog reload.

---

### 4.2 `/schedule create`

```python
@schedule_group.command(name="create", description="Schedule a study session reminder")
async def schedule_create(self, interaction: discord.Interaction,
                           time: str, topic: str):
    await interaction.response.defer(thinking=True)

    # Parse ISO 8601 string → UTC-aware datetime
    try:
        run_date = datetime.fromisoformat(time).replace(tzinfo=utc)
    except ValueError:
        return await interaction.followup.send(
            embed=embeds.error("Invalid time format. Use ISO 8601: `2025-05-14T18:00:00`")
        )

    # Reject past timestamps
    if run_date <= datetime.now(tz=utc):
        return await interaction.followup.send(
            embed=embeds.error("Scheduled time must be in the future.")
        )

    # Deterministic, guild-scoped job ID
    unix_ts = int(run_date.timestamp())
    job_id = f"session_{interaction.guild_id}_{unix_ts}"

    _scheduler.add_job(
        _send_session_reminder,
        trigger="date",
        run_date=run_date,
        args=[interaction.channel_id, topic, interaction.guild_id],
        id=job_id,
        replace_existing=True,   # idempotent: re-scheduling same second overwrites
        timezone=utc,
    )

    await interaction.followup.send(
        embed=embeds.info(
            f"📅 Session **{topic}** scheduled for "
            f"`{run_date.strftime('%Y-%m-%d %H:%M UTC')}`\n"
            f"Job ID: `{job_id}`"
        )
    )
```

**`replace_existing=True`:** If two `/schedule create` calls specify the same second (same `unix_ts` and same guild), the second call replaces the first without raising a `ConflictingIdError`. This is a pragmatic guard against accidental duplicate schedules.

---

### 4.3 `/schedule list`

```python
@schedule_group.command(name="list", description="List scheduled study sessions for this server")
async def schedule_list(self, interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    jobs = [j for j in _scheduler.get_jobs() if guild_id in j.id]

    if not jobs:
        return await interaction.response.send_message(
            embed=embeds.info("No sessions scheduled for this server.")
        )

    lines = []
    for job in jobs:
        # args = [channel_id, topic, guild_id]
        topic = job.args[1] if job.args else "Unknown"
        fire_time = job.next_run_time.strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"**{topic}** — {fire_time}\n`{job.id}`")

    await interaction.response.send_message(
        embed=embeds.info("📋 **Scheduled Sessions**\n\n" + "\n\n".join(lines))
    )
```

The guild-scope filter (`if guild_id in j.id`) relies on the job ID scheme `session_{guild_id}_{ts}`. Although a simple string containment check, it is unambiguous as long as the guild ID is not a substring of another guild's ID — a safe assumption since Discord IDs are 64-bit Snowflakes, which are unique and do not share substrings in practice.

---

### 4.4 `/schedule cancel`

```python
@schedule_group.command(name="cancel", description="Cancel a scheduled session")
async def schedule_cancel(self, interaction: discord.Interaction, job_id: str):
    guild_id = str(interaction.guild_id)

    # Security: ensure job belongs to this guild
    if guild_id not in job_id:
        return await interaction.response.send_message(
            embed=embeds.error("You can only cancel sessions scheduled in this server."),
            ephemeral=True,
        )

    try:
        _scheduler.remove_job(job_id)
        await interaction.response.send_message(
            embed=embeds.info(f"✅ Session `{job_id}` cancelled.")
        )
    except JobLookupError:
        await interaction.response.send_message(
            embed=embeds.error(f"No scheduled session found with ID `{job_id}`."),
            ephemeral=True,
        )
```

`JobLookupError` is APScheduler's exception for `remove_job()` called with a job ID that does not exist. This handles two cases: the job was already cancelled, or the job fired between when the user ran `/schedule list` and when they ran `/schedule cancel`.

---

### 4.5 Reminder Dispatch — `_send_session_reminder()`

```python
async def _send_session_reminder(channel_id: int, topic: str, guild_id: int):
    """Top-level coroutine — must be importable at module level for APScheduler."""
    # Bot instance injected via module-level reference set in setup()
    from bot import _bot_instance   # avoids circular import at module level
    bot = _bot_instance

    channel = bot.get_channel(channel_id)
    if not channel:
        log.warning(f"Reminder: channel {channel_id} not found (guild {guild_id})")
        return

    await channel.send(embed=discord.Embed(
        title="📚 Study Session Reminder",
        description=f"**{topic}** is starting now!\nUse `/study start topic:{topic}` to begin.",
        colour=discord.Colour.green(),
    ))
```

**Why a top-level function?** APScheduler requires the callable to be importable by Python's module system for serialisation purposes (even with `MemoryJobStore`, APScheduler validates callables at registration time). A method (`self._send_session_reminder`) would be bound to the `ScheduleCog` instance, which may not be predictably importable. A module-level `async def` is the safest pattern for APScheduler coroutine jobs.

**Bot instance access:** Rather than storing `self.bot` in the module scope during cog init (which would fail on the first import before the cog is loaded), we use a thin `_bot_instance` reference set in `bot.py`'s `setup_hook()`:

```python
# bot.py
import cogs.schedule as _sched_mod
_sched_mod._bot_instance = self   # inject after bot is ready
```

---

## 5. Job ID Scheme

```
session_{guild_id}_{unix_timestamp}

Example:
  session_1486308304354410629_1747238400
  │         │                   │
  │         │                   └─ Unix timestamp of scheduled run_date
  │         └─ Discord guild Snowflake ID (18–19 digits)
  └─ Fixed prefix for namespace clarity
```

Properties:
- **Guild-scoped:** contains the full guild ID, enabling O(n) filter on `get_jobs()`.
- **Deterministic:** same guild, same second → same ID → idempotent overwrite.
- **Human-readable:** users can decode the epoch timestamp to verify the scheduled time.
- **Unique across guilds:** since Discord Snowflakes are globally unique, no two guilds share an ID.

---

## 6. APScheduler and asyncio Integration

`AsyncIOScheduler` is APScheduler's native asyncio-compatible scheduler. It schedules jobs as asyncio coroutines dispatched via `asyncio.ensure_future()` on the running event loop, as opposed to `BackgroundScheduler` (which uses threads) or `BlockingScheduler` (which blocks the process).

The key interaction with the discord.py event loop:

```
asyncio event loop (discord.py)
  │
  ├── discord gateway heartbeat (every 40s)
  ├── command dispatch
  ├── voice recording callbacks
  ├── pomodoro timer tasks
  └── APScheduler timer (integrated — fires coroutines directly on this loop)
```

Since everything runs on a single event loop, the reminder coroutine `_send_session_reminder()` can safely call `channel.send()` without any thread-safety concerns or `asyncio.run_coroutine_threadsafe()` plumbing.

---

## 7. Edge Cases & Failure Modes

### 7.1 Past Timestamp Submitted

`/schedule create` validates `run_date <= datetime.now(tz=utc)` and returns an error embed immediately. APScheduler itself would also reject a past `date` trigger (it would fire immediately), but the pre-validation provides a clearer user error message.

### 7.2 Bot Restarts Before Reminder Fires

`MemoryJobStore` does not persist to disk. All scheduled jobs are lost on bot restart. The user will need to re-run `/schedule create`. For production-grade persistence, `SQLAlchemyJobStore` pointing to the Neon PostgreSQL database is the recommended Phase 6 upgrade.

### 7.3 Channel Deleted After Scheduling

If the reminder's target channel is deleted before the job fires, `bot.get_channel(channel_id)` returns `None`. The `_send_session_reminder()` function logs a warning and returns without raising an exception, so no traceback appears in the bot logs.

### 7.4 Guild Leaves Server / Bot Removed

If the bot is removed from the guild, `_scheduler.get_jobs()` will still contain the guild's jobs (since `MemoryJobStore` has no knowledge of Discord guild membership). When the reminder fires, `bot.get_channel()` returns `None` and the reminder is silently dropped. No cleanup is needed beyond the normal bot restart.

### 7.5 `/schedule cancel` with Stale Job ID

If the job has already fired (date trigger auto-removes after execution) and the user attempts to cancel it with a cached job ID, `_scheduler.remove_job()` raises `JobLookupError`, which is caught and presented as a user-friendly error embed.

### 7.6 Two Users Schedule at the Same Second

`job_id = f"session_{guild_id}_{unix_ts}"` is the same for two `/schedule create` calls within the same second from the same guild. With `replace_existing=True`, the second call silently overwrites the first. This is an edge case in practice but could cause confusion in high-volume guilds. Phase 6 can append a nonce (e.g., `uuid4()[:8]`) to ensure uniqueness.

### 7.7 Scheduler Not Running at Cog Load

`_ensure_scheduler_running()` calls `_scheduler.start()` only if `not _scheduler.running`. If the cog is reloaded (e.g., via `$reload schedule`), the scheduler was already started on first load and `_ensure_scheduler_running()` is a no-op — the existing jobs and running state are preserved.

---

## 8. Limitations & Phase 6 Roadmap

| Limitation | Phase 6 Mitigaton |
|---|---|
| Jobs lost on restart (`MemoryJobStore`) | Switch to `SQLAlchemyJobStore` backed by Neon PostgreSQL |
| No time-zone selection | Accept IANA tz parameter (e.g., `tz:America/New_York`); convert to UTC at creation time |
| Channel must be a text channel | Add guild channel type validation before scheduling |
| No repeat/recurrence | Add `cron` or `interval` trigger options for weekly study groups |
| No @mention in reminder | Allow user to specify @role or @user IDs to ping in the reminder embed |
| Single server — no bot restart recovery | On `setup_hook()`, load pending jobs from PostgreSQL |

---

## 9. Test Checklist

- [ ] `/schedule create time:2025-05-01T12:00:00 topic:K8s Networking` — confirm confirmation embed with job ID.
- [ ] `/schedule list` — confirm the new job appears with correct time and topic.
- [ ] Wait for scheduled time (use a near-future timestamp for testing) — confirm reminder embed posted in channel.
- [ ] `/schedule list` after reminder fires — confirm job no longer appears.
- [ ] `/schedule cancel <job_id>` — confirm job removed; subsequent `/schedule list` shows no entry.
- [ ] `/schedule cancel <job_id>` with a non-existent ID — confirm error embed.
- [ ] Submit a past time — confirm rejection embed.
- [ ] Submit an invalid ISO string — confirm format error embed.
- [ ] Attempt to cancel a job from guild B while in guild A — confirm permission denial.
- [ ] `/schedule create` twice with same-second time from same guild — confirm second call replaces first (only one reminder fires).

---

## 10. Appendices

### A — APScheduler Job Object Attributes Used

```python
job.id            # str  — "session_{guild_id}_{ts}"
job.args          # list — [channel_id, topic, guild_id]
job.next_run_time # datetime (UTC-aware) — when the job will next fire
```

### B — ISO 8601 Input Examples

| Input | Interpretation |
|---|---|
| `2025-05-14T18:00:00` | Treated as UTC (`.replace(tzinfo=utc)`) |
| `2025-05-14T18:00:00+05:30` | Converted to UTC on parse |
| `2025-05-14` | Raises `ValueError` (no time component) |
| `tomorrow at 6pm` | Raises `ValueError` — natural language not supported |

### C — Key Dependencies

```text
APScheduler==3.11.2
pytz>=2024.1        # UTC timezone object required by APScheduler
```

Install:
```bash
pip install apscheduler pytz
```

### D — References

- APScheduler documentation: https://apscheduler.readthedocs.io/en/stable/
- APScheduler asyncio integration: https://apscheduler.readthedocs.io/en/stable/userguide.html#running-apscheduler-with-asyncio
- ISO 8601 standard: https://www.iso.org/iso-8601-date-and-time-format.html
