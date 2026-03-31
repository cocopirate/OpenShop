from contextlib import asynccontextmanager
import uuid

import structlog
from fastapi import FastAPI, HTTPException, Request, status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import router
from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging
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
    log.info("git_aggregator_service.started", version="1.0.0")
    yield
    await engine.dispose()
    log.info("git_aggregator_service.stopped")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    description="Git commit aggregator – receives webhooks from Codeup/GitHub/GitLab and provides unified query APIs.",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# Request-ID middleware
# ─────────────────────────────────────────────────────────────────────────────


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Exception handlers – unified response format
# ─────────────────────────────────────────────────────────────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = http_status_to_code(exc.status_code)
    if isinstance(exc.detail, dict):
        # Already a structured error dict from our helpers
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content=err(code, detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=err(VALIDATION_ERROR, str(exc.errors())),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(router, prefix="/api")


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["health"], summary="Health check")
async def health_check():
    db_ok = False
    errors: dict = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        errors["database"] = str(exc)

    overall = "ok" if db_ok else "degraded"
    return {
        "status": overall,
        "service": settings.SERVICE_NAME,
        "checks": {"database": "ok" if db_ok else "error"},
        **({"errors": errors} if errors else {}),
    }


@app.get("/health/ready", tags=["health"], summary="K8s Readiness Probe")
async def readiness_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database not ready: {exc}",
        )
    return {"status": "ready", "service": settings.SERVICE_NAME}
