"""Unified API response helpers per api-contract.md."""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

from fastapi.responses import JSONResponse

# --------------------------------------------------------------------------- #
# Request-ID context variable                                                  #
# --------------------------------------------------------------------------- #

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    rid = _request_id_var.get()
    if not rid:
        rid = str(uuid.uuid4())
        _request_id_var.set(rid)
    return rid


def set_request_id(rid: str) -> None:
    _request_id_var.set(rid)


# --------------------------------------------------------------------------- #
# Business error codes (api-contract.md §错误码规范)                           #
# --------------------------------------------------------------------------- #

SUCCESS = 0

# Auth / user-related errors (40001–40099)
TOKEN_INVALID = 40007
MISSING_TOKEN = 40009
PERMISSION_DENIED = 40010

# Crypto / security errors (40012–40014)
SIGN_MISSING = 40012
SIGN_INVALID = 40013
DECRYPT_FAILED = 40014

# Internal-service / gateway errors (50000–50099)
INTERNAL_ERROR = 50000
UPSTREAM_UNAVAILABLE = 50001
UPSTREAM_TIMEOUT = 50002
ROUTE_NOT_FOUND = 50003
CRYPTO_CONFIG_ERROR = 50004


# --------------------------------------------------------------------------- #
# HTTP status → business error code default mapping for gateway errors         #
# --------------------------------------------------------------------------- #

_HTTP_CODE_MAP: dict[int, int] = {
    401: TOKEN_INVALID,
    403: PERMISSION_DENIED,
    404: ROUTE_NOT_FOUND,
    503: UPSTREAM_UNAVAILABLE,
    504: UPSTREAM_TIMEOUT,
}


def http_status_to_code(http_status: int) -> int:
    return _HTTP_CODE_MAP.get(http_status, INTERNAL_ERROR)


# --------------------------------------------------------------------------- #
# Response builders                                                             #
# --------------------------------------------------------------------------- #


def ok(data: Any = None, message: str = "success") -> dict:
    """Build a successful unified response body."""
    return {
        "code": SUCCESS,
        "message": message,
        "data": data,
        "request_id": get_request_id(),
    }


def err(code: int, message: str) -> dict:
    """Build an error unified response body."""
    return {
        "code": code,
        "message": message,
        "data": None,
        "request_id": get_request_id(),
    }


def error_response(http_status: int, code: int, message: str) -> JSONResponse:
    """Return a JSONResponse with unified error body."""
    return JSONResponse(
        status_code=http_status,
        content=err(code, message),
    )
