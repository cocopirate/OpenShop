"""
Registry of public (no-auth) routes, populated by fetching OpenAPI specs from
upstream services at gateway startup.

Each upstream service marks its public endpoints with ``tags=["public"]``.
The gateway fetches the OpenAPI JSON at startup, parses those tags, and caches
the resulting set of (method, path) pairs.  Requests whose (method, path) is in
this set bypass JWT verification.
"""

import re
from typing import Iterable

import httpx
import structlog

log = structlog.get_logger(__name__)

# Tag value that upstream services add to public (no-auth) routes
PUBLIC_TAG = "public"

# HTTP methods that carry OpenAPI operation objects
_OPERATION_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


class PublicRoutesRegistry:
    """
    Registry of (method, path) pairs that do not require token authentication.

    Exact paths are kept in a set for O(1) lookup.  Paths containing OpenAPI
    path-parameters (e.g. ``/api/users/{user_id}``) are converted to compiled
    regular expressions for pattern matching.
    """

    def __init__(self) -> None:
        self._exact: set[tuple[str, str]] = set()
        self._patterns: list[tuple[str, re.Pattern[str]]] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register(self, method: str, path: str) -> None:
        method = method.upper()
        if "{" in path:
            regex = re.sub(r"\{[^}]+\}", "[^/]+", path)
            self._patterns.append((method, re.compile(f"^{regex}$")))
        else:
            self._exact.add((method, path))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_spec(self, spec: dict) -> None:
        """Parse an OpenAPI spec dict and register every route tagged ``public``."""
        for path, operations in spec.get("paths", {}).items():
            for method, operation in operations.items():
                if not isinstance(operation, dict):
                    continue
                if method.upper() not in _OPERATION_METHODS:
                    continue
                if PUBLIC_TAG in operation.get("tags", []):
                    self._register(method, path)

    def is_public(self, method: str, path: str) -> bool:
        """Return ``True`` if the request does not require token authentication."""
        method = method.upper()
        if (method, path) in self._exact:
            return True
        for m, pattern in self._patterns:
            if m == method and pattern.match(path):
                return True
        return False

    async def refresh(self, service_urls: Iterable[str]) -> None:
        """
        Fetch the OpenAPI spec from each upstream service URL and rebuild the
        registry.  Unreachable or non-JSON responses are logged as warnings and
        skipped; the gateway continues with whatever specs were successfully
        loaded.

        :param service_urls: Iterable of base URLs (e.g. ``http://auth:8000``).
                             Duplicate URLs are fetched only once.
        """
        self._exact.clear()
        self._patterns.clear()

        seen: set[str] = set()
        async with httpx.AsyncClient(timeout=5.0) as client:
            for url in service_urls:
                if url in seen:
                    continue
                seen.add(url)
                spec_url = f"{url}/openapi.json"
                try:
                    resp = await client.get(spec_url)
                    resp.raise_for_status()
                    self.load_spec(resp.json())
                    log.info(
                        "public_routes.spec_loaded",
                        service=url,
                        exact_count=len(self._exact),
                        pattern_count=len(self._patterns),
                    )
                except Exception as exc:
                    log.warning(
                        "public_routes.fetch_failed",
                        service=url,
                        error=str(exc),
                    )


# Module-level singleton used across the gateway
public_routes_registry = PublicRoutesRegistry()
