"""POST /webhook/git – unified Git webhook receiver."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import WEBHOOK_UNKNOWN_PROVIDER, err, ok
from app.core.security import (
    check_ip_whitelist,
    detect_provider,
    verify_codeup_token,
    verify_github_signature,
    verify_gitlab_token,
)
from app.providers import codeup, github, gitlab
from app.services import commit_service
from fastapi import Depends

router = APIRouter()
log = structlog.get_logger(__name__)


@router.post("/git", summary="Receive Git platform push webhook")
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # 1. IP whitelist check
    check_ip_whitelist(request)

    # 2. Read raw body (needed for HMAC verification)
    body = await request.body()

    # 3. Detect provider from headers
    headers = {k.lower(): v for k, v in request.headers.items()}
    provider = detect_provider(headers)

    # 4. Security verification per provider
    if provider == "codeup":
        verify_codeup_token(headers.get("x-codeup-token", ""))
    elif provider == "github":
        verify_github_signature(body, headers.get("x-hub-signature-256", ""))
    elif provider == "gitlab":
        verify_gitlab_token(headers.get("x-gitlab-token", ""))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err(WEBHOOK_UNKNOWN_PROVIDER, "Unknown or missing Git platform headers"),
        )

    # 5. Parse JSON payload
    try:
        payload_dict = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err(WEBHOOK_UNKNOWN_PROVIDER, "Invalid JSON payload"),
        )

    # 6. Normalise payload
    try:
        if provider == "codeup":
            normalised = codeup.parse(payload_dict)
        elif provider == "github":
            normalised = github.parse(payload_dict)
        else:  # gitlab
            normalised = gitlab.parse(payload_dict)
    except Exception as exc:
        log.warning("webhook.parse_error", provider=provider, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err(WEBHOOK_UNKNOWN_PROVIDER, f"Payload parse error: {exc}"),
        )

    # 7. Persist
    try:
        saved = await commit_service.save_push_event(db, normalised)
    except Exception as exc:
        log.error("webhook.save_error", provider=provider, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=err(50000, "Failed to persist commits"),
        )

    log.info("webhook.received", provider=provider, repo=normalised.repo, saved=saved)
    return JSONResponse(content=ok({"saved": saved, "repo": normalised.repo}))
