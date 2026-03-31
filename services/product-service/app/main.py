from contextlib import asynccontextmanager
import uuid

import structlog
from fastapi import FastAPI, HTTPException, Request, status as http_status
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.redis import close_redis, get_redis, init_redis
from app.core.response import err, http_status_to_code, set_request_id

configure_logging()
log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_redis()
    log.info("product_service.started", version="1.0.0")
    yield
    await close_redis()
    log.info("product_service.stopped")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = http_status_to_code(exc.status_code)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=err(code, detail),
    )


app.include_router(v1_router, prefix="/api/v1")


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
