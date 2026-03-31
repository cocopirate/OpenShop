"""Pydantic schemas for commit query responses."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CommitFileResponse(BaseModel):
    path: str
    type: str
    additions: int
    deletions: int


class CommitResponse(BaseModel):
    commit: str
    repo: str | None
    branch: str | None
    author: str
    author_email: str | None
    message: str | None
    committed_at: datetime | None
    files: list[CommitFileResponse] = []


class CommitListItem(BaseModel):
    commit: str
    repo: str | None
    branch: str | None
    author: str
    author_email: str | None
    message: str | None
    committed_at: datetime | None


class CommitListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CommitListItem]


class AuthorStats(BaseModel):
    author_email: str | None
    author_name: str | None
    count: int


class RepoStats(BaseModel):
    repo: str | None
    count: int


class StatsResponse(BaseModel):
    by_author: list[AuthorStats]
    by_repo: list[RepoStats]
