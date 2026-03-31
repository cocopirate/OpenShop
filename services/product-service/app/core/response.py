"""Unified API response helpers for product-service."""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

from fastapi.responses import JSONResponse

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

# Product-related errors (43001–43099)
SPU_NOT_FOUND = 43001
SKU_NOT_FOUND = 43002
CATEGORY_NOT_FOUND = 43003
ATTRIBUTE_NOT_FOUND = 43004
GROUP_NOT_FOUND = 43005
CATEGORY_HAS_PRODUCTS = 43006
CATEGORY_LEVEL_EXCEEDED = 43007
SPU_NOT_ONLINE = 43008
DUPLICATE_GROUP_PRODUCT = 43009

INTERNAL_ERROR = 50000

_HTTP_CODE_MAP: dict[int, int] = {
    400: VALIDATION_ERROR,
    401: 40007,
    403: 40010,
    404: SPU_NOT_FOUND,
    422: VALIDATION_ERROR,
    500: INTERNAL_ERROR,
}


def http_status_to_code(http_status: int) -> int:
    return _HTTP_CODE_MAP.get(http_status, INTERNAL_ERROR)


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
