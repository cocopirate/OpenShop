"""Provider router — selects the appropriate AI provider."""
from __future__ import annotations

import structlog

from app.services.providers.base import BaseProvider
from app.services.providers.openai import OpenAIProvider

log = structlog.get_logger(__name__)

_providers: dict[str, BaseProvider] = {}


def get_provider(name: str) -> BaseProvider:
    """Return a cached provider instance by name."""
    name = name.lower()
    if name not in _providers:
        if name == "openai":
            _providers[name] = OpenAIProvider()
        elif name == "anthropic":
            from app.services.providers.anthropic import AnthropicProvider
            _providers[name] = AnthropicProvider()
        elif name == "qwen":
            from app.services.providers.qwen import QwenProvider
            _providers[name] = QwenProvider()
        else:
            raise ValueError(f"Unknown provider: {name}")
    return _providers[name]
