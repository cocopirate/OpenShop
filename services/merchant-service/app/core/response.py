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

VALIDATION_ERROR = 40011

# Merchant-related errors (42001–42099)
MERCHANT_NOT_FOUND = 42001
MERCHANT_ALREADY_EXISTS = 42002
STORE_NOT_FOUND = 42003
SUB_ACCOUNT_NOT_FOUND = 42004
STAFF_NOT_FOUND = 42005
ROLE_NOT_FOUND = 42006
PERMISSION_NOT_FOUND = 42007
DUPLICATE_USERNAME = 42008
DUPLICATE_PHONE = 42009

# Internal-service errors
INTERNAL_ERROR = 50000

# --------------------------------------------------------------------------- #
# HTTP status → business error code mapping                                    #
# --------------------------------------------------------------------------- #

_HTTP_CODE_MAP: dict[int, int] = {
    400: VALIDATION_ERROR,
    401: 40007,
    403: 40010,
    404: MERCHANT_NOT_FOUND,
    422: VALIDATION_ERROR,
    500: INTERNAL_ERROR,
}


def http_status_to_code(http_status: int) -> int:
    return _HTTP_CODE_MAP.get(http_status, INTERNAL_ERROR)


# --------------------------------------------------------------------------- #
# Response builders                                                             #
# --------------------------------------------------------------------------- #


def ok(data: Any = None, message: str = "success") -> dict:
    return {
        "code": SUCCESS,
        "message": message,
        "data": data,
        "request_id": get_request_id(),
    }


def err(code: int, message: str) -> dict:
    return {
        "code": code,
        "message": message,
        "data": None,
        "request_id": get_request_id(),
    }


def error_response(http_status: int, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content=err(code, message),
    )
