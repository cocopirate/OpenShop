"""Pydantic schemas for the normalised webhook payload."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CommitFilePayload(BaseModel):
    path: str
    type: str  # added / modified / removed


class CommitPayload(BaseModel):
    id: str  # SHA
    message: str
    timestamp: datetime
    author_name: str
    author_email: str
    files: list[CommitFilePayload] = []


class NormalisedPushPayload(BaseModel):
    """Platform-agnostic push event, produced by every provider parser."""

    repo: str
    repo_url: str | None = None
    branch: str
    provider: str
    commits: list[CommitPayload]
