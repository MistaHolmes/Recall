# AI Study Group Facilitator — Phase 1

Minimal README with setup and common commands for development and testing.

Prerequisites
-------------
- Linux (tested)
- Python 3.14.2
- Git
- A Discord application and bot token with `applications.commands` scope

Quick setup
-----------
1. Clone the repo and change directory:

```bash
git clone <repo-url> Discord_bot_AI
cd Discord_bot_AI
```

2. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create an environment file. Copy `.env.example` to `.env` and fill in keys (Discord token, DB, Groq/Gemini keys):

```bash
cp .env.example .env
# edit .env with your keys
```

Key env vars (examples):

- `DISCORD_BOT_TOKEN` — bot token
- `DISCORD_GUILD_ID` — test guild ID (used for guild-scoped command sync)
- `GROQ_API_KEY` / `GEMINI_API_KEY` — LLM provider keys
- `LLM_PROVIDER` — `groq` or `gemini`
- `DATABASE_URL` — Neon Postgres connection string
- `CHROMA_PERSIST_DIR` — local path for ChromaDB (default `./chroma_data`)

Run the bot
-----------
Start the bot in the foreground for development:

```bash
source venv/bin/activate
python bot.py
```

Stop a running bot and restart (development):

```bash
pkill -f "python bot.py" || true
python bot.py &
```

Run tests:
```bash
venv/bin/python -m pytest tests/ -v --tb=short 2>&1
```

Basic commands (slash commands)
------------------------------
The following slash commands are available in the test guild once the bot is running:

- `/upload` — Upload a PDF and index it into ChromaDB.
- `/files` — List PDFs ingested for the guild.
- `/clearfiles` — Delete the guild's vector collection.
- `/ask` — Ask a question about uploaded course material (RAG + LLM answer).
- `/quiz` — Generate a single multiple-choice question from ingested content.
- `/leaderboard` — Show aggregated quiz scores and streaks.
- `/study start` — Start a study session (Pomodoro-ready).
- `/study end` — End the active study session and generate a summary.
- `/study status` — Show current session status.
- `/voicejoin` / `/voiceleave` — Join/leave voice capture (WaveSink).

Developer notes
---------------
- Commands are synced guild-scoped during development to avoid global propagation delays — set `DISCORD_GUILD_ID` in `.env`.
- If you see the startup warning about `Privileged message content intent is missing`, enable `message_content` and `members` in the Discord Developer Portal and set the same flags to `True` in `bot.py` if you need those features.
- LLM switching: change `LLM_PROVIDER` in `.env` to `groq` or `gemini` and restart the bot. `ai/gemini_client.py` provides a provider-agnostic `ask()` / `ask_json()` API.

Troubleshooting
---------------
- `_pool is None` errors: ensure the DB `DATABASE_URL` is correct and `init_db()` ran (the bot logs `Database pool initialized` during startup).
- 429 / rate-limit errors from LLM: consider switching providers or adding retries/backoff; see `Documentation/phase-1/phase-1_documentation.md` for recommended patterns.

Additional documentation
------------------------
See `Documentation/phase-1/phase-1_documentation.md` for a full technical report, test plan, and evaluation protocol. The validation screenshot is at `Documentation/phase-1/upload-and-ask.png`.

Contact / Next steps
--------------------
Open issues or PRs in the repository for feature requests, tests, or deployment packaging (Docker/systemd).

Testing
-------
Install pytest (already in venv after first run of the bot):

```bash
source venv/bin/activate
pip install pytest pytest-asyncio
```

Run the full unit test suite:

```bash
python -m pytest tests/ -v --tb=short
```

Run a single test module:

```bash
python -m pytest tests/test_rag_pipeline.py -v
python -m pytest tests/test_gemini_client.py -v
python -m pytest tests/test_quiz_engine.py -v
python -m pytest tests/test_summarizer.py -v
```

Phase 4 — Voice transcription (Whisper)
---------------------------------------
Whisper is installed automatically with requirements. The bot loads the model
on first `/voicejoin` call and keeps it cached for the process lifetime.

Change the model size in `.env` (tradeoff: accuracy vs. speed vs. memory):

```dotenv
WHISPER_MODEL=base     # ~74 MB  — fast, good for short utterances
WHISPER_MODEL=small    # ~244 MB — better accuracy
WHISPER_MODEL=medium   # ~769 MB — high accuracy, slower on CPU
```

Phase 5 — Session scheduling
-----------------------------
Schedule a future study session reminder (bot sends a ping in the channel at the given time):

```
/schedule create topic:"Kubernetes HPA" iso_time:"2026-03-26T18:00:00"
/schedule list
/schedule cancel job_id:"session_<guild>_<timestamp>"
```

Times are always UTC. The job fires once and sends an embed reminding the group
to use `/study start`.
