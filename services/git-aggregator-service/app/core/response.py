"""Unified API response helpers."""
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


SUCCESS = 0

# Error codes
VALIDATION_ERROR = 40011
WEBHOOK_UNAUTHORIZED = 40101
WEBHOOK_INVALID_SIGNATURE = 40102
WEBHOOK_UNKNOWN_PROVIDER = 40103
COMMIT_NOT_FOUND = 40401
INTERNAL_ERROR = 50000


def http_status_to_code(http_status: int) -> int:
    _map: dict[int, int] = {
        400: VALIDATION_ERROR,
        401: WEBHOOK_UNAUTHORIZED,
        403: WEBHOOK_UNAUTHORIZED,
        404: COMMIT_NOT_FOUND,
        422: VALIDATION_ERROR,
        500: INTERNAL_ERROR,
    }
    return _map.get(http_status, INTERNAL_ERROR)


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
