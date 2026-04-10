"""FastAPI entry point for ai-service."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, Request
from fastapi import status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.core.response import (
    INTERNAL_ERROR,
    VALIDATION_ERROR,
    err,
    set_request_id,
)
from app.database import engine
from app.middleware.auth import ServiceAuthMiddleware
from app.routers.complete import router as complete_router
from app.routers.logs import router as logs_router
from app.routers.templates import router as templates_router

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Start Redis connection pool
    application.state.redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=False,
    )
    log.info("ai_service.started", version="1.0.0")
    yield
    await application.state.redis.aclose()
    await engine.dispose()
    log.info("ai_service.stopped")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    description="AI Service — 平台级 AI 能力统一出口",
    lifespan=lifespan,
)

app.add_middleware(ServiceAuthMiddleware)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=err(VALIDATION_ERROR, str(exc.errors())),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=err(INTERNAL_ERROR, "Internal server error"),
    )


app.include_router(complete_router, prefix="/api/v1/ai/complete", tags=["complete"])
app.include_router(templates_router, prefix="/api/v1/ai/templates", tags=["templates"])
app.include_router(logs_router, prefix="/api/v1/ai/logs", tags=["logs"])


@app.get("/health", tags=["health"], summary="Health check")
async def health_check(request: Request):
    db_status = "ok"
    redis_status = "ok"
    openai_status = "ok"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("health.db_error", error=str(exc))
        db_status = "error"

    try:
        redis: aioredis.Redis = request.app.state.redis
        await redis.ping()
    except Exception as exc:
        log.warning("health.redis_error", error=str(exc))
        redis_status = "error"

    overall = "ok" if (db_status == "ok" and redis_status == "ok") else "degraded"
    status_code = 200 if overall == "ok" else http_status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "db": db_status,
            "redis": redis_status,
            "providers": {"openai": openai_status},
        },
    )
