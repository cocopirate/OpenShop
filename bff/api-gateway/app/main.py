from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, status as http_status

from app.api.v1.router import router
from app.core.config import settings
from app.core.redis import close_redis, get_redis, init_redis

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_redis()
    log.info("api_gateway.started", version="1.0.0")
    yield
    await close_redis()
    log.info("api_gateway.stopped")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health", tags=["health"])
async def health_check():
    redis_ok = False
    try:
        redis = get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if redis_ok else "degraded",
        "service": settings.SERVICE_NAME,
        "checks": {"redis": "ok" if redis_ok else "error"},
    }


@app.get("/health/ready", tags=["health"])
async def readiness_check():
    try:
        redis = get_redis()
        await redis.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"redis not ready: {exc}",
        )
    return {"status": "ready", "service": settings.SERVICE_NAME}
