"""Business logic for persisting and querying commits."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commit import Commit, CommitFile
from app.models.repository import Repository
from app.schemas.webhook import NormalisedPushPayload


# ─────────────────────────────────────────────────────────────────────────────
# Write path
# ─────────────────────────────────────────────────────────────────────────────


async def upsert_repository(db: AsyncSession, name: str, url: str | None, provider: str) -> int:
    """Return the repository id, creating the row if it does not exist."""
    stmt = (
        pg_insert(Repository)
        .values(name=name, url=url, provider=provider)
        .on_conflict_do_update(
            index_elements=["name"],
            set_={"url": url, "provider": provider},
        )
        .returning(Repository.id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def save_push_event(db: AsyncSession, payload: NormalisedPushPayload) -> int:
    """Persist all commits from a normalised push event. Returns number saved."""
    repo_id = await upsert_repository(db, payload.repo, payload.repo_url, payload.provider)

    saved = 0
    for c in payload.commits:
        # UPSERT commit – idempotent on commit_sha
        commit_stmt = (
            pg_insert(Commit)
            .values(
                repo_id=repo_id,
                commit_sha=c.id,
                author_name=c.author_name,
                author_email=c.author_email,
                message=c.message,
                branch=payload.branch,
                committed_at=c.timestamp.replace(tzinfo=None) if c.timestamp.tzinfo else c.timestamp,
            )
            .on_conflict_do_nothing(index_elements=["commit_sha"])
            .returning(Commit.id)
        )
        result = await db.execute(commit_stmt)
        commit_id = result.scalar_one_or_none()
        if commit_id is None:
            # Already exists – skip file insertion
            continue

        # Insert files
        for f in c.files:
            db.add(
                CommitFile(
                    commit_id=commit_id,
                    file_path=f.path,
                    change_type=f.type,
                )
            )
        saved += 1

    await db.flush()
    return saved


# ─────────────────────────────────────────────────────────────────────────────
# Read path
# ─────────────────────────────────────────────────────────────────────────────


async def list_commits(
    db: AsyncSession,
    repo: str | None = None,
    author: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[int, list[Commit]]:
    """Return (total, page_items) for the commit list query."""
    stmt = select(Commit).join(Repository, Commit.repo_id == Repository.id, isouter=True)

    if repo:
        stmt = stmt.where(Repository.name == repo)
    if author:
        stmt = stmt.where(
            (Commit.author_email == author) | (Commit.author_name == author)
        )
    if since:
        stmt = stmt.where(Commit.committed_at >= since)
    if until:
        stmt = stmt.where(Commit.committed_at <= until)
    if keyword:
        stmt = stmt.where(Commit.message.ilike(f"%{keyword}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(Commit.committed_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = await db.execute(stmt)
    commits = list(rows.scalars().all())
    return total, commits


async def get_commit_by_sha(db: AsyncSession, sha: str) -> Commit | None:
    """Fetch a single commit with its files by SHA."""
    stmt = (
        select(Commit)
        .where(Commit.commit_sha == sha)
    )
    result = await db.execute(stmt)
    commit = result.scalar_one_or_none()
    if commit is None:
        return None
    # Eagerly load files in a second query
    files_stmt = select(CommitFile).where(CommitFile.commit_id == commit.id)
    files_result = await db.execute(files_stmt)
    commit.files = list(files_result.scalars().all())
    return commit


async def get_stats(
    db: AsyncSession,
    since: datetime | None = None,
    until: datetime | None = None,
    repo: str | None = None,
) -> dict:
    """Return commit counts grouped by author and by repository."""
    base = select(Commit).join(Repository, Commit.repo_id == Repository.id, isouter=True)
    if since:
        base = base.where(Commit.committed_at >= since)
    if until:
        base = base.where(Commit.committed_at <= until)
    if repo:
        base = base.where(Repository.name == repo)

    # By author
    author_stmt = (
        select(Commit.author_email, Commit.author_name, func.count(Commit.id).label("count"))
        .select_from(base.subquery())
        .group_by(Commit.author_email, Commit.author_name)
        .order_by(func.count(Commit.id).desc())
    )
    author_rows = (await db.execute(author_stmt)).all()

    # By repo
    repo_stmt = (
        select(Repository.name.label("repo"), func.count(Commit.id).label("count"))
        .join(Commit, Commit.repo_id == Repository.id)
        .select_from(base.subquery())
        .group_by(Repository.name)
        .order_by(func.count(Commit.id).desc())
    )
    repo_rows = (await db.execute(repo_stmt)).all()

    return {
        "by_author": [
            {"author_email": r.author_email, "author_name": r.author_name, "count": r.count}
            for r in author_rows
        ],
        "by_repo": [{"repo": r.repo, "count": r.count} for r in repo_rows],
    }
