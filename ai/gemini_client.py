"""
ai/gemini_client.py — Provider-agnostic LLM client
Supports: groq (default) | gemini
Switch provider via LLM_PROVIDER in .env — no code changes needed.
"""

import json
import asyncio
import logging
from config import config

log = logging.getLogger("llm")


# ── Unified interface ─────────────────────────────────────────────────────────

async def ask(prompt: str, system: str | None = None) -> str:
    """Send a prompt, return text response. Provider selected by LLM_PROVIDER env var."""
    if config.LLM_PROVIDER == "gemini":
        return await _ask_gemini(prompt, system)
    return await _ask_groq(prompt, system)


async def ask_json(prompt: str, system: str | None = None) -> dict:
    """Send a prompt expecting a JSON response back."""
    json_instruction = "\n\nYou must respond with valid JSON only. No markdown, no explanation, no code fences."
    system_block = (system or "") + json_instruction
    text = await ask(prompt, system=system_block)
    text = text.strip()
    # Strip markdown code fences if model wraps it anyway
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


# ── Groq ──────────────────────────────────────────────────────────────────────

async def _ask_groq(prompt: str, system: str | None = None) -> str:
    from groq import Groq
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    client = Groq(api_key=config.GROQ_API_KEY)
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
    )
    return response.choices[0].message.content.strip()


# ── Gemini (fallback) ─────────────────────────────────────────────────────────

async def _ask_gemini(prompt: str, system: str | None = None) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    contents = [types.Content(role="user", parts=[types.Part(text=full_prompt)])]

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(model="gemini-2.0-flash", contents=contents)
    )
    return response.text.strip()
