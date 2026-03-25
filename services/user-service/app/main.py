from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, status as http_status
from sqlalchemy import text

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging
from app.core.redis import close_redis, get_redis, init_redis

configure_logging()
log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    configure_logging()
    await init_redis()
    log.info("user_service.started", version="1.0.0")
    yield
    await close_redis()
    await engine.dispose()
    log.info("user_service.stopped")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(v1_router, prefix="/api", tags=["api"])


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
