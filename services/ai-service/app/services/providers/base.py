"""Abstract base class for AI providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CompletionResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str


class BaseProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: str,
    ) -> CompletionResult:
        """Call the AI provider and return a completion result."""
        ...
