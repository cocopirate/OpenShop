"""FastAPI application entry-point for captcha-service."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request, status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.captcha import router as captcha_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.redis import close_redis, get_redis, init_redis
from app.core.response import (
    VALIDATION_ERROR,
    err,
    http_status_to_code,
    set_request_id,
)

configure_logging()
log = structlog.get_logger(__name__)


# --------------------------------------------------------------------------- #
# Lifespan                                                                      #
# --------------------------------------------------------------------------- #


@asynccontextmanager
async def lifespan(application: FastAPI):
    configure_logging()
    await init_redis()
    log.info("captcha_service.started", version="1.0.0")
    yield
    await close_redis()
    log.info("captcha_service.stopped")


# --------------------------------------------------------------------------- #
# App                                                                           #
# --------------------------------------------------------------------------- #

app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    description="统一验证码与行为风控服务",
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# Middleware                                                                    #
# --------------------------------------------------------------------------- #


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# --------------------------------------------------------------------------- #
# Exception handlers                                                            #
# --------------------------------------------------------------------------- #


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = http_status_to_code(exc.status_code)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content=err(code, detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=err(VALIDATION_ERROR, str(exc.errors())),
    )


# --------------------------------------------------------------------------- #
# Routes                                                                        #
# --------------------------------------------------------------------------- #

app.include_router(captcha_router)


@app.get("/health", tags=["health"], summary="Health check")
async def health_check():
    redis_ok = False
    errors: dict = {}
    try:
        redis = get_redis()
        await redis.ping()
        redis_ok = True
    except Exception as exc:
        errors["redis"] = str(exc)

    overall = "ok" if redis_ok else "degraded"
    return {
        "status": overall,
        "service": settings.SERVICE_NAME,
        "checks": {"redis": "ok" if redis_ok else "error"},
        **({"errors": errors} if errors else {}),
    }
