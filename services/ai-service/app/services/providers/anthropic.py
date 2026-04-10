"""Anthropic provider — skeleton for future implementation."""
from __future__ import annotations

from app.services.providers.base import BaseProvider, CompletionResult


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider (not yet implemented)."""

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: str,
    ) -> CompletionResult:
        raise NotImplementedError("Anthropic provider is not yet implemented")
