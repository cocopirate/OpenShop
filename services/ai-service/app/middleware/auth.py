"""Service-to-service authentication middleware."""
from __future__ import annotations

import structlog
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

log = structlog.get_logger(__name__)

# Paths that bypass authentication
_PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        service_key = request.headers.get("X-Service-Key")
        if not service_key:
            return JSONResponse(status_code=401, content={"detail": "Missing X-Service-Key header"})

        key_map = settings.get_service_keys()
        if service_key not in key_map:
            log.warning("auth.invalid_key", path=request.url.path)
            return JSONResponse(status_code=401, content={"detail": "Invalid service key"})

        # Attach the resolved service name to request state for use in handlers
        request.state.caller_service = key_map[service_key]
        return await call_next(request)
