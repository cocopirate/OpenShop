"""Base interface for SMS provider adapters."""

import abc
from dataclasses import dataclass


@dataclass
class SendResult:
    success: bool
    provider_message_id: str = ""
    error_message: str = ""


class BaseSmsProvider(abc.ABC):
    """Abstract SMS provider.  Concrete adapters must implement *send*."""

    @abc.abstractmethod
    async def send(self, phone: str, template_id: str, params: dict) -> SendResult:
        """Send an SMS and return a SendResult."""
