from contextlib import asynccontextmanager
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.response import set_request_id

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    log.info("app_bff.started", version="1.0.0")
    yield
    log.info("app_bff.stopped")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    description="App BFF – aggregates data for mobile/mini-program clients",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


app.include_router(v1_router, prefix="/api/app")


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.get("/health/ready", tags=["health"])
async def readiness_check():
    return {"status": "ready", "service": settings.SERVICE_NAME}
