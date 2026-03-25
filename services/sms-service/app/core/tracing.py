"""OpenTelemetry tracing configuration for sms-service."""
from __future__ import annotations

from app.core.config import settings


def configure_tracing(app: "FastAPI") -> None:  # type: ignore[name-defined]  # noqa: F821
    """Configure OpenTelemetry tracing if OTEL_ENDPOINT is set."""
    if not settings.OTEL_ENDPOINT:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": settings.SERVICE_NAME,
            "deployment.environment": settings.ENV,
        })
        provider = TracerProvider(resource=resource)

        headers = {}
        if settings.OTEL_TOKEN:
            headers["Authorization"] = f"Bearer {settings.OTEL_TOKEN}"

        exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_ENDPOINT,
            headers=headers,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()
        RedisInstrumentor().instrument()
    except ImportError:
        # OpenTelemetry packages not installed; skip tracing
        pass
