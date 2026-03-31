"""GET /commits and GET /commits/{sha} – commit query API."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import COMMIT_NOT_FOUND, err, ok
from app.models.repository import Repository
from app.services import commit_service

router = APIRouter()


@router.get("", summary="List commits with optional filters")
async def list_commits(
    repo: str | None = Query(None, description="Repository name"),
    author: str | None = Query(None, description="Author name or email"),
    since: datetime | None = Query(None, description="Start time (ISO 8601)"),
    until: datetime | None = Query(None, description="End time (ISO 8601)"),
    keyword: str | None = Query(None, description="Keyword in commit message"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    total, commits = await commit_service.list_commits(
        db,
        repo=repo,
        author=author,
        since=since,
        until=until,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    # Eagerly resolve repository names (they are not loaded by default)
    repo_ids = {c.repo_id for c in commits if c.repo_id}
    repo_names: dict[int, str] = {}
    if repo_ids:
        from sqlalchemy import select
        rows = await db.execute(select(Repository).where(Repository.id.in_(repo_ids)))
        for r in rows.scalars():
            repo_names[r.id] = r.name

    items = [
        {
            "commit": c.commit_sha,
            "repo": repo_names.get(c.repo_id) if c.repo_id else None,
            "branch": c.branch,
            "author": c.author_name,
            "author_email": c.author_email,
            "message": c.message,
            "committed_at": c.committed_at.isoformat() if c.committed_at else None,
        }
        for c in commits
    ]

    return JSONResponse(
        content=ok(
            {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": items,
            }
        )
    )


@router.get("/{sha}", summary="Get commit detail by SHA")
async def get_commit(sha: str, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    commit = await commit_service.get_commit_by_sha(db, sha)
    if commit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=err(COMMIT_NOT_FOUND, f"Commit {sha} not found"),
        )

    # Resolve repo name
    repo_name: str | None = None
    if commit.repo_id:
        from sqlalchemy import select
        result = await db.execute(select(Repository).where(Repository.id == commit.repo_id))
        repo_obj = result.scalar_one_or_none()
        repo_name = repo_obj.name if repo_obj else None

    files = [
        {
            "path": f.file_path,
            "type": f.change_type,
            "additions": f.additions,
            "deletions": f.deletions,
        }
        for f in (commit.files or [])
    ]

    return JSONResponse(
        content=ok(
            {
                "commit": commit.commit_sha,
                "repo": repo_name,
                "branch": commit.branch,
                "author": commit.author_name,
                "author_email": commit.author_email,
                "message": commit.message,
                "committed_at": commit.committed_at.isoformat() if commit.committed_at else None,
                "files": files,
            }
        )
    )
