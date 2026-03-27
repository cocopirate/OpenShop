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

# General errors
VALIDATION_ERROR = 40011
INTERNAL_ERROR = 50000

# SMS-related errors (40500–40599)
SMS_SEND_FAILED = 40500
SMS_RATE_LIMIT_EXCEEDED = 40501
SMS_INVALID_CODE = 40502
SMS_TEMPLATE_NOT_FOUND = 40503
SMS_RECORD_NOT_FOUND = 40504

# --------------------------------------------------------------------------- #
# HTTP status → business error code default mapping                            #
# --------------------------------------------------------------------------- #

_HTTP_CODE_MAP: dict[int, int] = {
    400: VALIDATION_ERROR,
    401: VALIDATION_ERROR,
    403: VALIDATION_ERROR,
    404: INTERNAL_ERROR,
    422: VALIDATION_ERROR,
    429: SMS_RATE_LIMIT_EXCEEDED,
    500: INTERNAL_ERROR,
    502: SMS_SEND_FAILED,
    503: INTERNAL_ERROR,
}


def http_status_to_code(http_status: int) -> int:
    return _HTTP_CODE_MAP.get(http_status, INTERNAL_ERROR)


# --------------------------------------------------------------------------- #
# Response builders                                                            #
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
