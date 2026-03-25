# How to Use the Study Bot

A quick guide to every command. Type `/` in any channel to see them all in Discord.

---

## Quick Start

1. An admin uploads your course material with `/upload`
2. Start a study session with `/study start`
3. Ask questions, take quizzes, and chat — the bot keeps track
4. End the session with `/study end` to get an AI summary

---

## Commands

### `/ask` — Ask a question
Ask anything about the uploaded course material. The bot searches the documents and gives you a short, cited answer.

**Example:**
```
/ask question: What is the difference between mitosis and meiosis?
```

> Requires at least one PDF to be uploaded first.

---

### `/quiz` — Take a quiz
Generates a multiple-choice question based on the current session topic (or general knowledge if no session is active). React with 🇦 🇧 🇨 🇩 to answer. Results and points are shown when time runs out.

**Example:**
```
/quiz
```

> During an active study session, quizzes also run automatically at the end of each Pomodoro break.

---

### `/study start` — Start a study session
Kicks off a Pomodoro-style study session. The bot posts focus/break reminders and automatically runs quizzes at the end of each cycle. All questions asked and quiz scores during the session are tracked.

**Example:**
```
/study start topic: Chapter 4 — Organic Chemistry
```

---

### `/study end` — End the session
Ends the current session and posts an AI-generated summary of what was covered, including quiz scores.

**Example:**
```
/study end
```

---

### `/voicejoin` — Join voice channel
The bot joins your current voice channel and starts listening. Audio is transcribed using Whisper every 30 seconds and added to the session transcript (used in the final summary).

**Example:**
```
/voicejoin
```

> You must already be in a voice channel.

---

### `/voiceleave` — Leave voice channel
The bot leaves the voice channel and finalises the remaining transcript.

**Example:**
```
/voiceleave
```

---

### `/schedule create` — Schedule a session reminder
Posts a reminder in the current channel at the specified time. Time must be in UTC using ISO 8601 format.

**Example:**
```
/schedule create topic: Finals Revision  iso_time: 2026-04-01T18:00:00
```

The bot will reply with a **Job ID** — save it if you want to cancel later.

---

### `/schedule list` — View upcoming reminders
Shows all scheduled sessions for this server, along with their Job IDs and times.

**Example:**
```
/schedule list
```

---

### `/schedule cancel` — Cancel a reminder
Cancels a scheduled reminder using its Job ID (shown in `/schedule list`).

**Example:**
```
/schedule cancel job_id: session_123456789_1743530400
```

---

## Admin Commands

> These require the **Manage Server** or **Administrator** permission.

### `/upload` — Upload course material
Upload a PDF (max 25 MB). The bot splits it into chunks and indexes it so `/ask` and `/quiz` can use it.

**Example:**
```
/upload file: [attach your PDF]
```

---

### `/files` — List uploaded files
Shows all PDFs currently indexed for this server.

**Example:**
```
/files
```

---

### `/clearfiles` — Delete all course material
Removes all uploaded PDFs and their indexed data for this server. This cannot be undone.

**Example:**
```
/clearfiles
```

---

## Tips

- You can use `/ask` at any time, even without an active session.
- Quiz points only count toward the leaderboard when a `/study` session is running.
- `/voicejoin` works best when everyone in the call speaks clearly — the transcript feeds into the session summary.
- All schedule times are **UTC**. Adjust for your timezone before scheduling.
