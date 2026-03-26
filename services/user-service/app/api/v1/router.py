from fastapi import APIRouter

from app.api.v1 import addresses, consumers

router = APIRouter()
router.include_router(consumers.router, prefix="/consumers", tags=["consumers"])
router.include_router(addresses.router, prefix="/consumers", tags=["addresses"])
