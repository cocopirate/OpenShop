from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.v1.router import router as v1_router, set_sms_client
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=10) as client:
        set_sms_client(client)
        yield


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(v1_router, prefix="/api/v1", tags=["notification-service"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.SERVICE_NAME}
