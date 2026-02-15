"""LLM wrapper: Anthropic Claude (structured outputs) and OpenAI with static-only fallback."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ~8K tokens ≈ 32K chars for input
MAX_CONTEXT_CHARS = 30_000

# OpenAI
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"

# Anthropic Claude – Sonnet 4.5 supports structured outputs (constrained decoding)
ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

# Concurrency limiter: cap parallel LLM calls to avoid 429 rate-limit storms
_LLM_SEMAPHORE: asyncio.Semaphore | None = None
_LLM_CONCURRENCY: int = 10


def set_concurrency(n: int) -> None:
    """Override the default LLM concurrency limit (default: 3)."""
    global _LLM_SEMAPHORE, _LLM_CONCURRENCY
    _LLM_CONCURRENCY = max(1, n)
    _LLM_SEMAPHORE = None  # Reset so it gets re-created lazily


def _get_semaphore() -> asyncio.Semaphore:
    """Lazily create the semaphore (must be done inside a running event loop)."""
    global _LLM_SEMAPHORE
    if _LLM_SEMAPHORE is None:
        _LLM_SEMAPHORE = asyncio.Semaphore(_LLM_CONCURRENCY)
    return _LLM_SEMAPHORE


def is_llm_available() -> bool:
    """Check if LLM is configured (OpenAI or Anthropic API key present)."""
    return bool(
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    )


def _truncate_context(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Truncate context to fit token limits."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 100] + "\n\n[... truncated for length ...]"


def _extract_json(content: str) -> dict:
    """Extract JSON from LLM response (handle markdown code blocks). Used for OpenAI fallback."""
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


async def _complete_openai(
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
    model: str,
) -> T | None:
    """Call OpenAI API (traditional JSON extraction path)."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            OPENAI_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    parsed = _extract_json(content)
    return schema.model_validate(parsed)


async def _complete_claude(
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
    model: str,
) -> T | None:
    """Call Anthropic Claude API with structured outputs (constrained decoding).

    Uses client.messages.parse() which:
    1. Converts the Pydantic model to JSON Schema automatically
    2. Sends it with output_config.format for constrained decoding
    3. Returns response.parsed_output as a validated Pydantic instance

    No manual JSON extraction or repair needed -- the API guarantees schema-valid output.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key, timeout=120.0)
    response = await client.messages.parse(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        output_format=schema,
    )
    return response.parsed_output


async def complete(
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
    model: str | None = None,
) -> T | None:
    """
    Call LLM API (Claude preferred if ANTHROPIC_API_KEY set, else OpenAI).

    - Claude path uses structured outputs (constrained decoding) for guaranteed valid JSON.
    - OpenAI path uses traditional JSON extraction with retry.
    - Concurrency is capped by an asyncio.Semaphore.
    - Exponential backoff on 429 rate-limit errors (up to 3 retries).

    Returns None if no API key or on failure.
    """
    use_claude = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    use_openai = bool(os.environ.get("OPENAI_API_KEY", "").strip())

    if not use_claude and not use_openai:
        logger.debug("No API key (OPENAI_API_KEY or ANTHROPIC_API_KEY), skipping LLM call")
        return None

    system_prompt = _truncate_context(system_prompt)
    user_prompt = _truncate_context(user_prompt)

    if model is None:
        model = ANTHROPIC_DEFAULT_MODEL if use_claude else OPENAI_DEFAULT_MODEL

    max_retries = 3
    sem = _get_semaphore()

    for attempt in range(max_retries):
        try:
            async with sem:
                if use_claude:
                    result = await _complete_claude(system_prompt, user_prompt, schema, model)
                else:
                    result = await _complete_openai(system_prompt, user_prompt, schema, model)
            if result is not None:
                return result
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # JSON parse failures (only possible on OpenAI path; Claude uses structured outputs)
            logger.warning("LLM parse failure (attempt %d/%d): %s", attempt + 1, max_retries, e)
            if attempt >= max_retries - 1:
                return None
        except Exception as e:
            err_str = str(e)
            # Handle rate-limit (429) with exponential backoff
            if "429" in err_str or "rate" in err_str.lower():
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "LLM rate-limited (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, max_retries, wait, e,
                )
                await asyncio.sleep(wait)
                if attempt >= max_retries - 1:
                    return None
                continue
            # Handle auth errors
            if "401" in err_str or "Unauthorized" in err_str:
                logger.warning(
                    "LLM API 401 Unauthorized: Check your API key in .env (ANTHROPIC_API_KEY). "
                    "Ensure the key is valid and has no extra spaces or quotes."
                )
                return None
            # All other errors
            logger.warning("LLM error (attempt %d/%d): %s", attempt + 1, max_retries, e)
            if attempt >= max_retries - 1:
                return None

    return None
