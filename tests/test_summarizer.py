"""
tests/test_summarizer.py — Unit tests for ai/summarizer.py
Mocks ai.gemini_client.ask so no LLM calls are made.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


_MOCK_SUMMARY = """## Key Takeaways
- HPA uses connection density as the scaling metric.

## Questions Raised
- What happens under burst traffic?

## Action Items
- Review StatefulAutoscaler experiment results.

## Quiz Performance
- MistaHolmes: 10 points"""


class TestGenerateSummary:
    def test_returns_string(self):
        with patch("ai.summarizer.ask", new_callable=AsyncMock, return_value=_MOCK_SUMMARY):
            from ai.summarizer import generate_summary
            result = _run(generate_summary(
                topic="Kubernetes HPA",
                transcript="Pod scaling discussion",
                chat_log=["Q: what is HPA?", "A: Horizontal Pod Autoscaler"],
                quiz_scores={"MistaHolmes": 10},
            ))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_llm_output_verbatim(self):
        with patch("ai.summarizer.ask", new_callable=AsyncMock, return_value=_MOCK_SUMMARY):
            from ai.summarizer import generate_summary
            result = _run(generate_summary("topic", "transcript", [], {}))
        assert result == _MOCK_SUMMARY

    def test_topic_in_prompt(self):
        with patch("ai.summarizer.ask", new_callable=AsyncMock, return_value="ok") as mock_ask:
            from ai.summarizer import generate_summary
            _run(generate_summary("Kubernetes HPA", "", [], {}))

        prompt_arg = mock_ask.call_args[0][0]
        assert "Kubernetes HPA" in prompt_arg

    def test_quiz_scores_in_prompt(self):
        with patch("ai.summarizer.ask", new_callable=AsyncMock, return_value="ok") as mock_ask:
            from ai.summarizer import generate_summary
            _run(generate_summary("topic", "", [], {"Alice": 15, "Bob": 5}))

        prompt_arg = mock_ask.call_args[0][0]
        assert "Alice" in prompt_arg
        assert "Bob" in prompt_arg

    def test_chat_log_capped_at_60_entries(self):
        """The summariser should only include the last 60 chat lines to avoid
        exhausting the LLM context window."""
        long_log = [f"msg {i}" for i in range(100)]

        with patch("ai.summarizer.ask", new_callable=AsyncMock, return_value="ok") as mock_ask:
            from ai.summarizer import generate_summary
            _run(generate_summary("topic", "", long_log, {}))

        prompt_arg = mock_ask.call_args[0][0]
        # The 1st message should NOT appear in the capped prompt
        assert "msg 0" not in prompt_arg
        # The last message SHOULD appear
        assert "msg 99" in prompt_arg

    def test_missing_transcript_handled(self):
        """None or empty transcript must not cause an exception."""
        with patch("ai.summarizer.ask", new_callable=AsyncMock, return_value="ok"):
            from ai.summarizer import generate_summary
            # Should not raise
            _run(generate_summary("topic", "", [], {}))
            _run(generate_summary("topic", "   ", [], {}))

    def test_empty_quiz_scores_handled(self):
        with patch("ai.summarizer.ask", new_callable=AsyncMock, return_value="ok") as mock_ask:
            from ai.summarizer import generate_summary
            _run(generate_summary("topic", "", [], {}))

        prompt_arg = mock_ask.call_args[0][0]
        assert "No quiz attempts" in prompt_arg

    def test_system_prompt_passed_to_ask(self):
        with patch("ai.summarizer.ask", new_callable=AsyncMock, return_value="ok") as mock_ask:
            from ai.summarizer import generate_summary
            _run(generate_summary("topic", "", [], {}))

        _, kwargs = mock_ask.call_args
        # system is passed as second positional or keyword arg
        system_arg = kwargs.get("system") or (mock_ask.call_args[0][1] if len(mock_ask.call_args[0]) > 1 else None)
        assert system_arg is not None
        assert "session" in system_arg.lower() or "summary" in system_arg.lower()
