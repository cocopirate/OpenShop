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

# Captcha errors (42000–42099)
CHALLENGE_NOT_FOUND = 42001
CHALLENGE_EXPIRED = 42002
CHALLENGE_ALREADY_USED = 42003
SIGNATURE_INVALID = 42004
TRACK_INVALID = 42005
CAPTCHA_REJECTED = 42006
CAPTCHA_SECONDARY_REQUIRED = 42007

# Internal errors
INTERNAL_ERROR = 50000
VALIDATION_ERROR = 40011


# --------------------------------------------------------------------------- #
# HTTP status → business error code default mapping                            #
# --------------------------------------------------------------------------- #

_HTTP_CODE_MAP: dict[int, int] = {
    400: VALIDATION_ERROR,
    404: CHALLENGE_NOT_FOUND,
    422: VALIDATION_ERROR,
    429: CAPTCHA_REJECTED,
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
