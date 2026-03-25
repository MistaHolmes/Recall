# Implementation Plan — AI Study Group Facilitator Bot

> **Purpose:** This document is the engineering gameplan for Project 20. It defines,
> day by day, exactly what gets built, in what order, and why — covering every
> architectural decision, data contract, integration point, and failure mode.
> Claude Code will execute this plan directly. No ambiguity should remain after reading it.

---

## Table of Contents

1. [Repository Structure](#1-repository-structure)
2. [Environment & Configuration](#2-environment--configuration)
3. [Day 1 — Architecture & Schema Design](#3-day-1--architecture--schema-design)
4. [Day 2 — Bot Foundation & RAG Pipeline](#4-day-2--bot-foundation--rag-pipeline)
5. [Day 3 — Quiz Engine & Active Facilitation](#5-day-3--quiz-engine--active-facilitation)
6. [Day 4 — Voice Transcription & Session Summaries](#6-day-4--voice-transcription--session-summaries)
7. [Day 5 — Scheduling, Gamification & Polish](#7-day-5--scheduling-gamification--polish)
8. [Day 6 — Demo Preparation & Defence](#8-day-6--demo-preparation--defence)
9. [Cross-Cutting Concerns](#9-cross-cutting-concerns)
10. [Testing Strategy](#10-testing-strategy)
11. [Deployment](#11-deployment)

---

## 1. Repository Structure

The repository is organised by responsibility boundary, not by file type. Each top-level directory maps to a single team member's workstream.

```
study-bot/
│
├── bot.py                   # Entry point: instantiates StudyBot, loads all cogs
├── config.py                # Centralised settings loaded from .env
│
├── cogs/                    # Discord command handlers (Member A)
│   ├── study.py             # /study start, /study end, Pomodoro loop
│   ├── quiz.py              # /quiz command, reaction listener, answer reveal
│   ├── rag.py               # /ask command
│   ├── voice.py             # Voice channel join, PCM capture, reconnection
│   └── schedule.py          # /schedule command, reminder dispatch
│
├── rag/                     # AI pipeline (Member B)
│   ├── pipeline.py          # PDF ingestion + ChromaDB query
│   ├── quiz_engine.py       # GPT-4o MCQ generation from RAG context
│   ├── summariser.py        # GPT-4o session summary generation
│   └── embeddings.py        # Embedding client wrapper (text-embedding-3-small)
│
├── db/                      # Data layer (Member C)
│   ├── database.py          # asyncpg pool, get_db() context manager
│   ├── schema.sql           # Canonical PostgreSQL DDL
│   ├── models.py            # Python dataclasses mirroring DB tables
│   └── migrations/          # Numbered migration files
│
├── scheduler/               # APScheduler setup (Member C)
│   └── jobs.py              # Session reminder jobs, Pomodoro task factory
│
├── utils/
│   ├── embeds.py            # All Discord Embed builders
│   ├── audio.py             # PCM buffer management, Whisper wrapper
│   └── logger.py            # Structured logging configuration
│
├── tests/
│   ├── test_rag.py
│   ├── test_quiz.py
│   └── test_db.py
│
├── docker-compose.yml        # PostgreSQL + Redis + Bot services
├── Dockerfile
├── requirements.txt
├── .env.example
├── README.md
└── Implementation-Plan.md    # This file
```

**Why this structure?** Cogs, RAG, and DB are developed by different people simultaneously. Keeping them in separate top-level directories means each person owns their directory completely. Merge conflicts will be rare and isolated to `bot.py` (which only loads cogs by name) and `utils/embeds.py` (shared embed formatting).

---

## 2. Environment & Configuration

All secrets and environment-specific values live in `.env`. The bot reads nothing from hardcoded strings. `config.py` is the single source of truth for all configuration — no cog ever reads `os.getenv()` directly.

**Required environment variables:**

| Variable | Description |
|---|---|
| `DISCORD_BOT_TOKEN` | Bot token from Discord Developer Portal |
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o + embeddings) |
| `DATABASE_URL` | PostgreSQL connection string (asyncpg DSN) |
| `REDIS_URL` | Redis connection string for Celery broker |
| `CHROMA_PERSIST_DIR` | Filesystem path where ChromaDB persists data |
| `WHISPER_MODEL` | `"base"` for dev, `"medium"` for production |
| `POMODORO_FOCUS_MINS` | Default `25`, overrideable for demo purposes |
| `POMODORO_BREAK_MINS` | Default `5`, overrideable for demo purposes |
| `QUIZ_TIMEOUT_SECS` | Default `60`, time before quiz auto-locks |
| `ENVIRONMENT` | `"development"` or `"production"` |

The `config.py` module loads these at import time and raises a clear `EnvironmentError` (not a cryptic `None` crash) if any required variable is missing.

---

## 3. Day 1 — Architecture & Schema Design

**Goal:** No code runs today. The deliverable is complete design documentation that enables parallel implementation from Day 2 onward with no blocking decisions.

### 3.1 Database Schema Design

The schema is written as canonical SQL in `db/schema.sql` before a single line of application code is written. This is the single source of truth. All ORM-style queries in `db/database.py` must match it exactly.

**`users` table**

Stores every Discord user who has interacted with the bot. The `discord_id` (a 64-bit integer assigned by Discord) is the natural key for lookups, but we use a UUID as the primary key for all internal foreign-key relationships. This decouples the internal data model from the Discord API — if Discord ever changes their ID format, only one column needs updating.

**`sessions` table**

One row per study session. `guild_id` scopes the session to a specific Discord server. `topic` is a free-text string set at `/study start`. `started_at` and `ended_at` are timezone-aware timestamps. `summary` is the GPT-4o generated text stored after `/study end`. Crucially, `ended_at` being NULL indicates an active session — this is how the bot checks for conflicts without an in-memory lookup.

**`quiz_scores` table**

One row per quiz attempt per user per session. Storing individual attempts (rather than aggregated totals) is important: it enables per-session analysis, accuracy tracking, and the ability to re-compute the leaderboard with different scoring rules without data loss.

**`streaks` table**

One row per user per guild. `last_active` is a `DATE` (not `TIMESTAMPTZ`) — streak logic only cares about calendar day participation, not exact time. The streak update logic runs at session end: if `last_active = today - 1 day`, increment `current_streak`; if `last_active = today`, do nothing (already counted); otherwise reset to 1.

**`leaderboard` view**

A PostgreSQL view that joins `quiz_scores` and `sessions` to compute total points, quiz count, and accuracy percentage per user per guild. At MVP scale (< 1000 users per guild), computing on read is preferable to maintaining a denormalised table with triggers. If performance becomes an issue, this is straightforward to materialise.

### 3.2 ChromaDB Collection Design

**One collection per Discord guild.** The collection name is `guild_{guild_id}`. This means a `/ask` query from Guild A can never accidentally retrieve material ingested by Guild B. It also means an admin can delete a guild's entire knowledge base by dropping one collection.

**Chunk strategy.** PDFs are split using `RecursiveCharacterTextSplitter` with a chunk size of 512 tokens and an overlap of 64 tokens. The overlap prevents a concept that spans a page boundary from being split across two context-less chunks. The custom separators `Section \d+` and `Article \d+` are prepended to the splitter's default separator list — this ensures the splitter tries to break at section boundaries before falling back to paragraphs, then sentences, then words.

**Metadata per chunk.** Every stored chunk carries: `filename` (original PDF name), `page` (source page number for citation), `guild_id` (redundant with collection name, but useful for debugging), and `upload_timestamp`. The `page` field is what enables the bot to say "see page 47 of OS_textbook.pdf" in its answer.

**Retrieval strategy.** The query is embedded using `text-embedding-3-small`. The top-5 chunks by cosine similarity are retrieved. Before passing to GPT-4o, chunks are annotated with their source metadata so GPT-4o can include citations in its answer. At MVP, BM25 re-ranking is optional but listed as a recommended Day 3 enhancement.

### 3.3 Asynchronous Architecture Design

This is the most critical design decision in the entire project. **The Discord bot event loop must never be blocked.** A blocked event loop means the bot stops responding to commands while it waits for an OpenAI API call, a database write, or a Whisper transcription job.

The solution is a two-layer async architecture:

**Layer 1 — Discord.py event loop.** All cogs run inside this loop. Every operation in a cog that calls an external service must use `await`. This means the OpenAI client, the asyncpg database pool, and the ChromaDB client must all have async interfaces (or be run in a thread executor for blocking libraries).

**Layer 2 — Celery task queue.** Long-running background jobs (Whisper transcription of a 10-minute audio buffer, batch embedding of a large PDF) are dispatched to Celery workers. The bot dispatches the task and immediately continues. The Celery worker runs the job in a separate process. Results are stored in PostgreSQL or Redis for the bot to retrieve.

The boundary rule: if a task takes more than ~2 seconds and runs in the background without the user waiting, it goes to Celery. If a user is waiting for a response (e.g., `/ask`), it uses `await` in the event loop with a Discord `defer()` to buy time.

---

## 4. Day 2 — Bot Foundation & RAG Pipeline

**Goal:** A running bot that stays online, responds to `/ask`, and can prove RAG retrieval works against an ingested PDF. All three team members deliver working code.

### 4.1 Bot Entry Point (`bot.py`)

`StudyBot` subclasses `discord.ext.commands.Bot`. The `setup_hook()` coroutine (called once before the gateway connects) loads all four cogs and syncs slash commands globally. For development, guild-scoped sync is used instead (it propagates in seconds rather than up to an hour).

The bot maintains one piece of shared mutable state: `active_sessions`, a Python dict mapping `guild_id → session_dict`. This is the in-memory session store. It is the fastest possible lookup for "is there an active session in this guild?" — a check that happens on every incoming event. The dict is populated at `/study start` and cleared at `/study end`.

### 4.2 Discord Permissions

The OAuth2 invite link must be generated with the following scopes and permissions. Missing any of these will cause silent failures that are time-consuming to debug.

**OAuth2 Scopes:** `bot`, `applications.commands`

**Bot Permissions:** Send Messages, Embed Links, Read Message History, Add Reactions, Connect (voice), Speak (voice), Mute Members, Use Slash Commands

**Privileged Gateway Intents** (enabled in the Developer Portal): `MESSAGE_CONTENT`, `GUILD_MEMBERS`, `GUILD_VOICE_STATES`

### 4.3 RAG Ingestion Pipeline (`rag/pipeline.py`)

Ingestion is a four-step sequential pipeline:

**Step 1 — PDF text extraction.** `pypdf.PdfReader` extracts text page by page. Each page's text is stored alongside its page number. Pages with no extractable text (scanned images) are logged and skipped. In a future iteration, Tesseract OCR would handle these.

**Step 2 — Chunking.** LangChain's `RecursiveCharacterTextSplitter` splits each page's text. The chunk size is 512 tokens (approximately 380-400 words), chosen to fit comfortably within GPT-4o's context window even when 5 chunks are concatenated. The 64-token overlap ensures concepts at chunk boundaries are captured by at least one chunk in full.

**Step 3 — Embedding.** All chunks are sent to OpenAI's `text-embedding-3-small` in a single batch API call. This model produces 1536-dimensional vectors and is significantly cheaper than `text-embedding-ada-002` while matching its quality. The entire embedding call is awaited asynchronously.

**Step 4 — Storage.** Chunk texts, embeddings, and metadata are upserted into ChromaDB using `collection.upsert()`. Upsert (not insert) is critical — it means re-ingesting the same PDF after an edit is safe and idempotent. The chunk ID is derived deterministically from `{filename}_p{page}_{chunk_index}`.

### 4.4 RAG Query Pipeline (`rag/pipeline.py`)

The query flow is:

1. Embed the question using `text-embedding-3-small`.
2. Query the guild's ChromaDB collection with the embedding, retrieving the top-5 chunks (documents, metadata, distances).
3. If the collection does not exist (no PDFs ingested), raise a `RuntimeError` with a clear user-facing message.
4. Format the retrieved chunks into a numbered context string, annotating each chunk with its source and cosine similarity score.
5. Send the context + question to GPT-4o with a tightly controlled system prompt. The prompt instructs GPT-4o to answer only from the provided context, keep the answer to 3-5 sentences, and cite the source page.
6. Return a dict containing the answer string and a deduplicated list of source citations.

**Key failure modes to handle:**
- ChromaDB collection not found → return a clear "no materials uploaded" message, do not raise an unhandled exception.
- OpenAI API rate limit → Celery retry with exponential backoff (5s, 25s, 125s).
- Empty retrieval results (very low similarity) → GPT-4o is instructed to say "I couldn't find relevant material" rather than hallucinating.

### 4.5 Day 2 Demo Proof

The Day 2 KPI requires a live demo where `/ask What is a Mutex?` returns the correct definition from an ingested Operating Systems textbook. To reliably pass this:

- Ingest the textbook before the demo and verify the ChromaDB collection is non-empty.
- Run a test query from the Python shell to confirm retrieval works before the Discord bot is even involved.
- The bot's `/ask` response embed must show the source citation (filename + page number), proving the answer came from the ingested material and not GPT-4o's training data.

---

## 5. Day 3 — Quiz Engine & Active Facilitation

**Goal:** The core active learning feature is fully functional. The bot generates a quiz, collects reactions from multiple simultaneous users, grades them, and updates the leaderboard.

### 5.1 Quiz State Machine

The quiz has two states: `OPEN` and `LOCKED`. The transition from OPEN to LOCKED is triggered by either a 60-second asyncio timer or a manual admin command. The following invariants must hold at all times:

- Only one quiz can be OPEN per guild at any time.
- Reactions are accepted only while the quiz is OPEN.
- Reactions from users who are not registered participants of the active session are silently discarded.
- A user's vote is overwritable — if a user reacts with 🇦 and then 🇧, their vote is 🇧. This is natural Discord behaviour (you can change your reaction), and the bot must honour it.
- When the quiz transitions to LOCKED, all vote processing stops immediately, even if reaction events arrive out of order from the Discord gateway.

The quiz state is stored in a dict in `QuizCog`: `_active_quizzes: dict[int, ActiveQuiz]`. The `ActiveQuiz` dataclass holds the question, options, correct index, the Discord message reference (needed to edit it when revealed), the votes dict, and the locked flag.

### 5.2 GPT-4o Quiz Generation

The `quiz_engine.py` module sends a system prompt that enforces strict JSON output via GPT-4o's `response_format: {"type": "json_object"}` parameter. This eliminates the need to parse markdown code fences from the response. The schema is:

```json
{
  "question": "string",
  "options": ["string", "string", "string", "string"],
  "correct_index": 0,
  "explanation": "string"
}
```

The system prompt enforces that all four options must be plausible distractors (no obviously wrong answers), the correct index must be 0-3, and the question must be answerable from the provided context. After parsing, the bot validates the schema — if any field is missing or malformed, it raises a `RuntimeError` and the quiz command returns an error message rather than posting a broken embed.

**Why JSON mode?** Without it, GPT-4o frequently wraps JSON in markdown code fences (` ```json `). Parsing those with string manipulation is fragile and fails silently on edge cases. JSON mode guarantees a parseable response every time.

### 5.3 Reaction Handling

Discord sends reaction events via `on_raw_reaction_add`. "Raw" events (as opposed to `on_reaction_add`) fire even when the message is not in the bot's internal cache — critical for quizzes that were posted before the bot restarted.

The handler checks, in order:
1. Is the reactor the bot itself? If yes, ignore (the bot adds the initial reaction options).
2. Is there an active quiz in this guild? If no, ignore.
3. Is the reaction on the quiz message? If no, ignore.
4. Is the reactor a registered participant of the active session? If no, ignore silently.
5. Is the emoji one of 🇦🇧🇨🇩? If no, ignore.
6. Record the vote: `quiz.votes[user_id] = emoji_index`. This overwrites any previous vote.

### 5.4 Leaderboard Update Logic

When a quiz locks, scores are written to `quiz_scores` in PostgreSQL. The update uses `INSERT ... ON CONFLICT DO NOTHING` to prevent double-counting if a race condition causes the lock to trigger twice. After the database write, the in-memory `session["quiz_scores"]` dict is updated for use in the end-of-session summary (so the summary can reference quiz performance without an extra DB query).

---

## 6. Day 4 — Voice Transcription & Session Summaries

**Goal:** A full end-to-end pipeline where a 10-minute voice session produces a clean, structured summary when `/study end` is called.

### 6.1 Voice Channel Capture (`cogs/voice.py`)

Discord.py provides `discord.VoiceClient` for joining voice channels. The bot joins when `/study start` is called (if the invoking user is in a voice channel). It captures audio using a custom `discord.AudioSink`.

**PCM audio format.** Discord sends audio in 48kHz, 16-bit stereo PCM. Each 20ms audio frame is 3840 bytes. The bot collects these frames into a rolling buffer. Every 30 seconds, the buffer is flushed: its contents are saved to a temporary WAV file on disk, the Whisper transcription job is dispatched (synchronously in dev, via Celery in production), and the buffer is cleared.

**Speaker diarisation (simplified).** Discord identifies each audio packet's SSRC (synchronous source) — a per-user stream identifier. By mapping SSRC to Discord user ID, the bot can tag each transcription segment with the speaker's username. In practice, Discord's gateway sometimes delivers overlapping SSRC packets from multiple speakers; the bot handles this by interleaving transcription segments by timestamp rather than grouping by speaker.

**Reconnection.** Discord voice connections drop regularly, especially in sessions longer than 30 minutes. The `VoiceCog` wraps the capture loop in a retry loop with exponential backoff. If the connection drops, the bot attempts to reconnect up to 5 times before posting a channel notification. Critically, the audio buffer from before the disconnect is preserved in memory — no transcription is lost.

**Privacy compliance.** At `/study start`, the bot posts a prominent message: "🔴 This bot is now recording voice audio in this channel for transcription purposes. Audio is discarded immediately after transcription." Audio buffers are explicitly `del`'d from memory after each Whisper call. No raw audio is persisted to disk beyond the current 30-second buffer.

### 6.2 Whisper Transcription (`utils/audio.py`)

Two modes are supported:

**Cloud mode (OpenAI Whisper API).** The 30-second WAV buffer is sent to `openai.audio.transcriptions.create()` with `model="whisper-1"` and `response_format="verbose_json"` (which includes word-level timestamps). This is simpler to implement but costs money per call and introduces network latency.

**Local mode (faster-whisper).** The `faster-whisper` library runs the Whisper model locally using CTranslate2 for efficient CPU/GPU inference. The `"medium"` model is recommended for production — it balances accuracy and speed. In local mode, transcription of a 30-second buffer takes approximately 5-8 seconds on a modern CPU. This is dispatched to a Celery worker to avoid blocking the event loop.

**Which to use when.** Development uses cloud mode (simpler, no local GPU required). The demo uses local mode with the `"base"` model on the demo machine to avoid API costs and network dependency. Production would use local mode with `"medium"`.

### 6.3 Session Summary Generation (`rag/summariser.py`)

At `/study end`, three data sources are assembled:

1. **Voice transcript.** The accumulated Whisper output, with speaker labels and timestamps if available.
2. **Text chat log.** The last 60 messages from the session channel, collected by the `study.py` cog's `on_message` listener (filtered to the active session channel and within the session's time window).
3. **Quiz scores.** The `session["quiz_scores"]` dict — user IDs to cumulative points.

These are formatted into a structured user message and sent to GPT-4o with a system prompt that enforces a four-section Markdown output: **Key Takeaways**, **Questions Raised**, **Action Items**, and **Quiz Performance**. The system prompt specifies a 400-word maximum and instructs GPT-4o to be specific, not generic — referencing actual topics discussed rather than boilerplate study advice.

The generated summary is stored in `sessions.summary` (PostgreSQL) and posted to Discord as a formatted Embed. The embed uses a dark blue colour to distinguish it visually from session-control embeds (teal/red/green).

### 6.4 End-to-End Data Flow Verification

The Day 4 KPI requires proving data flows "seamlessly from live voice/text → Whisper/DB → GPT-4o → Final Discord Embed Summary." The following manual test must pass before the Day 4 submission:

1. Start a session with `/study start "Mutex and Semaphores"`.
2. Speak in the voice channel for at least 2 minutes about the topic.
3. Send 5 text messages in the channel asking and answering questions.
4. Trigger one quiz and answer it.
5. Type `/study end`.
6. The posted summary embed must reference concepts from the voice discussion, reference questions from the text chat, and include the quiz score.

If the summary is generic (no reference to the actual session content), the system prompt needs tightening or the context assembly logic is not passing data correctly.

---

## 7. Day 5 — Scheduling, Gamification & Polish

**Goal:** A visually polished, fully gamified bot ready for live demonstration. All slash commands function together as an integrated system.

### 7.1 Scheduling (`cogs/schedule.py` + `scheduler/jobs.py`)

The `/schedule` command takes a topic, a datetime string, and a timezone identifier (e.g., `"Asia/Kolkata"`). The bot converts the local time to UTC and creates two APScheduler jobs: one for a 24-hour reminder and one for a 1-hour reminder. A third job triggers the session automatically at the scheduled time (equivalent to calling `/study start`).

APScheduler is configured to use the **PostgreSQL job store**. This is non-negotiable: if the job store were in-memory, scheduled sessions would be lost every time the bot restarts. With the PostgreSQL job store, scheduled jobs survive bot restarts, crashes, and Docker container restarts.

Reminder notifications are sent as Discord DMs to the session organiser and as channel pings (if a designated "announcements" channel is configured for the guild).

### 7.2 Pomodoro Mute/Unmute (Day 5 Extension)

The Pomodoro loop in `cogs/study.py` already fires at the correct intervals — the Day 5 task is to add the actual voice channel mute/unmute calls.

Voice channel muting is done via `guild.change_voice_state()` or by setting the channel's `overwrites` to deny `Connect` and `Speak` for the `@everyone` role during focus time and restoring them during break time. The `overwrites` approach is preferred — it prevents new users from joining during focus time, which matches the intended UX.

**Important:** The bot must have `Manage Channels` permission for this to work. This is added to the OAuth2 invite link.

### 7.3 Leaderboard Polish

The leaderboard Embed uses three distinct visual sections:

- **Gold** (top 1): `🥇` medal prefix, embed colour `discord.Color.gold()`
- **Silver** (top 2-3): `🥈` medal prefix
- **Bronze** (top 4-5): `🥉` medal prefix
- **Below top 5**: Plain numbered list

Each entry shows: rank, username, total points, accuracy percentage, and current streak length. The streak is rendered as a flame emoji count (🔥🔥🔥 for a 3-day streak) up to a maximum of 10 flames. This visual representation is more immediately engaging than a raw number.

### 7.4 Embed Colour System

Consistent colour coding makes the bot's messages instantly recognisable at a glance. This is specified as a hard requirement for the Day 5 UI polish KPI.

| Context | Colour | Hex | Usage |
|---|---|---|---|
| Session start | Teal | `#1ABC9C` | `/study start` confirmation |
| Focus time | Red | `#E74C3C` | Pomodoro focus block announcement |
| Break time | Green | `#2ECC71` | Pomodoro break block announcement |
| Quiz open | Purple | `#9B59B6` | Active quiz embed |
| Quiz results | Gold | `#F1C40F` | Answer reveal + winner announcement |
| RAG answer | Blue | `#3498DB` | `/ask` response embeds |
| Session summary | Dark Blue | `#2C3E50` | End-of-session summary |
| Leaderboard | Gold | `#F1C40F` | `/leaderboard` display |
| Error / warning | Orange | `#E67E22` | Error messages |

All embed builders are centralised in `utils/embeds.py` to ensure no cog defines its own colour values.

### 7.5 Demo Server Population

Before the live demo, the test server must be populated with realistic-looking data to demonstrate the bot looks "highly utilised." This requires a setup script that:

- Creates 5-8 fake user records in the `users` table with realistic usernames.
- Creates 3-4 past sessions with completed timestamps and GPT-4o generated summaries.
- Populates `quiz_scores` with varied scores across users, creating a meaningful leaderboard ranking.
- Sets streak values so that 2-3 users show multi-day streaks.

This script is in `tests/seed_demo_data.py` and is run once before the Day 6 demo.

---

## 8. Day 6 — Demo Preparation & Defence

**Goal:** A flawless live demonstration and a confident technical defence of every architectural decision.

### 8.1 Demo Script

The demo follows this exact sequence — rehearse it until it takes under 8 minutes:

1. Show the populated server: past sessions, leaderboard, active members.
2. Type `/study start "Process Scheduling — Round Robin vs Priority Scheduling"`.
3. Bot posts the teal session-start embed. Pomodoro timer begins (demo mode: 2-minute focus, 1-minute break).
4. A team member types `/ask "What is the difference between preemptive and non-preemptive scheduling?"` — show the bot retrieving from the textbook.
5. A team member joins the voice channel and speaks about the topic for 30 seconds.
6. The Pomodoro break fires. Bot posts the green break embed. Bot posts a quiz question.
7. Team members react with different answers. Timer fires. Correct answer is revealed.
8. Type `/study end`. Bot generates and posts the session summary — point to the specific voice content referenced in the summary.
9. Type `/leaderboard` — show the updated scores.

**Backup plan.** A screen recording of a successful dry run is saved and ready to play if the live bot fails. This is explicitly required by the Day 6 spec.

### 8.2 Technical Defence Preparation

The evaluation panel will probe three areas:

**Async architecture.** Be prepared to explain why `asyncio` was used and how it keeps the bot responsive. The key insight: `await`ing an OpenAI API call yields control back to the event loop, allowing the bot to respond to other commands while waiting. Without `await`, the bot would freeze during every API call.

**RAG pipeline.** Be prepared to explain why ChromaDB uses per-guild collections, how chunk overlap prevents information loss at boundaries, and why cosine similarity is the right distance metric for semantic search (it measures angle, not magnitude, so a long paragraph and a short sentence about the same topic still match well).

**Privacy and voice recording.** The bot must announce recording when it starts (`/study start`), process audio locally where possible (faster-whisper), and flush buffers immediately after transcription. There is no persistent raw audio storage. The transcript is stored but can be deleted by an admin command.

---

## 9. Cross-Cutting Concerns

### 9.1 Error Handling Strategy

Every external call (OpenAI API, ChromaDB, PostgreSQL, Discord API) is wrapped in a `try/except` block. The error handling strategy follows this hierarchy:

- **Transient errors** (network timeouts, rate limits): Celery retry with exponential backoff. Notify the user only after 3 failed retries.
- **User errors** (invalid command, no active session): `interaction.response.send_message(message, ephemeral=True)` — visible only to the invoking user.
- **System errors** (DB connection lost, ChromaDB collection missing): Log the full traceback, post a generic "something went wrong" message to the channel, alert via the bot owner's DM if configured.
- **Voice disconnect**: Automatic reconnect loop with up to 5 retries. Preserve audio buffer across disconnects.

### 9.2 Logging

All logs use Python's `logging` module with structured output (timestamp, level, logger name, message). Every significant event is logged: session start/end, quiz generation, RAG query, voice buffer flush, Celery task dispatch. The log level is `DEBUG` in development and `INFO` in production, configurable via `ENVIRONMENT` in `.env`.

Logs are written to stdout (Docker captures them automatically) and optionally to a rotating file handler for production.

### 9.3 Rate Limiting

The bot enforces per-command cooldowns using Discord.py's `@commands.cooldown` decorator where appropriate. `/ask` has a 5-second per-user cooldown (prevents spam while an API call is in flight). `/quiz` has a 60-second per-guild cooldown (there can only be one active quiz anyway, but the cooldown prevents the command from being re-issued before the previous quiz locks). `/study start` has no cooldown (there is a logical guard against double-starting).

### 9.4 Security Considerations

- The `/upload` command (PDF ingestion) is restricted to users with the `Manage Server` Discord permission. Non-admins cannot inject arbitrary content into the knowledge base.
- Slash command responses use `ephemeral=True` for error messages and private information — these are visible only to the invoking user.
- No raw audio is logged, stored, or transmitted beyond the Whisper transcription call.
- All database queries use parameterised statements via asyncpg — no string interpolation in SQL.

---

## 10. Testing Strategy

### 10.1 Unit Tests

Unit tests live in `tests/` and run without a Discord connection or real API keys. Mock objects replace the OpenAI client and ChromaDB client.

**`test_rag.py`** — Tests the chunking logic (correct chunk count and overlap), the metadata assignment (every chunk has the correct filename and page), and the query function's error handling (collection not found, empty results, malformed GPT-4o response).

**`test_quiz.py`** — Tests the quiz state machine (only one active quiz per guild, reactions ignored when locked), the JSON schema validation (missing fields raise errors), and the scoring logic (correct vote increments score, incorrect does not).

**`test_db.py`** — Tests the streak update logic (consecutive days increment, missed days reset, same-day participation is idempotent) and the leaderboard view (correct ordering, correct accuracy calculation).

### 10.2 Integration Test — Day 2 KPI

Before the Day 2 submission, run the following integration test from the command line (not through Discord):

1. Ingest a known PDF (an OS textbook chapter with a definition of "mutex").
2. Call `query_rag(guild_id=TEST_GUILD_ID, question="What is a mutex?")` directly.
3. Assert that the returned answer contains the word "mutex" and that at least one source citation is present.

This test proves the RAG pipeline works end-to-end before the Discord interface is connected.

### 10.3 Day 3 Test Cases

The following test cases must be demonstrable for the Day 3 submission:

- **Test case 1:** A user who is not in the active session reacts to the quiz — their vote is not recorded.
- **Test case 2:** A user changes their reaction (removes 🇦, adds 🇧) — only 🇧 is counted.
- **Test case 3:** The quiz fires exactly 60 seconds after posting, regardless of how many reactions have been received.
- **Test case 4:** Two guilds run simultaneous quizzes — neither interferes with the other.

---

## 11. Deployment

### 11.1 Docker Compose Setup

The production environment runs three Docker containers orchestrated by Docker Compose:

**`db`** — PostgreSQL 15 with a named volume for persistence. The `schema.sql` init script runs on first start.

**`redis`** — Redis 7 (used as Celery broker and result backend). No persistence required — task queue data is ephemeral.

**`bot`** — The main bot process. Depends on `db` and `redis`. Runs `python bot.py`. The Celery worker runs in the same container for simplicity (could be split in production).

The `CHROMA_PERSIST_DIR` maps to a named Docker volume, ensuring ChromaDB embeddings persist across container restarts.

### 11.2 First-Run Checklist

Before the bot goes live for the first time:

1. Copy `.env.example` to `.env` and fill in all values.
2. Run `docker compose up -d db redis` to start the database and message broker.
3. Run `python -m db.database` to initialise the PostgreSQL schema.
4. Run `docker compose up -d bot` to start the bot.
5. Invite the bot to the Discord server using the OAuth2 URL with the correct scopes and permissions.
6. Upload a course PDF using `/upload` from a server administrator account.
7. Run the Day 2 integration test to verify the RAG pipeline.
8. Type `/ask` in the Discord server to verify the end-to-end flow.

### 11.3 Recommended Development Workflow

During development, run only `db` and `redis` via Docker, and run the bot directly with `python bot.py` for faster iteration. Use guild-scoped slash command sync (passing `guild=discord.Object(id=YOUR_TEST_GUILD_ID)` to `tree.sync()`) so command changes propagate instantly instead of waiting for global propagation.

Set `POMODORO_FOCUS_MINS=2` and `POMODORO_BREAK_MINS=1` in `.env` for testing — waiting 25 minutes per cycle is not viable during development.

---

*Implementation Plan v1.0 — Project 20: AI Study Group Facilitator Bot*
*All architectural decisions documented here supersede informal team discussions.*
*Update this document when any design decision changes — it is the source of truth.*
