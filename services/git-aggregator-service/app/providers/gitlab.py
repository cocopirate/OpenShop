"""GitLab webhook payload parser.

GitLab push event (simplified):
{
  "ref": "refs/heads/main",
  "project": {"name": "order-service", "http_url": "https://..."},
  "commits": [
    {
      "id": "abc123",
      "message": "fix: bug",
      "timestamp": "2026-03-31T10:00:00+00:00",
      "author": {"name": "张三", "email": "xxx@test.com"},
      "added": [],
      "modified": ["order.py"],
      "removed": []
    }
  ]
}
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.webhook import CommitFilePayload, CommitPayload, NormalisedPushPayload


def _extract_branch(ref: str) -> str:
    if ref.startswith("refs/heads/"):
        return ref[len("refs/heads/"):]
    return ref


def _parse_files(commit: dict) -> list[CommitFilePayload]:
    files: list[CommitFilePayload] = []
    for path in commit.get("added") or []:
        files.append(CommitFilePayload(path=path, type="added"))
    for path in commit.get("modified") or []:
        files.append(CommitFilePayload(path=path, type="modified"))
    for path in commit.get("removed") or []:
        files.append(CommitFilePayload(path=path, type="removed"))
    return files


def parse(payload: dict) -> NormalisedPushPayload:
    project = payload.get("project") or {}
    # GitLab may put repo info under "project" or "repository"
    repo_info = payload.get("repository") or project
    repo_name = project.get("name") or repo_info.get("name", "unknown")
    repo_url = project.get("http_url") or repo_info.get("url")
    ref = payload.get("ref", "")
    branch = _extract_branch(ref)

    commits: list[CommitPayload] = []
    for c in payload.get("commits") or []:
        author = c.get("author") or {}
        ts_raw = c.get("timestamp") or datetime.now(timezone.utc).isoformat()
        try:
            ts = datetime.fromisoformat(ts_raw)
        except (ValueError, TypeError):
            ts = datetime.now(timezone.utc)
        commits.append(
            CommitPayload(
                id=c.get("id", ""),
                message=c.get("message", ""),
                timestamp=ts,
                author_name=author.get("name", ""),
                author_email=author.get("email", ""),
                files=_parse_files(c),
            )
        )

    return NormalisedPushPayload(
        repo=repo_name,
        repo_url=repo_url,
        branch=branch,
        provider="gitlab",
        commits=commits,
    )
