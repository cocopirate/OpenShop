import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from sqlalchemy import text

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.logging import configure_logging
from app.core.redis import close_redis, get_redis, init_redis

configure_logging()
log = structlog.get_logger(__name__)

_cleanup_task: asyncio.Task | None = None


async def _periodic_cleanup() -> None:
    """Run record cleanup every 24 hours."""
    from app.services.sms_service import cleanup_old_records
    while True:
        await asyncio.sleep(86400)
        if settings.SMS_RECORDS_RETENTION_DAYS > 0:
            try:
                async with AsyncSessionLocal() as session:
                    count = await cleanup_old_records(session)
                    await session.commit()
                    log.info("sms.cleanup.done", deleted=count)
            except Exception as exc:
                log.error("sms.cleanup.error", error=str(exc))


@asynccontextmanager
async def lifespan(application: FastAPI):
    global _cleanup_task
    configure_logging()
    await init_redis()
    _cleanup_task = asyncio.create_task(_periodic_cleanup())
    log.info("sms_service.started", version="1.0.0", provider=settings.SMS_PROVIDER)
    yield
    if _cleanup_task:
        _cleanup_task.cancel()
    await close_redis()
    await engine.dispose()
    log.info("sms_service.stopped")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

from app.core.tracing import configure_tracing
configure_tracing(app)

app.include_router(v1_router, prefix="/api/v1", tags=["sms"])

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health", tags=["health"], summary="服务健康检查（含 DB / Redis 连通性）")
async def health_check():
    """Check PostgreSQL and Redis connectivity."""
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
    """K8s readiness probe – returns 200 only when DB and Redis are reachable."""
    from fastapi import HTTPException, status as http_status

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

