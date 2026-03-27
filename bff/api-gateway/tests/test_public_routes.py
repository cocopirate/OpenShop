"""Tests for PublicRoutesRegistry."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.core.public_routes import PublicRoutesRegistry, PUBLIC_TAG


# ---------------------------------------------------------------------------
# load_spec – unit tests (no network)
# ---------------------------------------------------------------------------


def _make_spec(*routes: tuple[str, str, list[str]]) -> dict:
    """Build a minimal OpenAPI spec dict.

    Each element of *routes* is (method, path, tags).
    """
    paths: dict = {}
    for method, path, tags in routes:
        paths.setdefault(path, {})[method.lower()] = {"tags": tags, "summary": "test"}
    return {"paths": paths}


def test_load_spec_exact_public_route():
    registry = PublicRoutesRegistry()
    spec = _make_spec(("POST", "/api/auth/consumer/login", ["public", "auth"]))
    registry.load_spec(spec)
    assert registry.is_public("POST", "/api/auth/consumer/login")


def test_load_spec_non_public_route_not_registered():
    registry = PublicRoutesRegistry()
    spec = _make_spec(("GET", "/api/admins", ["admin"]))
    registry.load_spec(spec)
    assert not registry.is_public("GET", "/api/admins")


def test_load_spec_multiple_routes():
    registry = PublicRoutesRegistry()
    spec = _make_spec(
        ("POST", "/api/auth/consumer/login", ["public"]),
        ("POST", "/api/auth/admin/login", ["public"]),
        ("POST", "/api/auth/logout", ["auth"]),
    )
    registry.load_spec(spec)
    assert registry.is_public("POST", "/api/auth/consumer/login")
    assert registry.is_public("POST", "/api/auth/admin/login")
    assert not registry.is_public("POST", "/api/auth/logout")


def test_load_spec_path_with_parameter():
    registry = PublicRoutesRegistry()
    spec = _make_spec(("GET", "/api/products/{product_id}", ["public"]))
    registry.load_spec(spec)
    assert registry.is_public("GET", "/api/products/123")
    assert registry.is_public("GET", "/api/products/abc-def")
    assert not registry.is_public("GET", "/api/products/123/reviews")


def test_load_spec_method_mismatch():
    registry = PublicRoutesRegistry()
    spec = _make_spec(("POST", "/api/auth/consumer/login", ["public"]))
    registry.load_spec(spec)
    # GET against a POST-only public route should not be public
    assert not registry.is_public("GET", "/api/auth/consumer/login")


def test_load_spec_empty_spec():
    registry = PublicRoutesRegistry()
    registry.load_spec({})
    assert not registry.is_public("GET", "/anything")


def test_load_spec_case_insensitive_method():
    """Registry normalises methods to uppercase."""
    registry = PublicRoutesRegistry()
    spec = _make_spec(("post", "/api/auth/login", ["public"]))
    registry.load_spec(spec)
    assert registry.is_public("POST", "/api/auth/login")
    assert registry.is_public("post", "/api/auth/login")


# ---------------------------------------------------------------------------
# refresh – integration-style tests with mocked HTTP
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_loads_public_routes():
    spec = _make_spec(
        ("POST", "/api/auth/consumer/login", ["public"]),
        ("GET", "/api/orders", ["admin"]),
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=spec)

    registry = PublicRoutesRegistry()

    with patch("app.core.public_routes.httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        await registry.refresh(["http://auth:8000"])

    assert registry.is_public("POST", "/api/auth/consumer/login")
    assert not registry.is_public("GET", "/api/orders")


@pytest.mark.asyncio
async def test_refresh_deduplicates_urls():
    """When the same URL appears multiple times, it is fetched only once."""
    spec = _make_spec(("POST", "/api/sms/send-code", ["public"]))

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=spec)

    registry = PublicRoutesRegistry()

    with patch("app.core.public_routes.httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        # Pass the same URL twice
        await registry.refresh(["http://sms:8000", "http://sms:8000"])

    # Should have been called exactly once despite duplicate URL
    mock_client_instance.get.assert_called_once()
    assert registry.is_public("POST", "/api/sms/send-code")


@pytest.mark.asyncio
async def test_refresh_continues_on_service_unavailable():
    """An unreachable service is skipped; the registry still loads what it can."""
    spec = _make_spec(("POST", "/api/auth/consumer/login", ["public"]))

    good_response = MagicMock()
    good_response.raise_for_status = MagicMock()
    good_response.json = MagicMock(return_value=spec)

    registry = PublicRoutesRegistry()

    async def fake_get(url: str):
        if "auth" in url:
            return good_response
        raise httpx.ConnectError("connection refused")

    with patch("app.core.public_routes.httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(side_effect=fake_get)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        # Should not raise even though sms service is unavailable
        await registry.refresh(["http://auth:8000", "http://sms:8000"])

    assert registry.is_public("POST", "/api/auth/consumer/login")


@pytest.mark.asyncio
async def test_refresh_clears_previous_state():
    """Each refresh replaces the previous registry contents."""
    spec_v1 = _make_spec(("POST", "/api/auth/old-login", ["public"]))
    spec_v2 = _make_spec(("POST", "/api/auth/new-login", ["public"]))

    registry = PublicRoutesRegistry()
    registry.load_spec(spec_v1)
    assert registry.is_public("POST", "/api/auth/old-login")

    new_response = MagicMock()
    new_response.raise_for_status = MagicMock()
    new_response.json = MagicMock(return_value=spec_v2)

    with patch("app.core.public_routes.httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=new_response)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        await registry.refresh(["http://auth:8000"])

    # Old route should be gone, new route should be present
    assert not registry.is_public("POST", "/api/auth/old-login")
    assert registry.is_public("POST", "/api/auth/new-login")
