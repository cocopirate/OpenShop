from fastapi import FastAPI
from app.api.v1.router import router as v1_router
from app.core.config import settings

app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
)

app.include_router(v1_router, prefix="/api/v1", tags=["product-service"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.SERVICE_NAME}
