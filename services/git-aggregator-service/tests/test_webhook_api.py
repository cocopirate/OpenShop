"""Integration-style tests for the webhook API endpoint (no real DB)."""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

GITHUB_PAYLOAD = {
    "ref": "refs/heads/main",
    "repository": {"name": "order-service", "html_url": "https://github.com/test/order-service"},
    "commits": [
        {
            "id": "abc123def456abc1",
            "message": "fix: order bug",
            "timestamp": "2026-03-31T10:00:00Z",
            "author": {"name": "张三", "email": "zhangsan@test.com"},
            "added": [],
            "modified": ["order.py"],
            "removed": [],
        }
    ],
}


def _make_github_sig(body: bytes, secret: str = "test-secret") -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _mock_db():
    """Return a mock AsyncSession that does nothing."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=1)))
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=None)
    return db


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """TestClient with mocked DB and settings."""
    mock_db = _mock_db()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.core.security.settings") as mock_settings, \
         patch("app.api.webhook.commit_service.save_push_event", new_callable=AsyncMock) as mock_save:
        mock_settings.CODEUP_TOKEN = "codeup-secret"
        mock_settings.GITHUB_WEBHOOK_SECRET = "test-secret"
        mock_settings.GITLAB_TOKEN = "gitlab-secret"
        mock_settings.IP_WHITELIST = ""
        mock_settings.MAX_TIMESTAMP_DELAY = 300
        mock_save.return_value = 1

        yield TestClient(app)

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_webhook_github_valid(client):
    body = json.dumps(GITHUB_PAYLOAD).encode()
    sig = _make_github_sig(body)
    response = client.post(
        "/api/webhook/git",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0


def test_webhook_github_invalid_signature(client):
    body = json.dumps(GITHUB_PAYLOAD).encode()
    response = client.post(
        "/api/webhook/git",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=badsig"},
    )
    assert response.status_code == 401


def test_webhook_codeup_valid(client):
    body = json.dumps(GITHUB_PAYLOAD).encode()
    response = client.post(
        "/api/webhook/git",
        content=body,
        headers={"Content-Type": "application/json", "X-Codeup-Token": "codeup-secret"},
    )
    assert response.status_code == 200


def test_webhook_codeup_invalid_token(client):
    body = json.dumps(GITHUB_PAYLOAD).encode()
    response = client.post(
        "/api/webhook/git",
        content=body,
        headers={"Content-Type": "application/json", "X-Codeup-Token": "wrong"},
    )
    assert response.status_code == 401


def test_webhook_gitlab_valid(client):
    body = json.dumps(GITHUB_PAYLOAD).encode()
    response = client.post(
        "/api/webhook/git",
        content=body,
        headers={"Content-Type": "application/json", "X-Gitlab-Token": "gitlab-secret"},
    )
    assert response.status_code == 200


def test_webhook_unknown_provider(client):
    body = json.dumps(GITHUB_PAYLOAD).encode()
    response = client.post(
        "/api/webhook/git",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_health_endpoint():
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_engine.dispose = AsyncMock()

    with patch("app.main.engine", mock_engine), patch("app.core.database.engine", mock_engine):
        with TestClient(app) as c:
            response = c.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service" in data
