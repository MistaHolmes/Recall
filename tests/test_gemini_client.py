"""
tests/test_gemini_client.py — Unit tests for ai/gemini_client.py
Mocks the Groq and Gemini SDK clients; no network calls are made.
"""

import json
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock


# ── Helpers ───────────────────────────────────────────────────────────────────

def _groq_response(text: str):
    """Build a fake Groq ChatCompletion response object."""
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── ask() dispatch tests ──────────────────────────────────────────────────────

class TestAskDispatch:
    def test_dispatches_to_groq_by_default(self):
        with patch("ai.gemini_client._ask_groq", new_callable=AsyncMock) as mock_groq, \
             patch("ai.gemini_client._ask_gemini", new_callable=AsyncMock) as mock_gemini, \
             patch("ai.gemini_client.config") as mock_cfg:

            mock_cfg.LLM_PROVIDER = "groq"
            mock_groq.return_value = "groq answer"

            from ai.gemini_client import ask
            result = _run(ask("What is HPA?"))

        mock_groq.assert_called_once()
        mock_gemini.assert_not_called()
        assert result == "groq answer"

    def test_dispatches_to_gemini_when_configured(self):
        with patch("ai.gemini_client._ask_groq", new_callable=AsyncMock) as mock_groq, \
             patch("ai.gemini_client._ask_gemini", new_callable=AsyncMock) as mock_gemini, \
             patch("ai.gemini_client.config") as mock_cfg:

            mock_cfg.LLM_PROVIDER = "gemini"
            mock_gemini.return_value = "gemini answer"

            from ai.gemini_client import ask
            result = _run(ask("What is HPA?"))

        mock_gemini.assert_called_once()
        mock_groq.assert_not_called()
        assert result == "gemini answer"

    def test_system_prompt_forwarded(self):
        with patch("ai.gemini_client._ask_groq", new_callable=AsyncMock) as mock_groq, \
             patch("ai.gemini_client.config") as mock_cfg:

            mock_cfg.LLM_PROVIDER = "groq"
            mock_groq.return_value = "ok"

            from ai.gemini_client import ask
            _run(ask("prompt text", system="system text"))

        _, kwargs = mock_groq.call_args
        args = mock_groq.call_args[0]
        # system is the second positional arg to _ask_groq
        assert "system text" in args


# ── ask_json() tests ──────────────────────────────────────────────────────────

class TestAskJson:
    def _patch_ask(self, return_value: str):
        return patch("ai.gemini_client.ask", new_callable=AsyncMock, return_value=return_value)

    def test_parses_clean_json(self):
        payload = {"question": "What is X?", "options": ["A", "B"], "correct_index": 0}
        with self._patch_ask(json.dumps(payload)):
            from ai.gemini_client import ask_json
            result = _run(ask_json("generate quiz"))
        assert result == payload

    def test_strips_code_fences(self):
        payload = {"key": "value"}
        wrapped = f"```json\n{json.dumps(payload)}\n```"
        with self._patch_ask(wrapped):
            from ai.gemini_client import ask_json
            result = _run(ask_json("prompt"))
        assert result == payload

    def test_strips_plain_code_fences(self):
        payload = {"a": 1}
        wrapped = f"```\n{json.dumps(payload)}\n```"
        with self._patch_ask(wrapped):
            from ai.gemini_client import ask_json
            result = _run(ask_json("prompt"))
        assert result == payload

    def test_raises_on_invalid_json(self):
        with self._patch_ask("this is not json at all"):
            from ai.gemini_client import ask_json
            with pytest.raises(json.JSONDecodeError):
                _run(ask_json("prompt"))

    def test_appends_json_instruction_to_system(self):
        """ask_json must append the JSON-only instruction before forwarding to ask()."""
        payload = {"x": 1}
        with self._patch_ask(json.dumps(payload)) as mock_ask:
            from ai.gemini_client import ask_json
            _run(ask_json("prompt", system="base system"))

        _, kwargs = mock_ask.call_args
        system_arg = mock_ask.call_args[1].get("system") or mock_ask.call_args[0][1]
        assert "JSON" in system_arg
        assert "base system" in system_arg


# ── _ask_groq() unit tests ────────────────────────────────────────────────────

class TestAskGroq:
    def test_builds_messages_with_system(self):
        fake_resp = _groq_response("  answer text  ")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = fake_resp

        with patch("ai.gemini_client.config") as mock_cfg, \
             patch("ai.gemini_client.Groq", return_value=mock_client, create=True):

            mock_cfg.GROQ_API_KEY = "key"
            mock_cfg.LLM_MODEL = "llama-3.3-70b-versatile"

            # Import fresh to avoid module-level caching issues
            import importlib
            import ai.gemini_client as mod
            result = _run(mod._ask_groq("user prompt", system="sys msg"))

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        roles = [m["role"] for m in messages]
        assert roles == ["system", "user"]
        assert messages[0]["content"] == "sys msg"
        assert messages[1]["content"] == "user prompt"

    def test_no_system_message_when_none(self):
        fake_resp = _groq_response("answer")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = fake_resp

        with patch("ai.gemini_client.config") as mock_cfg, \
             patch("ai.gemini_client.Groq", return_value=mock_client, create=True):

            mock_cfg.GROQ_API_KEY = "key"
            mock_cfg.LLM_MODEL = "llama-3.3-70b-versatile"

            import ai.gemini_client as mod
            result = _run(mod._ask_groq("user prompt", system=None))

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert all(m["role"] != "system" for m in messages)

    def test_strips_whitespace_from_response(self):
        fake_resp = _groq_response("   trailing spaces   ")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = fake_resp

        with patch("ai.gemini_client.config") as mock_cfg, \
             patch("ai.gemini_client.Groq", return_value=mock_client, create=True):

            mock_cfg.GROQ_API_KEY = "key"
            mock_cfg.LLM_MODEL = "any-model"

            import ai.gemini_client as mod
            result = _run(mod._ask_groq("p"))

        assert result == "trailing spaces"
