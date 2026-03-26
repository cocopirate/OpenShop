from contextlib import asynccontextmanager
import uuid

import structlog
from fastapi import FastAPI, HTTPException, Request, status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.internal import router as internal_router
from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.database import engine
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


@asynccontextmanager
async def lifespan(application: FastAPI):
    configure_logging()
    await init_redis()
    log.info("admin_service.started", version="1.0.0")
    yield
    await close_redis()
    await engine.dispose()
    log.info("admin_service.stopped")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# Request-ID middleware                                                         #
# --------------------------------------------------------------------------- #


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# --------------------------------------------------------------------------- #
# Exception handlers – unified response format                                 #
# --------------------------------------------------------------------------- #


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = http_status_to_code(exc.status_code)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=err(code, detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=err(VALIDATION_ERROR, str(exc.errors())),
    )


app.include_router(v1_router, prefix="/api", tags=["api"])
app.include_router(internal_router, prefix="/internal", tags=["internal"])


@app.get("/health", tags=["health"], summary="Health check")
async def health_check():
    db_ok = False
    redis_ok = False
    errors: dict = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        errors["database"] = str(exc)

    try:
        redis = get_redis()
        await redis.ping()
        redis_ok = True
    except Exception as exc:
        errors["redis"] = str(exc)

    overall = "ok" if (db_ok and redis_ok) else "degraded"
    return {
        "status": overall,
        "service": settings.SERVICE_NAME,
        "checks": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
        **({"errors": errors} if errors else {}),
    }


@app.get("/health/ready", tags=["health"], summary="K8s Readiness Probe")
async def readiness_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database not ready: {exc}",
        )

    try:
        redis = get_redis()
        await redis.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"redis not ready: {exc}",
        )

    return {"status": "ready", "service": settings.SERVICE_NAME}
