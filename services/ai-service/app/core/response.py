"""Unified API response helpers — matches platform api-contract.md."""
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
# Business error codes                                                         #
# --------------------------------------------------------------------------- #

SUCCESS = 0

VALIDATION_ERROR    = 40011

# AI-service specific (42000–42099)
TEMPLATE_NOT_FOUND  = 42001
TEMPLATE_EXISTS     = 42002
TEMPLATE_VAR_MISSING = 42003
PROVIDER_NOT_FOUND  = 42004
RATE_LIMITED        = 42005
PROVIDER_ERROR      = 42006

# Auth
TOKEN_INVALID       = 40007
MISSING_TOKEN       = 40009
PERMISSION_DENIED   = 40010

# Internal
INTERNAL_ERROR      = 50000


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
    return JSONResponse(status_code=http_status, content=err(code, message))
