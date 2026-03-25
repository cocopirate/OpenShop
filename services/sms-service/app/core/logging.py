"""Structured logging configuration using structlog."""
import logging
import sys
import uuid

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog for JSON output with required fields."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.DEBUG:
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a bound structlog logger with service context."""
    return structlog.get_logger(name).bind(
        service=settings.SERVICE_NAME,
        env=settings.ENV,
    )


def new_trace_id() -> str:
    """Generate a new trace ID."""
    return uuid.uuid4().hex
