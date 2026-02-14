"""LLM Client abstraction supporting multiple providers."""

import os
import json
import hashlib
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from core.validation_logger import logger, LogLevel, EventType


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    content: str
    model: str
    usage: Dict[str, int]
    confidence: float = 0.8
    raw_response: Any = None


class LLMCache:
    """Simple in-memory cache for LLM responses."""

    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl = ttl_seconds

    def _get_key(self, prompt: str, context: Dict) -> str:
        """Generate cache key."""
        content = prompt + json.dumps(context, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, prompt: str, context: Dict) -> Optional[LLMResponse]:
        """Get cached response if available."""
        key = self._get_key(prompt, context)
        if key in self.cache:
            response, timestamp = self.cache[key]
            import time

            if time.time() - timestamp < self.ttl:
                return response
            else:
                del self.cache[key]
        return None

    def set(self, prompt: str, context: Dict, response: LLMResponse):
        """Cache a response."""
        import time

        key = self._get_key(prompt, context)
        self.cache[key] = (response, time.time())


class LLMClient:
    """Universal LLM client supporting multiple providers."""

    # Recommended models per task type
    MODEL_RECOMMENDATIONS = {
        "security": {
            "primary": (LLMProvider.ANTHROPIC, "claude-sonnet-4-20250514"),
            "fallback": (LLMProvider.OPENAI, "gpt-4o"),
            "reasoning": "Claude excels at security analysis due to its careful reasoning and lower false positive rate",
        },
        "performance": {
            "primary": (LLMProvider.OPENAI, "gpt-4o"),
            "fallback": (LLMProvider.ANTHROPIC, "claude-sonnet-4-20250514"),
            "reasoning": "GPT-4o is faster and excellent at code optimization patterns",
        },
        "functional": {
            "primary": (LLMProvider.OPENAI, "gpt-4o-mini"),
            "fallback": (LLMProvider.OPENAI, "gpt-4o"),
            "reasoning": "GPT-4o-mini is cost-effective for test analysis with good accuracy",
        },
        "logic": {
            "primary": (LLMProvider.ANTHROPIC, "claude-sonnet-4-20250514"),
            "fallback": (LLMProvider.OPENAI, "gpt-4o"),
            "reasoning": "Claude's reasoning is superior for detecting subtle logical bugs",
        },
        "architecture": {
            "primary": (LLMProvider.ANTHROPIC, "claude-opus-4-6"),
            "fallback": (LLMProvider.OPENAI, "gpt-4o"),
            "reasoning": "Claude Opus excels at high-level architectural thinking and design patterns",
        },
        "technical_debt": {
            "primary": (LLMProvider.OPENAI, "gpt-4o-mini"),
            "fallback": (LLMProvider.OPENAI, "gpt-4o"),
            "reasoning": "Fast and cost-effective for identifying code smells",
        },
        "observability": {
            "primary": (LLMProvider.OPENAI, "gpt-4o-mini"),
            "fallback": (LLMProvider.OPENAI, "gpt-4o"),
            "reasoning": "Good balance of speed and accuracy for observability patterns",
        },
        "resilience": {
            "primary": (LLMProvider.ANTHROPIC, "claude-sonnet-4-20250514"),
            "fallback": (LLMProvider.OPENAI, "gpt-4o"),
            "reasoning": "Claude is better at understanding failure modes and edge cases",
        },
        "semantics": {
            "primary": (LLMProvider.OPENAI, "gpt-4o"),
            "fallback": (LLMProvider.ANTHROPIC, "claude-sonnet-4-20250514"),
            "reasoning": "GPT-4o is excellent at naming and semantic understanding",
        },
        "deployment": {
            "primary": (LLMProvider.OPENAI, "gpt-4o-mini"),
            "fallback": (LLMProvider.OPENAI, "gpt-4o"),
            "reasoning": "Deployment checks are straightforward, mini is sufficient",
        },
    }

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        task_type: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
    ):
        """
        Initialize LLM client.

        Args:
            provider: LLM provider (auto-selected based on task_type if None)
            model: Model name (auto-selected if None)
            task_type: Type of task for model selection
            api_key: API key (reads from env if None)
            cache_enabled: Whether to enable response caching
            cache_ttl: Cache time-to-live in seconds
        """
        self.task_type = task_type

        # Auto-select model based on task type
        if task_type and task_type in self.MODEL_RECOMMENDATIONS:
            rec = self.MODEL_RECOMMENDATIONS[task_type]
            self.provider = provider or rec["primary"][0]
            self.model = model or rec["primary"][1]
            self.fallback = rec["fallback"]
            self.reasoning = rec["reasoning"]
        else:
            self.provider = provider or LLMProvider.OPENAI
            self.model = model or "gpt-4o-mini"
            self.fallback = None
            self.reasoning = "Default model"

        # Take API key from env if not passed
        if api_key is not None:
            self.api_key = api_key
        else:
            if self.provider == LLMProvider.OPENAI:
                self.api_key = os.getenv("OPENAI_API_KEY")
            elif self.provider == LLMProvider.ANTHROPIC:
                self.api_key = os.getenv("ANTHROPIC_API_KEY")
            else:
                self.api_key = None

        self.cache = LLMCache(cache_ttl) if cache_enabled else None

        # Initialize provider client
        self._init_client()

    def _init_client(self):
        """Initialize the specific provider client."""
        if self.provider == LLMProvider.OPENAI:
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")
            try:
                import openai

                self.client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Install openai: pip install openai")

        elif self.provider == LLMProvider.ANTHROPIC:
            self.api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "Anthropic API key required. Set ANTHROPIC_API_KEY env var."
                )
            try:
                import anthropic

                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Install anthropic: pip install anthropic")

        elif self.provider == LLMProvider.LOCAL:
            # For local models (ollama, etc.)
            self.client = None
            self.local_url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434")

    async def analyze(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        """
        Send analysis request to LLM.

        Args:
            prompt: The prompt to send
            context: Additional context
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            response_format: 'json' for JSON mode

        Returns:
            LLMResponse with standardized format
        """
        context = context or {}
        request_time = time.time()

        # Estimate prompt tokens (rough estimate: ~4 chars per token)
        prompt_token_estimate = len(prompt) // 4

        # Log LLM call
        logger.log_event(
            EventType.LLM_CALL,
            LogLevel.INFO,
            "llm_client",
            f"LLM request to {self.provider.value}",
            {
                "provider": self.provider.value,
                "model": self.model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": response_format,
                "prompt_length_chars": len(prompt),
                "prompt_token_estimate": prompt_token_estimate,
                "task_type": self.task_type,
                "cache_checked": self.cache is not None,
                "timestamp_request": datetime.now().isoformat(),
            },
        )

        # Check cache
        cache_hit = False
        if self.cache:
            cached = self.cache.get(prompt, context)
            if cached:
                cache_hit = True
                logger.log_event(
                    EventType.LLM_RESPONSE,
                    LogLevel.INFO,
                    "llm_client",
                    "LLM response from cache",
                    {
                        "provider": self.provider.value,
                        "model": cached.model,
                        "cache_hit": True,
                        "confidence": cached.confidence,
                    },
                )
                return cached

        try:
            if self.provider == LLMProvider.OPENAI:
                response = await self._call_openai(
                    prompt, temperature, max_tokens, response_format
                )
            elif self.provider == LLMProvider.ANTHROPIC:
                response = await self._call_anthropic(prompt, temperature, max_tokens)
            elif self.provider == LLMProvider.LOCAL:
                response = await self._call_local(prompt, temperature, max_tokens)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            # Calculate latency
            latency_ms = int((time.time() - request_time) * 1000)

            # Log response
            logger.log_event(
                EventType.LLM_RESPONSE,
                LogLevel.INFO,
                "llm_client",
                f"LLM response received from {self.provider.value}",
                {
                    "provider": self.provider.value,
                    "model": response.model,
                    "content_length_chars": len(response.content),
                    "confidence": response.confidence,
                    "usage": response.usage,
                    "latency_ms": latency_ms,
                    "cache_hit": False,
                    "timestamp_response": datetime.now().isoformat(),
                },
            )

            # Cache response
            if self.cache:
                self.cache.set(prompt, context, response)

            return response

        except Exception as e:
            # Log error
            logger.log_error(
                "llm_client", f"LLM call failed to {self.provider.value}", e
            )

            # Try fallback if available
            if self.fallback:
                print(f"Primary LLM failed ({e}), trying fallback...")
                logger.log_event(
                    EventType.LLM_CALL,
                    LogLevel.WARNING,
                    "llm_client",
                    f"Attempting fallback to {self.fallback[0].value}",
                    {
                        "fallback_provider": self.fallback[0].value,
                        "fallback_model": self.fallback[1],
                        "original_error": str(e),
                    },
                )
                self.provider, self.model = self.fallback
                # Clear api_key so _init_client() reads the correct env var for the new provider
                self.api_key = None
                self._init_client()
                return await self.analyze(
                    prompt, context, temperature, max_tokens, response_format
                )
            raise

    async def _call_openai(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> LLMResponse:
        """Call OpenAI API."""
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content

        # Try to extract confidence from content if JSON
        confidence = 0.8
        if response_format == "json":
            try:
                parsed = json.loads(content)
                confidence = parsed.get("confidence", 0.8)
            except:
                pass

        return LLMResponse(
            content=content,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            confidence=confidence,
            raw_response=response,
        )

    async def _call_anthropic(
        self, prompt: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        """Call Anthropic API."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text

        # Try to extract confidence
        confidence = 0.8
        try:
            parsed = json.loads(content)
            confidence = parsed.get("confidence", 0.8)
        except:
            pass

        return LLMResponse(
            content=content,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens
                + response.usage.output_tokens,
            },
            confidence=confidence,
            raw_response=response,
        )

    async def _call_local(
        self, prompt: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        """Call local LLM (ollama, etc.)."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.local_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                },
            ) as resp:
                data = await resp.json()

                return LLMResponse(
                    content=data.get("response", ""),
                    model=self.model,
                    usage={
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    },
                    confidence=0.7,  # Local models typically less reliable
                    raw_response=data,
                )

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the selected model."""
        return {
            "provider": self.provider.value,
            "model": self.model,
            "task_type": self.task_type,
            "reasoning": self.reasoning,
            "fallback": self.fallback,
        }


class RateLimiter:
    """Rate limiter for LLM API calls."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    async def acquire(self):
        """Acquire permission to make a request."""
        import time

        now = time.time()
        # Remove requests older than 1 minute
        self.requests = [r for r in self.requests if now - r < 60]

        if len(self.requests) >= self.requests_per_minute:
            # Wait until we can make another request
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self.requests.append(time.time())
