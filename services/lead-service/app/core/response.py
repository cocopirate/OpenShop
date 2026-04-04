"""Unified API response helpers."""
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
# Business error codes                                                          #
# --------------------------------------------------------------------------- #

SUCCESS = 0

# Generic errors
VALIDATION_ERROR = 40011
INTERNAL_ERROR = 50000

# Lead-related errors (40100–40199)
LEAD_NOT_FOUND = 40100
LEAD_ALREADY_TERMINAL = 40101
LEAD_INVALID_TRANSITION = 40102
INVALID_PRODUCT_IDS = 40103
DUPLICATE_LEAD = 40104

# --------------------------------------------------------------------------- #
# HTTP status → business error code default mapping                            #
# --------------------------------------------------------------------------- #

_HTTP_CODE_MAP: dict[int, int] = {
    400: VALIDATION_ERROR,
    401: 40007,
    403: 40010,
    404: LEAD_NOT_FOUND,
    409: DUPLICATE_LEAD,
    422: VALIDATION_ERROR,
    500: INTERNAL_ERROR,
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
