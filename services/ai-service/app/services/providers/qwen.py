"""Aliyun Dashscope Qwen provider — OpenAI-compatible mode."""
from __future__ import annotations

import structlog
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, RateLimitError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings
from app.services.providers.base import BaseProvider, CompletionResult

log = structlog.get_logger(__name__)

# Dashscope OpenAI-compatible endpoint
_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# Cost estimates per 1M tokens (USD) — Dashscope reference pricing, update as needed.
# https://help.aliyun.com/zh/model-studio/product-overview/billing
_COST_TABLE: dict[str, tuple[float, float]] = {
    # model_prefix: (input_per_1m, output_per_1m)
    "qwen-turbo":    (0.056,  0.170),
    "qwen-plus":     (0.400,  1.200),
    "qwen-max":      (1.600,  6.400),
    "qwen-long":     (0.056,  0.170),
}
_COST_DEFAULT = (0.400, 1.200)  # fallback: qwen-plus pricing


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on network errors and 5xx; skip 4xx."""
    if isinstance(exc, APIConnectionError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500
    return False


class QwenProvider(BaseProvider):
    """Aliyun Dashscope Qwen provider using OpenAI-compatible SDK."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=_DASHSCOPE_BASE_URL,
        )

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
        log.info("qwen.calling", model=model)

        kwargs: dict = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": 60.0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        # Dashscope supports response_format when using compatible mode
        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)

        raw = response.choices[0].message.content or ""
        usage = response.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        log.info("qwen.success", model=model, total_tokens=total_tokens)
        return CompletionResult(
            content=raw,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=response.model,
        )


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str = "") -> float:
    """Estimate USD cost for a Qwen completion call."""
    prefix = next(
        (k for k in _COST_TABLE if model.startswith(k)),
        None,
    )
    input_per_1m, output_per_1m = _COST_TABLE.get(prefix or "", _COST_DEFAULT)
    return (prompt_tokens / 1_000_000) * input_per_1m + (
        completion_tokens / 1_000_000
    ) * output_per_1m
