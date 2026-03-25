# Phase 3 — Quiz Engine & Session Management
### Technical Implementation Report

| Field | Value |
|---|---|
| **Project** | AI Study Group Facilitator — Discord Bot |
| **Phase** | 3 — MCQ quiz engine, Pomodoro study sessions, leaderboard |
| **Date** | 2026-03-25 |
| **Runtime** | Python 3.14.2 · discord.py 2.7.1 · asyncpg · Groq llama-3.3-70b-versatile |
| **Status** | ✅ Operational — quiz generation, reaction voting, score recording verified in production |
| **Depends On** | Phase 1 (bot, DB, LLM client), Phase 2 (RAG corpus for quiz topics) |

---

## Table of Contents

1. [Abstract](#1-abstract)
2. [Motivation & Research Context](#2-motivation--research-context)
3. [Phase 3 Architecture](#3-phase-3-architecture)
4. [Component Deep-Dives](#4-component-deep-dives)
   - 4.1 [Study Session Lifecycle — `cogs/study.py`](#41-study-session-lifecycle--cogsstudypy)
   - 4.2 [Pomodoro Timer Loop](#42-pomodoro-timer-loop)
   - 4.3 [Quiz Engine — `cogs/quiz.py`](#43-quiz-engine--cogsquizpy)
   - 4.4 [Quiz Generation — `ai/quiz_engine.py`](#44-quiz-generation--aiquiz_enginepy)
   - 4.5 [Reaction-Based Voting](#45-reaction-based-voting)
   - 4.6 [Summary Generation — `ai/summarizer.py`](#46-summary-generation--aisummarizerpy)
5. [In-Memory Session Model](#5-in-memory-session-model)
6. [Database Interactions](#6-database-interactions)
7. [Edge Cases & Failure Modes](#7-edge-cases--failure-modes)
8. [Test Checklist Before Phase 4](#8-test-checklist-before-phase-4)
9. [Appendices](#9-appendices)

---

## 1. Abstract

Phase 3 introduces the **study session and quiz engine** — the primary engagement features of the bot. When a user starts a study session (`/study start`), the bot registers the session in PostgreSQL, allocates an in-memory state dictionary, and launches a Pomodoro timer task (25-minute focus blocks separated by 5-minute breaks). At each break, the bot automatically generates and posts a multiple-choice question based on the session topic, using LLM-structured JSON output (`ask_json()`). Users answer by reacting with regional-indicator emoji. Scores are persisted in the `quiz_scores` table, powering a leaderboard (`/leaderboard`). On `/study end`, the bot generates a coherent bullet-point summary of the session's chat log and Q&A activity.

---

## 2. Motivation & Research Context

**Spaced practice and testing effect:** Cognitive psychology research (Roediger & Karpicke, 2006) consistently finds that interspersed low-stakes testing produces significantly better long-term retention than passive re-reading. The Pomodoro-triggered auto-quiz instantiates this "testing effect" automatically without requiring any user to initiate a quiz.

**Pomodoro Technique:** F. Cirillo's (1980s) time-management method alternates 25-minute focused work intervals ("Pomodoros") with 5-minute rest intervals. It has been empirically associated with reduced mental fatigue and improved attention in knowledge-worker studies. Implemented as an asyncio background task, the bot enforces this cadence for all session participants.

**Structured output from LLMs:** MCQ generation requires output that is machine-parseable (question text, four answer strings, a correct-index integer, an explanation). Forcing LLM output into JSON via a system prompt (`ask_json()` in Phase 1) is more robust than regex-parsing free text and allows full control over the MCQ schema.

---

## 3. Phase 3 Architecture

```
User                    bot.active_sessions[guild_id]
  │                               (in-memory dict)
  │  /study start topic:Kubernetes
  ▼
cogs/study.py  StudyCog.study_start()
  │  1. DB: upsert user, create_session()
  │  2. Allocate session dict (topic, channel, timestamps, buffers, task=None)
  │  3. Launch asyncio.Task(_pomodoro_loop)
  │
  │  ─────── 25 min focus period ──────────
  │
  │  _pomodoro_loop (background Task)
  │  4. await asyncio.sleep(25 * 60)
  │  5. Notify "Focus period over! Starting quiz..."
  │  6. await QuizCog.dispatch_quiz(guild_id, channel, topic, session_id)
  │
  ▼
cogs/quiz.py  QuizCog.dispatch_quiz()
  │  7. ai/quiz_engine.py: generate_quiz(topic, context_from_RAG)
  │       └─ gemini_client.ask_json(prompt, schema) → {question, options[4], correct_index, explanation}
  │  8. Build Discord embed (4-choice MCQ)
  │  9. Add 4 regional-indicator emoji reactions (🇦🇧🇨🇩)
  │  10. Set 60s auto-close timer
  │
  │  ─────── users react within 60s ──────────
  │
  │  on_raw_reaction_add listener
  │  11. Record first reaction per user, ignore duplicates
  │
  │  _close_quiz() [triggered by timer or explicitly]
  │  12. Tally votes, reveal correct answer
  │  13. DB: record_quiz_answer() per voter
  │  14. Update session["quiz_scores"]
  │  15. Announce result embed in channel
  │
  │  ─────── 5 min break period ──────────
  │
  │  _pomodoro_loop continues; await asyncio.sleep(5 * 60); repeat
  │
  │  /study end
  ▼
cogs/study.py  StudyCog.study_end()
  │  16. Cancel pomodoro_task
  │  17. ai/summarizer.py: generate_summary(chat_log, quiz_scores)
  │  18. DB: end_session(), update_streak()
  │  19. Post summary embed
```

---

## 4. Component Deep-Dives

### 4.1 Study Session Lifecycle — `cogs/study.py`

```python
@study.command(name="start", description="Start a study session")
async def study_start(self, interaction: discord.Interaction, topic: str):
    if interaction.guild_id in self.bot.active_sessions:
        return await interaction.response.send_message(
            embed=embeds.error("A study session is already active in this server."), ephemeral=True
        )

    await upsert_user(interaction.user.id, interaction.user.display_name)
    session_id = await create_session(interaction.guild_id, interaction.user.id, topic)

    self.bot.active_sessions[interaction.guild_id] = {
        "session_id": session_id,
        "topic": topic,
        "channel_id": interaction.channel_id,
        "started_at": datetime.now(timezone.utc),
        "voice_transcript": [],
        "chat_log": [],
        "quiz_scores": {},          # {user_id: [True, False, ...]}
        "pomodoro_task": None,
    }
    task = asyncio.create_task(self._pomodoro_loop(interaction.guild_id, interaction.channel))
    self.bot.active_sessions[interaction.guild_id]["pomodoro_task"] = task

    await interaction.response.send_message(
        embed=embeds.session_start(topic, session_id)
    )
```

**Session end:**

```python
@study.command(name="end", description="End the current study session")
async def study_end(self, interaction: discord.Interaction):
    session = self.bot.active_sessions.pop(interaction.guild_id, None)
    if not session:
        return await interaction.response.send_message(
            embed=embeds.error("No active session."), ephemeral=True
        )

    # Cancel Pomodoro background task
    if session["pomodoro_task"] and not session["pomodoro_task"].done():
        session["pomodoro_task"].cancel()

    await interaction.response.defer(thinking=True)

    # Generate AI summary from chat log
    summary = await generate_summary(session["chat_log"], session["quiz_scores"])
    duration = int((datetime.now(timezone.utc) - session["started_at"]).total_seconds() / 60)

    await end_session(session["session_id"], duration)
    await update_streak(interaction.user.id)

    await interaction.followup.send(embed=embeds.session_end(summary, duration))
```

---

### 4.2 Pomodoro Timer Loop

```python
POMODORO_WORK_SECS  = 25 * 60   # 25 minutes of focused study
POMODORO_BREAK_SECS =  5 * 60   #  5 minutes of rest / quiz time

async def _pomodoro_loop(self, guild_id: int, channel: discord.TextChannel):
    try:
        cycle = 0
        while True:
            cycle += 1
            # ── Focus period ──────────────────────────────────────────
            await channel.send(embed=embeds.info(
                f"🍅 **Pomodoro #{cycle} started!** Focus for 25 minutes."
            ))
            await asyncio.sleep(POMODORO_WORK_SECS)

            # ── Break: auto-quiz ──────────────────────────────────────
            session = self.bot.active_sessions.get(guild_id)
            if not session:
                break
            await channel.send(embed=embeds.info(
                "⏸️ **Focus period over!** Time for a 5-minute quiz break."
            ))
            quiz_cog: QuizCog = self.bot.cogs.get("QuizCog")
            if quiz_cog:
                await quiz_cog.dispatch_quiz(guild_id, channel, session["topic"],
                                             session["session_id"])
            await asyncio.sleep(POMODORO_BREAK_SECS)

    except asyncio.CancelledError:
        pass   # clean shutdown — do not propagate
```

**Design decisions:**
- `CancelledError` is silently swallowed. This is correct asyncio practice for tasks that are expected to be cancelled (e.g., via `task.cancel()` on `/study end` or on bot shutdown).
- The loop re-fetches `self.bot.active_sessions.get(guild_id)` on each iteration — if the session was externally terminated between cycles, the loop exits cleanly.
- `quiz_cog: QuizCog = self.bot.cogs.get("QuizCog")` looks up the quiz cog at runtime rather than holding a reference, avoiding circular dependency issues.

---

### 4.3 Quiz Engine — `cogs/quiz.py`

```python
EMOJI_MAP = {"🇦": 0, "🇧": 1, "🇨": 2, "🇩": 3}
REACTION_EMOJIS = ["🇦", "🇧", "🇨", "🇩"]
QUIZ_TIMEOUT_SECS = 60

active_quizzes: dict[int, dict] = {}   # guild_id → quiz state

async def dispatch_quiz(self, guild_id: int, channel: discord.TextChannel,
                        topic: str, session_id: int):
    quiz = await generate_quiz(topic)
    if not quiz:
        await channel.send(embed=embeds.error("Quiz generation failed — skipping this break."))
        return

    embed = embeds.quiz_question(quiz["question"], quiz["options"])
    msg = await channel.send(embed=embed)
    for emoji in REACTION_EMOJIS:
        await msg.add_reaction(emoji)

    active_quizzes[guild_id] = {
        "message_id": msg.id,
        "channel_id": channel.id,
        "question": quiz["question"],
        "options": quiz["options"],
        "correct_index": quiz["correct_index"],
        "explanation": quiz["explanation"],
        "citations": quiz.get("citations", []),
        "votes": {},           # {user_id: option_index}
        "session_id": session_id,
    }

    # Auto-close after timeout
    asyncio.create_task(self._auto_close_quiz(guild_id, delay=QUIZ_TIMEOUT_SECS))
```

**Vote tallying in `_close_quiz()`:**

```python
async def _close_quiz(self, guild_id: int):
    quiz = active_quizzes.pop(guild_id, None)
    if not quiz:
        return

    correct = quiz["correct_index"]
    result_lines = []
    for uid, chosen in quiz["votes"].items():
        is_correct = chosen == correct
        await record_quiz_answer(quiz["session_id"], uid, quiz["question"],
                                 quiz["options"][chosen], is_correct)
        session = self.bot.active_sessions.get(guild_id)
        if session:
            session["quiz_scores"].setdefault(uid, []).append(is_correct)
        result_lines.append(f"<@{uid}> chose **{REACTION_EMOJIS[chosen]}** — "
                            f"{'✅ Correct' if is_correct else '❌ Wrong'}")

    await channel.send(embed=embeds.quiz_result(
        quiz["question"], quiz["options"], correct,
        quiz["explanation"], result_lines
    ))
```

---

### 4.4 Quiz Generation — `ai/quiz_engine.py`

```python
MCQ_SCHEMA = {
    "question": "string",
    "options": ["string", "string", "string", "string"],
    "correct_index": "integer (0–3)",
    "explanation": "string (one sentence)",
}

async def generate_quiz(topic: str, context: str = "") -> dict | None:
    prompt = f"""Generate a multiple-choice question about: {topic}

Context (use if provided):
{context if context else "No additional context — use general knowledge."}

Return ONLY a JSON object matching this schema:
{json.dumps(MCQ_SCHEMA, indent=2)}"""

    try:
        result = await ask_json(prompt, system="You are a quiz generator. Output only valid JSON.")
        # Validate required fields
        assert "question" in result
        assert len(result["options"]) == 4
        assert 0 <= result["correct_index"] <= 3
        return result
    except (KeyError, AssertionError, json.JSONDecodeError) as e:
        log.warning(f"Quiz generation failed: {e}")
        return None   # caller handles gracefully
```

**`ask_json()` mechanism** (from Phase 1 `ai/gemini_client.py`):
1. Appends `"Respond ONLY with valid JSON. No markdown, no code fences."` to the system prompt.
2. Calls `ask(prompt, system=combined_system)`.
3. Strips any ` ``` ` code fences the model may still include despite instructions.
4. Runs `json.loads()`. If parsing fails, the exception propagates to the caller (`generate_quiz()`), which returns `None`.

---

### 4.5 Reaction-Based Voting

`on_raw_reaction_add` is used rather than `on_reaction_add` to avoid the message cache requirement for reactions on older messages.

```python
@commands.Cog.listener()
async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    if payload.user_id == self.bot.user.id:
        return    # ignore the bot's own reactions (added as voting buttons)

    guild_id = payload.guild_id
    quiz = active_quizzes.get(guild_id)
    if not quiz or payload.message_id != quiz["message_id"]:
        return    # reaction not on the active quiz message

    emoji = str(payload.emoji)
    if emoji not in EMOJI_MAP:
        return    # not a valid choice emoji

    if payload.user_id in quiz["votes"]:
        return    # first vote is final — no changing answers

    quiz["votes"][payload.user_id] = EMOJI_MAP[emoji]
```

**First-reaction-wins semantics** are enforced by the `if payload.user_id in quiz["votes"]: return` check. Discord does not prevent users from adding multiple reactions, so this guard is essential for fair voting.

---

### 4.6 Summary Generation — `ai/summarizer.py`

```python
async def generate_summary(chat_log: list[str], quiz_scores: dict) -> str:
    # Cap chat log to avoid exceeding LLM context window
    recent_log = chat_log[-60:]
    score_lines = []
    for uid, scores in quiz_scores.items():
        correct = sum(scores)
        total = len(scores)
        score_lines.append(f"User {uid}: {correct}/{total} correct")

    prompt = f"""Summarise this study session in 5–7 bullet points.
Chat log (most recent 60 messages):
{chr(10).join(recent_log)}

Quiz performance:
{chr(10).join(score_lines) if score_lines else 'No quizzes this session.'}"""

    summary = await ask(prompt, system="You are a helpful study assistant. Write concise bullets.")
    return summary
```

The 60-message cap on `chat_log` prevents extremely long sessions from producing a prompt that exceeds the LLM's context window (~8K tokens for Groq llama-3.3-70b-versatile). The `on_message` listener in `StudyCog` appends messages in real time.

---

## 5. In-Memory Session Model

```python
{
    "session_id":      int,          # PostgreSQL sessions.id
    "topic":           str,          # user-specified study topic
    "channel_id":      int,          # Discord channel for notifications
    "started_at":      datetime,     # UTC, for duration calculation on end
    "voice_transcript": list[str],   # populated by Phase 4 Whisper transcription
    "chat_log":        list[str],    # text messages during session
    "quiz_scores":     dict[int, list[bool]],  # {user_id: [correct?, ...]}
    "pomodoro_task":   asyncio.Task | None,    # cancel handle
}
```

The `bot.active_sessions` dict is keyed by `guild_id`, enforcing one active session per guild at a time.

---

## 6. Database Interactions

| Function | Table | Operation |
|---|---|---|
| `upsert_user(user_id, name)` | `users` | `INSERT ... ON CONFLICT DO UPDATE` |
| `create_session(guild_id, user_id, topic)` | `sessions` | `INSERT` — returns `session_id` |
| `end_session(session_id, duration_min)` | `sessions` | `UPDATE SET ended_at, duration_minutes` |
| `record_quiz_answer(session_id, user_id, q, a, correct)` | `quiz_scores` | `INSERT` |
| `update_streak(user_id)` | `streaks` | `INSERT ... ON CONFLICT DO UPDATE` |
| `get_leaderboard(guild_id)` | `leaderboard` VIEW | `SELECT` |

All DB calls are `async def` using an `asyncpg` connection pool. The `leaderboard` view aggregates `quiz_scores` across all sessions for a guild, grouping by user and counting correct answers.

---

## 7. Edge Cases & Failure Modes

### 7.1 Quiz Generation Failure (LLM JSON Parsing Error)

`generate_quiz()` wraps all assertions and `json.loads()` in a `try/except` and returns `None` on failure. `dispatch_quiz()` checks for `None` and sends an error embed rather than posting a malformed quiz. The Pomodoro loop continues normally — the next break will attempt a fresh quiz.

### 7.2 Duplicate Reaction (User Votes Twice)

Handled by the `if payload.user_id in quiz["votes"]: return` guard in `on_raw_reaction_add`. First reaction is final and immutable.

### 7.3 No Active Session at Quiz Time

The Pomodoro loop re-reads `self.bot.active_sessions.get(guild_id)` at break time. If the session was ended by the user between the start of the focus period and the break, `session` will be `None` and the loop will `break` — no quiz is dispatched, no error occurs.

### 7.4 `/quiz` Without an Active Session

`/quiz` is a manual trigger for testing. If no active session exists, `topic` defaults to `"general knowledge"` and `session_id` is set to `None`, so no quiz score is persisted to the database.

### 7.5 Bot Restart Loses In-Memory Sessions

`active_sessions` is an in-memory dict and does not survive process restarts. If the bot crashes during a session, the user must re-run `/study start`. The PostgreSQL `sessions` row will remain open (no `ended_at`). A Phase 6 improvement is to detect stale open sessions on startup and mark them as ended.

### 7.6 asyncio.CancelledError in Pomodoro

`asyncio.sleep()` raises `CancelledError` when the task is cancelled. The `except asyncio.CancelledError: pass` block in `_pomodoro_loop` ensures no traceback is emitted. This is the prescribed asyncio pattern for cooperative cancellation.

---

## 8. Test Checklist Before Phase 4

- [ ] `/study start topic:Python asyncio` — confirms embed, session appears in `bot.active_sessions`.
- [ ] `/study status` — confirms session and running-time embed.
- [ ] Wait for one Pomodoro cycle (or mock-shorten timer for testing) — confirm quiz embed posted with 4 flag reactions.
- [ ] React to the quiz with a correct answer — confirm ✅ result announced.
- [ ] React to the quiz with a wrong answer — confirm ❌ result announced.
- [ ] React twice as the same user — confirm second reaction silently ignored (still shows first vote tally).
- [ ] `/study end` — confirms summary embed, streak update, session DM (if configured).
- [ ] `/leaderboard` — confirms scores from the closed session appear.
- [ ] Force-kill the bot mid-session; restart — confirm new `/study start` works cleanly.

---

## 9. Appendices

### A — MCQ JSON Schema

```json
{
  "question": "What does the `asyncio.CancelledError` exception indicate in Python?",
  "options": [
    "A network timeout has occurred",
    "A coroutine or task has been cancelled",
    "An async function returned None",
    "A context manager was not exited correctly"
  ],
  "correct_index": 1,
  "explanation": "CancelledError is raised inside a coroutine when its Task is cancelled via task.cancel()."
}
```

### B — leaderboard VIEW Schema

```sql
CREATE VIEW leaderboard AS
SELECT
    qs.user_id,
    u.display_name,
    s.guild_id,
    COUNT(*)                   FILTER (WHERE qs.is_correct) AS correct_answers,
    COUNT(*)                                                 AS total_answers,
    ROUND(
        COUNT(*) FILTER (WHERE qs.is_correct)::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 1
    )                                                        AS accuracy_pct
FROM quiz_scores qs
JOIN users    u ON u.user_id    = qs.user_id
JOIN sessions s ON s.session_id = qs.session_id
GROUP BY qs.user_id, u.display_name, s.guild_id;
```

### C — Key Timing Constants

| Constant | Value | Location |
|---|---|---|
| `POMODORO_WORK_SECS` | 1500 s (25 min) | `cogs/study.py` |
| `POMODORO_BREAK_SECS` | 300 s (5 min) | `cogs/study.py` |
| `QUIZ_TIMEOUT_SECS` | 60 s | `cogs/quiz.py` |
| Chat log cap | 60 entries | `ai/summarizer.py` |

### D — References

- Roediger, H. L. & Karpicke, J. D. (2006). *Test-Enhanced Learning: Taking Memory Tests Improves Long-Term Retention.* Psychological Science, 17(3), 249–255.
- Cirillo, F. (2007). *The Pomodoro Technique.* FC Garage.
- asyncio documentation — Task cancellation: https://docs.python.org/3/library/asyncio-task.html#asyncio.Task.cancel
