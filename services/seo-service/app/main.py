"""FastAPI entry point for seo-service."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi import status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers import admin, generate, pages

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    log.info("seo_service.started", version="1.0.0")
    yield
    await engine.dispose()
    log.info("seo_service.stopped")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    description="SEO Content Generator Service — 管理SEO页面生命周期，异步批量调用AI生成本地化内容",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


app.include_router(pages.router, prefix="/pages", tags=["pages"])
app.include_router(generate.router, prefix="/generate", tags=["generate"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.get("/health", tags=["health"], summary="Health check")
async def health_check():
    db_status = "ok"
    redis_status = "ok"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("health.db_error", error=str(exc))
        db_status = "error"

    try:
        from arq.connections import RedisSettings, create_pool
        redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await redis.ping()
        await redis.aclose()
    except Exception as exc:
        log.warning("health.redis_error", error=str(exc))
        redis_status = "error"

    overall = "ok" if (db_status == "ok" and redis_status == "ok") else "degraded"
    status_code = 200 if overall == "ok" else http_status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "db": db_status, "redis": redis_status},
    )
