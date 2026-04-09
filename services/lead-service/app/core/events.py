"""RabbitMQ event publishing for lead-service."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import aio_pika
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

EXCHANGE_NAME = "openshop"


async def publish_event(routing_key: str, payload: dict[str, Any]) -> None:
    """Publish a JSON event to the openshop topic exchange."""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                EXCHANGE_NAME,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            body = json.dumps(payload, default=_json_default).encode()
            message = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            await exchange.publish(message, routing_key=routing_key)
            log.info("event.published", routing_key=routing_key)
    except Exception as exc:
        log.error("event.publish_failed", routing_key=routing_key, error=str(exc))


async def publish_lead_submitted(
    lead_id: UUID,
    phone: str,
    product_ids: list[str],
    created_at: datetime,
) -> None:
    payload = {
        "event": "lead.submitted",
        "lead_id": str(lead_id),
        "phone": phone,
        "product_ids": product_ids,
        "created_at": created_at.isoformat(),
    }
    await publish_event("lead.submitted", payload)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (UUID, datetime)):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
