"""OpenAI provider implementation with retry and timeout."""
from __future__ import annotations

import structlog
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, RateLimitError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings
from app.services.providers.base import BaseProvider, CompletionResult

log = structlog.get_logger(__name__)

# Cost estimates per 1M tokens (USD) – gpt-4o-mini pricing as baseline
_COST_PER_1M_INPUT = 0.15
_COST_PER_1M_OUTPUT = 0.60


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on network errors and 5xx; skip 4xx."""
    if isinstance(exc, APIConnectionError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500
    return False


class OpenAIProvider(BaseProvider):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: str,
    ) -> CompletionResult:
        log.info("openai.calling", model=model)

        kwargs: dict = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": 30.0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)

        raw = response.choices[0].message.content or ""
        usage = response.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        log.info("openai.success", model=model, total_tokens=total_tokens)
        return CompletionResult(
            content=raw,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=response.model,
        )


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens / 1_000_000) * _COST_PER_1M_INPUT + (
        completion_tokens / 1_000_000
    ) * _COST_PER_1M_OUTPUT
