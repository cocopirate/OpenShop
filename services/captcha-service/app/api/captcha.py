"""Captcha API router – GET /captcha/init  and  POST /captcha/verify."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from app.core.redis import get_redis
from app.core.response import (
    CHALLENGE_ALREADY_USED,
    CHALLENGE_NOT_FOUND,
    CHALLENGE_EXPIRED,
    SIGNATURE_INVALID,
    TRACK_INVALID,
    CAPTCHA_REJECTED,
    CAPTCHA_SECONDARY_REQUIRED,
    INTERNAL_ERROR,
    err,
    ok,
)
from app.models.schema import CaptchaInitRequest, CaptchaVerifyRequest
from app.service import challenge_service, verify_service

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/captcha", tags=["captcha"])

# Map ValueError message strings → (http_status, business_code)
_ERROR_MAP = {
    "challenge_not_found": (status.HTTP_404_NOT_FOUND, CHALLENGE_NOT_FOUND),
    "challenge_expired": (status.HTTP_400_BAD_REQUEST, CHALLENGE_EXPIRED),
    "challenge_already_used": (status.HTTP_400_BAD_REQUEST, CHALLENGE_ALREADY_USED),
    "signature_invalid": (status.HTTP_400_BAD_REQUEST, SIGNATURE_INVALID),
    "track_invalid": (status.HTTP_400_BAD_REQUEST, TRACK_INVALID),
}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real = request.headers.get("X-Real-IP")
    if real:
        return real.strip()
    return request.client.host if request.client else ""


# --------------------------------------------------------------------------- #
# GET /captcha/init                                                             #
# --------------------------------------------------------------------------- #


@router.get("/init", summary="Initialise a CAPTCHA challenge")
async def captcha_init(
    request: Request,
    scene: str = "login",
    client_type: str = "h5",
):
    # Validate enum values via a quick schema parse
    try:
        params = CaptchaInitRequest(scene=scene, client_type=client_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    ip = _client_ip(request)
    ua = request.headers.get("User-Agent", "")

    try:
        redis = get_redis()
    except RuntimeError:
        # Redis unavailable – proceed with fallback (challenge_service handles it)
        redis = None  # type: ignore[assignment]

    try:
        payload = await challenge_service.create_challenge(
            redis,
            scene=params.scene,
            client_type=params.client_type,
            ip=ip,
            ua=ua,
        )
    except Exception as exc:
        log.error("captcha_init.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create challenge.",
        ) from exc

    return ok(data=payload)


# --------------------------------------------------------------------------- #
# POST /captcha/verify                                                          #
# --------------------------------------------------------------------------- #


@router.post("/verify", summary="Verify a slider gesture")
async def captcha_verify(request: Request, body: CaptchaVerifyRequest):
    ip = _client_ip(request)

    try:
        redis = get_redis()
    except RuntimeError:
        # Redis unavailable: fallback – pass with medium risk
        log.warning("captcha_verify.redis_unavailable")
        return ok(
            data={
                "pass": True,
                "score": 0.5,
                "risk_level": "medium",
                "token": None,
                "redis_fallback": True,
            }
        )

    try:
        result = await verify_service.verify(redis, body, client_ip=ip)
    except ValueError as exc:
        error_key = str(exc)
        if error_key in _ERROR_MAP:
            http_st, code = _ERROR_MAP[error_key]
            raise HTTPException(status_code=http_st, detail=err(code, error_key))
        log.error("captcha_verify.unexpected_error", error=error_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=err(INTERNAL_ERROR, "verification_failed"),
        )
    except Exception as exc:
        log.error("captcha_verify.unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=err(INTERNAL_ERROR, "verification_failed"),
        ) from exc

    return ok(data=result)


# --------------------------------------------------------------------------- #
# GET /captcha/token/verify  (internal – for downstream services)              #
# --------------------------------------------------------------------------- #


@router.get("/token/verify", summary="Verify a captcha pass-token (internal use)")
async def token_verify(token: str):
    try:
        redis = get_redis()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable.",
        )

    payload = await challenge_service.verify_token(redis, token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=err(CHALLENGE_NOT_FOUND, "token_not_found_or_expired"),
        )
    return ok(data=payload)
