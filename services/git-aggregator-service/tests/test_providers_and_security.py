"""Unit tests for provider parsers and security helpers."""
from __future__ import annotations

import hashlib
import hmac
import time
from unittest.mock import MagicMock, patch

import pytest

from app.providers import codeup, github, gitlab
from app.core import security


# ─────────────────────────────────────────────────────────────────────────────
# Provider parsers
# ─────────────────────────────────────────────────────────────────────────────

GITHUB_PAYLOAD = {
    "ref": "refs/heads/main",
    "repository": {"name": "order-service", "html_url": "https://github.com/test/order-service"},
    "commits": [
        {
            "id": "abc123def456",
            "message": "fix: resolve order bug",
            "timestamp": "2026-03-31T10:00:00Z",
            "author": {"name": "张三", "email": "zhangsan@test.com"},
            "added": ["new_file.py"],
            "modified": ["order.py"],
            "removed": [],
        }
    ],
}

GITLAB_PAYLOAD = {
    "ref": "refs/heads/feature/x",
    "project": {"name": "user-service", "http_url": "https://gitlab.com/test/user-service"},
    "commits": [
        {
            "id": "deadbeef1234",
            "message": "feat: add user endpoint",
            "timestamp": "2026-03-31T12:00:00+00:00",
            "author": {"name": "李四", "email": "lisi@test.com"},
            "added": [],
            "modified": ["user.py"],
            "removed": ["old.py"],
        }
    ],
}

CODEUP_PAYLOAD = {
    "ref": "refs/heads/release",
    "repository": {
        "name": "payment-service",
        "git_http_url": "https://codeup.aliyun.com/test/payment-service",
    },
    "commits": [
        {
            "id": "cafebabe5678",
            "message": "refactor: payment module",
            "timestamp": "2026-03-31T08:00:00+08:00",
            "author": {"name": "王五", "email": "wangwu@test.com"},
            "added": [],
            "modified": ["payment.py"],
            "removed": [],
        }
    ],
}


def test_github_parser():
    result = github.parse(GITHUB_PAYLOAD)
    assert result.provider == "github"
    assert result.repo == "order-service"
    assert result.branch == "main"
    assert len(result.commits) == 1
    c = result.commits[0]
    assert c.id == "abc123def456"
    assert c.author_name == "张三"
    assert c.author_email == "zhangsan@test.com"
    assert c.message == "fix: resolve order bug"
    assert len(c.files) == 2
    file_types = {f.path: f.type for f in c.files}
    assert file_types["new_file.py"] == "added"
    assert file_types["order.py"] == "modified"


def test_gitlab_parser():
    result = gitlab.parse(GITLAB_PAYLOAD)
    assert result.provider == "gitlab"
    assert result.repo == "user-service"
    assert result.branch == "feature/x"
    assert len(result.commits) == 1
    c = result.commits[0]
    assert c.id == "deadbeef1234"
    assert c.author_name == "李四"
    file_types = {f.path: f.type for f in c.files}
    assert file_types["user.py"] == "modified"
    assert file_types["old.py"] == "removed"


def test_codeup_parser():
    result = codeup.parse(CODEUP_PAYLOAD)
    assert result.provider == "codeup"
    assert result.repo == "payment-service"
    assert result.branch == "release"
    assert len(result.commits) == 1
    c = result.commits[0]
    assert c.id == "cafebabe5678"
    assert c.author_name == "王五"


def test_parser_empty_commits():
    payload = {**GITHUB_PAYLOAD, "commits": []}
    result = github.parse(payload)
    assert result.commits == []


# ─────────────────────────────────────────────────────────────────────────────
# detect_provider
# ─────────────────────────────────────────────────────────────────────────────


def test_detect_provider_codeup():
    assert security.detect_provider({"x-codeup-token": "tok"}) == "codeup"


def test_detect_provider_github():
    assert security.detect_provider({"x-hub-signature-256": "sha256=abc"}) == "github"


def test_detect_provider_gitlab():
    assert security.detect_provider({"x-gitlab-token": "tok"}) == "gitlab"


def test_detect_provider_unknown():
    assert security.detect_provider({}) == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# verify_github_signature
# ─────────────────────────────────────────────────────────────────────────────


def test_verify_github_signature_valid():
    body = b'{"ref":"refs/heads/main"}'
    secret = "test-secret"
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    with patch("app.core.security.settings") as mock_settings:
        mock_settings.GITHUB_WEBHOOK_SECRET = secret
        # Should not raise
        security.verify_github_signature(body, sig)


def test_verify_github_signature_invalid():
    from fastapi import HTTPException

    body = b'{"ref":"refs/heads/main"}'
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.GITHUB_WEBHOOK_SECRET = "test-secret"
        with pytest.raises(HTTPException) as exc_info:
            security.verify_github_signature(body, "sha256=wrongsig")
        assert exc_info.value.status_code == 401


def test_verify_github_signature_missing_prefix():
    from fastapi import HTTPException

    with patch("app.core.security.settings") as mock_settings:
        mock_settings.GITHUB_WEBHOOK_SECRET = "test-secret"
        with pytest.raises(HTTPException) as exc_info:
            security.verify_github_signature(b"body", "invalidsig")
        assert exc_info.value.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# check_timestamp
# ─────────────────────────────────────────────────────────────────────────────


def test_check_timestamp_valid():
    ts = int(time.time())
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.MAX_TIMESTAMP_DELAY = 300
        security.check_timestamp(ts)  # Should not raise


def test_check_timestamp_expired():
    from fastapi import HTTPException

    old_ts = int(time.time()) - 400
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.MAX_TIMESTAMP_DELAY = 300
        with pytest.raises(HTTPException) as exc_info:
            security.check_timestamp(old_ts)
        assert exc_info.value.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# verify_codeup_token
# ─────────────────────────────────────────────────────────────────────────────


def test_verify_codeup_token_valid():
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.CODEUP_TOKEN = "secret123"
        security.verify_codeup_token("secret123")  # Should not raise


def test_verify_codeup_token_invalid():
    from fastapi import HTTPException

    with patch("app.core.security.settings") as mock_settings:
        mock_settings.CODEUP_TOKEN = "secret123"
        with pytest.raises(HTTPException) as exc_info:
            security.verify_codeup_token("wrong")
        assert exc_info.value.status_code == 401
