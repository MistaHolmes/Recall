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

Be specific — reference actual topics discussed, not generic advice.
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
