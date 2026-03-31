"""GET /stats/commits – aggregated commit statistics."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ok
from app.services import commit_service

router = APIRouter()


@router.get("/commits", summary="Commit statistics by author and repository")
async def commit_stats(
    since: datetime | None = Query(None, description="Start time (ISO 8601)"),
    until: datetime | None = Query(None, description="End time (ISO 8601)"),
    repo: str | None = Query(None, description="Filter by repository name"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    stats = await commit_service.get_stats(db, since=since, until=until, repo=repo)
    return JSONResponse(content=ok(stats))
