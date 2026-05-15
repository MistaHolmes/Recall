"""
ai/summarizer.py — End-of-session summary generation via Gemini
"""

import logging
from ai.gemini_client import ask

log = logging.getLogger("summarizer")

SYSTEM_PROMPT = """You are an AI study session analyst.
Generate a structured session summary with exactly these four sections:

## Key Takeaways
(3-5 bullet points of the most important concepts covered)

## Questions Raised
(Questions asked during the session that need follow-up)

## Action Items
(Concrete tasks students should complete before next session)

## Quiz Performance
(Summary of quiz results provided)

IMPORTANT: Only reference content that is explicitly present in the
transcript or chat log provided.  If those sources say "No voice
transcript available" or "No chat messages recorded", do NOT invent or
fabricate discussion points — instead write "No data recorded for this
session" under each affected section and skip generic advice.
Keep the total summary under 400 words."""


async def generate_summary(
    topic: str,
    transcript: str,
    chat_log: list[str],
    quiz_scores: dict[str, int],  # {username: points}
) -> str:
    """Generate a structured session summary."""

    chat_text = "\n".join(chat_log[-60:]) if chat_log else "No chat messages recorded."
    transcript_text = transcript.strip() if transcript else "No voice transcript available."

    scores_text = "\n".join([f"  {user}: {pts} points" for user, pts in quiz_scores.items()])
    if not scores_text:
        scores_text = "  No quiz attempts recorded."

    prompt = f"""Session Topic: {topic}

Voice Transcript:
{transcript_text}

Text Chat (last 60 messages):
{chat_text}

Quiz Scores:
{scores_text}

Generate the session summary now."""

    return await ask(prompt, system=SYSTEM_PROMPT)


# ── Standalone voice meeting summary ─────────────────────────────────────────

_VOICE_SYSTEM_PROMPT = """You are a meeting notes assistant.
Generate a concise meeting summary with exactly these three sections:

## Summary
(2-3 sentence overview of what was discussed)

## Key Points
(3-5 bullet points of the main topics, ideas, or decisions)

## Action Items
(Any tasks, follow-ups, or next steps mentioned — write "None mentioned" if absent)

Be specific and reference actual content from the transcript.
Keep the total summary under 300 words."""


async def generate_voice_summary(transcript: str) -> str:
    """Generate a summary for a standalone voice meeting (no study session)."""
    prompt = f"""Voice Recording Transcript:
{transcript.strip()}

Generate the meeting summary now."""
    return await ask(prompt, system=_VOICE_SYSTEM_PROMPT)
