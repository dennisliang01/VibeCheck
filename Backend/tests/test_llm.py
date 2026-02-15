"""Tests for LLM wrapper (structured outputs, concurrency, error handling)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from codeval.llm import (
    _extract_json,
    _truncate_context,
    complete,
    is_llm_available,
    set_concurrency,
    _get_semaphore,
    _LLM_CONCURRENCY,
)
from codeval.schemas import AgentReport


class TestHelpers:
    def test_truncate_context_short(self):
        assert _truncate_context("hello", 100) == "hello"

    def test_truncate_context_long(self):
        text = "x" * 50_000
        result = _truncate_context(text, 1000)
        assert len(result) <= 1000
        assert "truncated" in result

    def test_extract_json_plain(self):
        data = _extract_json('{"agent": "test"}')
        assert data["agent"] == "test"

    def test_extract_json_markdown_block(self):
        data = _extract_json('```json\n{"agent": "test"}\n```')
        assert data["agent"] == "test"

    def test_extract_json_generic_block(self):
        data = _extract_json('```\n{"agent": "test"}\n```')
        assert data["agent"] == "test"


class TestConcurrency:
    def test_set_concurrency(self):
        set_concurrency(5)
        # Reset semaphore
        import codeval.llm as llm_mod
        assert llm_mod._LLM_CONCURRENCY == 5
        assert llm_mod._LLM_SEMAPHORE is None  # Reset, will be re-created lazily
        # Restore default
        set_concurrency(3)


class TestComplete:
    @pytest.mark.asyncio
    async def test_complete_returns_none_without_keys(self):
        """Should return None when no API keys are set."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}, clear=False):
            result = await complete("sys", "user", AgentReport)
            assert result is None

    @pytest.mark.asyncio
    async def test_complete_claude_structured_output(self):
        """Verify structured output path is used for Claude."""
        mock_response = MagicMock()
        mock_response.parsed_output = AgentReport(
            agent="test",
            findings=[],
        )

        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.parse = AsyncMock(return_value=mock_response)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            # AsyncAnthropic is lazily imported inside _complete_claude, so patch at source
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                # Reset semaphore for fresh test
                import codeval.llm as llm_mod
                llm_mod._LLM_SEMAPHORE = None

                result = await complete("system prompt", "user prompt", AgentReport)

                assert result is not None
                assert result.agent == "test"
                # Verify .parse() was called (not .create())
                mock_client.messages.parse.assert_called_once()
                call_kwargs = mock_client.messages.parse.call_args
                assert call_kwargs.kwargs.get("output_format") == AgentReport
                assert call_kwargs.kwargs.get("max_tokens") == 8192

    @pytest.mark.asyncio
    async def test_complete_handles_rate_limit(self):
        """Should retry with backoff on 429 errors."""
        call_count = 0

        async def _mock_parse(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Error 429: rate limit exceeded")
            mock_resp = MagicMock()
            mock_resp.parsed_output = AgentReport(agent="test")
            return mock_resp

        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.parse = _mock_parse

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                import codeval.llm as llm_mod
                llm_mod._LLM_SEMAPHORE = None

                result = await complete("sys", "user", AgentReport)
                assert result is not None
                assert call_count == 3  # Two failures + one success
