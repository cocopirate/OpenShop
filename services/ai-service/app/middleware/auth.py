"""Service-to-service authentication middleware."""
from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.response import MISSING_TOKEN, PERMISSION_DENIED, err

log = structlog.get_logger(__name__)

# Paths that bypass authentication entirely (no JWT, no service key)
_PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

# Only paths under this prefix require X-Service-Key (service-to-service calls)
_SERVICE_KEY_PREFIX = "/api/v1/ai/complete"


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # X-Service-Key is only required for model completion endpoints
        if not request.url.path.startswith(_SERVICE_KEY_PREFIX):
            return await call_next(request)

        service_key = request.headers.get("X-Service-Key")
        if not service_key:
            return JSONResponse(
                status_code=401,
                content=err(MISSING_TOKEN, "Missing X-Service-Key header"),
            )

        key_map = settings.get_service_keys()
        if service_key not in key_map:
            log.warning("auth.invalid_key", path=request.url.path)
            return JSONResponse(
                status_code=401,
                content=err(PERMISSION_DENIED, "Invalid service key"),
            )

        # Attach the resolved service name to request state for use in handlers
        request.state.caller_service = key_map[service_key]
        return await call_next(request)
