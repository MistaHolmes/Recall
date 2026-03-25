"""
tests/test_quiz_engine.py — Unit tests for ai/quiz_engine.py
Mocks ai.rag_pipeline.query and ai.gemini_client.ask_json.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


GUILD_ID = 111222333
TOPIC    = "Kubernetes HPA"

_VALID_QUIZ = {
    "question":      "What metric does the HPA controller use?",
    "options":       ["A) CPU", "B) Memory", "C) Connection density", "D) Disk I/O"],
    "correct_index": 2,
    "explanation":   "The paper proposes a connection-density-driven operator.",
}

_RAG_RESULT = {
    "context":   "[Source: doc.pdf p.4]\nThe operator monitors connection density.",
    "citations": ["doc.pdf (p.4)"],
}


class TestGenerateQuiz:
    def test_returns_dict_with_required_keys(self):
        with patch("ai.quiz_engine.query", return_value=_RAG_RESULT), \
             patch("ai.quiz_engine.ask_json", new_callable=AsyncMock, return_value=_VALID_QUIZ):
            from ai.quiz_engine import generate_quiz
            result = _run(generate_quiz(GUILD_ID, TOPIC))

        for key in ("question", "options", "correct_index", "explanation"):
            assert key in result, f"Missing key: {key}"

    def test_citations_appended_from_rag(self):
        with patch("ai.quiz_engine.query", return_value=_RAG_RESULT), \
             patch("ai.quiz_engine.ask_json", new_callable=AsyncMock, return_value=dict(_VALID_QUIZ)):
            from ai.quiz_engine import generate_quiz
            result = _run(generate_quiz(GUILD_ID, TOPIC))

        assert result["citations"] == _RAG_RESULT["citations"]

    def test_correct_index_is_in_valid_range(self):
        with patch("ai.quiz_engine.query", return_value=_RAG_RESULT), \
             patch("ai.quiz_engine.ask_json", new_callable=AsyncMock, return_value=dict(_VALID_QUIZ)):
            from ai.quiz_engine import generate_quiz
            result = _run(generate_quiz(GUILD_ID, TOPIC))

        assert 0 <= result["correct_index"] <= 3

    def test_has_four_options(self):
        with patch("ai.quiz_engine.query", return_value=_RAG_RESULT), \
             patch("ai.quiz_engine.ask_json", new_callable=AsyncMock, return_value=dict(_VALID_QUIZ)):
            from ai.quiz_engine import generate_quiz
            result = _run(generate_quiz(GUILD_ID, TOPIC))

        assert len(result["options"]) == 4

    def test_rag_context_passed_to_llm_prompt(self):
        """The RAG context string must appear in the prompt forwarded to ask_json."""
        with patch("ai.quiz_engine.query", return_value=_RAG_RESULT), \
             patch("ai.quiz_engine.ask_json", new_callable=AsyncMock, return_value=dict(_VALID_QUIZ)) as mock_ask:
            from ai.quiz_engine import generate_quiz
            _run(generate_quiz(GUILD_ID, TOPIC))

        prompt_arg = mock_ask.call_args[0][0]
        assert _RAG_RESULT["context"] in prompt_arg

    def test_topic_passed_to_llm_prompt(self):
        with patch("ai.quiz_engine.query", return_value=_RAG_RESULT), \
             patch("ai.quiz_engine.ask_json", new_callable=AsyncMock, return_value=dict(_VALID_QUIZ)) as mock_ask:
            from ai.quiz_engine import generate_quiz
            _run(generate_quiz(GUILD_ID, TOPIC))

        prompt_arg = mock_ask.call_args[0][0]
        assert TOPIC in prompt_arg

    def test_graceful_fallback_when_no_material_uploaded(self):
        """If query() raises RuntimeError (empty collection), generate_quiz
        must still resolve — it falls back to parametric LLM knowledge."""
        with patch("ai.quiz_engine.query", side_effect=RuntimeError("No course materials")), \
             patch("ai.quiz_engine.ask_json", new_callable=AsyncMock, return_value=dict(_VALID_QUIZ)):
            from ai.quiz_engine import generate_quiz
            # Should not raise
            result = _run(generate_quiz(GUILD_ID, TOPIC))

        for key in ("question", "options", "correct_index", "explanation"):
            assert key in result

    def test_empty_citations_on_fallback(self):
        """Fallback path should produce an empty citations list."""
        with patch("ai.quiz_engine.query", side_effect=RuntimeError("No course materials")), \
             patch("ai.quiz_engine.ask_json", new_callable=AsyncMock, return_value=dict(_VALID_QUIZ)):
            from ai.quiz_engine import generate_quiz
            result = _run(generate_quiz(GUILD_ID, TOPIC))

        assert result.get("citations") == []

    def test_llm_exception_propagates(self):
        """If ask_json raises (e.g. network error), it should propagate."""
        with patch("ai.quiz_engine.query", return_value=_RAG_RESULT), \
             patch("ai.quiz_engine.ask_json", new_callable=AsyncMock, side_effect=Exception("LLM down")):
            from ai.quiz_engine import generate_quiz
            with pytest.raises(Exception, match="LLM down"):
                _run(generate_quiz(GUILD_ID, TOPIC))
