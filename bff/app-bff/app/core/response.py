"""Unified API response helpers for app-bff."""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    rid = _request_id_var.get()
    if not rid:
        rid = str(uuid.uuid4())
        _request_id_var.set(rid)
    return rid


def set_request_id(rid: str) -> None:
    _request_id_var.set(rid)


def ok(data: Any = None, message: str = "success") -> dict:
    return {
        "code": 0,
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
