"""Base interface for SMS provider adapters."""

import abc
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SendResult:
    success: bool
    provider_message_id: str = ""
    error_message: str = ""
    error_code: str = ""
    # Populated when the provider returns the verification code in the send response.
    # Callers (e.g. send_verification_code) can then cache it in Redis.
    verification_code: str = ""


@dataclass
class StatusResult:
    provider_message_id: str
    status: str  # e.g. "DELIVERED", "FAILED", "PENDING"
    error_message: str = ""


class BaseSmsProvider(abc.ABC):
    """Abstract SMS provider. Concrete adapters must implement send and query_status."""

    @abc.abstractmethod
    async def send(self, phone: str, template_id: str, params: dict) -> SendResult:
        """Send an SMS and return a SendResult."""

    @abc.abstractmethod
    async def query_status(self, provider_message_id: str) -> StatusResult:
        """Query the delivery status of a sent message."""
