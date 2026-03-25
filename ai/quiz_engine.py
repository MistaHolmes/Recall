"""
ai/quiz_engine.py — MCQ generation using Gemini + RAG context
"""

import logging
from ai.gemini_client import ask_json
from ai.rag_pipeline import query

log = logging.getLogger("quiz")

SYSTEM_PROMPT = """You are a quiz generator for a university study group.
Generate exactly ONE multiple-choice question based solely on the provided context.
The question must test genuine understanding, not trivia.
Return valid JSON with this exact schema:
{
  "question": "string",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "correct_index": 0,
  "explanation": "string"
}
correct_index is 0-based (0=A, 1=B, 2=C, 3=D)."""


async def generate_quiz(guild_id: int, topic: str) -> dict:
    """
    Generate a quiz question from ingested material for the given topic.
    Returns a dict with: question, options, correct_index, explanation
    """
    try:
        rag = query(guild_id, topic)
        context = rag["context"]
        citations = rag["citations"]
    except RuntimeError:
        # No materials uploaded — generate a generic knowledge question
        context = f"Topic: {topic}"
        citations = []

    prompt = f"Context:\n{context}\n\nTopic: {topic}\n\nGenerate a quiz question about this topic."
    result = await ask_json(prompt, system=SYSTEM_PROMPT)
    result["citations"] = citations
    return result
