"""Webhook security: token verification and HMAC signature validation."""
from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.response import WEBHOOK_INVALID_SIGNATURE, WEBHOOK_UNAUTHORIZED


def detect_provider(headers: dict) -> str:
    """Identify the Git platform from request headers."""
    if "x-codeup-token" in headers:
        return "codeup"
    if "x-gitlab-token" in headers:
        return "gitlab"
    if "x-hub-signature-256" in headers:
        return "github"
    return "unknown"


def verify_codeup_token(token: str) -> None:
    """Validate Codeup static token."""
    if token != settings.CODEUP_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": WEBHOOK_UNAUTHORIZED, "message": "Invalid Codeup token"},
        )


def verify_gitlab_token(token: str) -> None:
    """Validate GitLab static token."""
    if token != settings.GITLAB_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": WEBHOOK_UNAUTHORIZED, "message": "Invalid GitLab token"},
        )


def verify_github_signature(body: bytes, signature_header: str) -> None:
    """Validate GitHub HMAC-SHA256 webhook signature."""
    if not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": WEBHOOK_INVALID_SIGNATURE, "message": "Missing sha256= prefix"},
        )
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": WEBHOOK_INVALID_SIGNATURE, "message": "Invalid GitHub signature"},
        )


def check_ip_whitelist(request: Request) -> None:
    """Optionally restrict source IPs."""
    whitelist_raw = settings.IP_WHITELIST.strip()
    if not whitelist_raw:
        return
    allowed = {ip.strip() for ip in whitelist_raw.split(",") if ip.strip()}
    client_ip = request.client.host if request.client else ""
    if client_ip not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": WEBHOOK_UNAUTHORIZED, "message": f"IP {client_ip} not whitelisted"},
        )


def check_timestamp(ts: int) -> None:
    """Prevent replay attacks by rejecting stale timestamps."""
    now = int(time.time())
    if abs(now - ts) > settings.MAX_TIMESTAMP_DELAY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": WEBHOOK_UNAUTHORIZED, "message": "Request timestamp expired"},
        )
