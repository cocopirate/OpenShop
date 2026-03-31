from fastapi import APIRouter

from app.api import commits, stats, webhook

router = APIRouter()

router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
router.include_router(commits.router, prefix="/commits", tags=["commits"])
router.include_router(stats.router, prefix="/stats", tags=["stats"])
