import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import Scope

from app.core.auth import verify_request
from app.core.config import settings


def _make_request(method: str, path: str, token: str | None = None) -> Request:
    headers = {}
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    scope: Scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": Headers(headers=headers).raw,
    }
    return Request(scope)


def _make_token(uid: str = "u1", ver: int = 1, permissions: list | None = None) -> str:
    payload: dict = {"uid": uid, "ver": ver}
    if permissions is not None:
        payload["permissions"] = permissions
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------------------------------
# Public path: /api/auth/login – no auth required (tested via router, but we
# confirm verify_request itself rejects missing token for non-public paths).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_request_missing_token():
    request = _make_request("GET", "/api/users")
    with pytest.raises(HTTPException) as exc_info:
        await verify_request(request)
    assert exc_info.value.status_code == 401
    assert "Missing bearer token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_request_invalid_token():
    request = _make_request("GET", "/api/users", token="not.a.valid.jwt")
    with pytest.raises(HTTPException) as exc_info:
        await verify_request(request)
    assert exc_info.value.status_code == 401
    assert "Invalid or expired token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_request_disabled_user():
    token = _make_token(uid="u2")
    request = _make_request("GET", "/api/orders", token=token)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=lambda key: "disabled" if "user_status" in key else None)

    with patch("app.core.auth.get_redis", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await verify_request(request)
    assert exc_info.value.status_code == 401
    assert "disabled" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_request_version_mismatch():
    token = _make_token(uid="u3", ver=1)
    request = _make_request("GET", "/api/orders", token=token)

    async def fake_get(key: str):
        if "user_status" in key:
            return "active"
        if "user_perm_ver" in key:
            return "2"  # different from token ver=1
        return None

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=fake_get)

    with patch("app.core.auth.get_redis", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await verify_request(request)
    assert exc_info.value.status_code == 401
    assert "invalidated" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_request_permission_denied():
    token = _make_token(uid="u4", ver=1)
    request = _make_request("GET", "/api/orders", token=token)

    async def fake_get(key: str):
        if "user_status" in key:
            return "active"
        if "user_perm_ver" in key:
            return "1"
        if "user_permissions" in key:
            return json.dumps(["product:list"])  # missing order:list
        return None

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=fake_get)

    with patch("app.core.auth.get_redis", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await verify_request(request)
    assert exc_info.value.status_code == 403
    assert "order:list" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_request_success():
    token = _make_token(uid="u5", ver=1)
    request = _make_request("GET", "/api/orders", token=token)

    async def fake_get(key: str):
        if "user_status" in key:
            return "active"
        if "user_perm_ver" in key:
            return "1"
        if "user_permissions" in key:
            return json.dumps(["order:list", "order:create"])
        return None

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=fake_get)

    with patch("app.core.auth.get_redis", return_value=mock_redis):
        payload = await verify_request(request)

    assert payload["uid"] == "u5"
    assert payload["ver"] == 1


@pytest.mark.asyncio
async def test_verify_request_wildcard_permission():
    """A user with '*' permission should be allowed regardless of path."""
    token = _make_token(uid="u6", ver=1)
    request = _make_request("DELETE", "/api/users/42", token=token)

    async def fake_get(key: str):
        if "user_status" in key:
            return "active"
        if "user_perm_ver" in key:
            return "1"
        if "user_permissions" in key:
            return json.dumps(["*"])
        return None

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=fake_get)

    with patch("app.core.auth.get_redis", return_value=mock_redis):
        payload = await verify_request(request)

    assert payload["uid"] == "u6"
