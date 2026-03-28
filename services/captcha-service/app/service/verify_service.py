"""Full verification pipeline: signature → challenge → features → score → token."""
from __future__ import annotations

import time
from typing import Any

import structlog

from app.core.config import settings
from app.core.security import verify_sign
from app.models.schema import CaptchaVerifyRequest
from app.service import challenge_service, feature_extractor, scorer
from app.utils import track as track_utils

log = structlog.get_logger(__name__)


async def verify(
    redis,
    req: CaptchaVerifyRequest,
    client_ip: str,
) -> dict[str, Any]:
    """Run the full verification pipeline.

    Returns a response dict ready to be wrapped in ``ok()``.
    Raises ``ValueError`` with a descriptive message on hard failures
    (challenge not found, already used, signature mismatch, etc.).
    """
    # ------------------------------------------------------------------ #
    # 1. Load and validate the challenge                                   #
    # ------------------------------------------------------------------ #
    challenge = await challenge_service.fetch_challenge(redis, req.challenge_id)

    if challenge is None:
        raise ValueError("challenge_not_found")

    if challenge.get("used"):
        raise ValueError("challenge_already_used")

    # Replay / expiry guard – belt-and-suspenders on top of Redis TTL
    expire_at = challenge.get("expire", 0)
    if expire_at and int(time.time()) > expire_at:
        raise ValueError("challenge_expired")

    # ------------------------------------------------------------------ #
    # 2. Signature verification (防伪造)                                   #
    # ------------------------------------------------------------------ #
    sign_key: str = challenge.get("sign_key", "")
    if not verify_sign(
        req.challenge_id, req.start_time, req.end_time, sign_key, req.sign
    ):
        raise ValueError("signature_invalid")

    # ------------------------------------------------------------------ #
    # 3. Consume challenge (one-time use, 防重放)                          #
    # ------------------------------------------------------------------ #
    consumed = await challenge_service.consume_challenge(redis, req.challenge_id)
    if not consumed:
        raise ValueError("challenge_already_used")

    # ------------------------------------------------------------------ #
    # 4. Duration sanity check                                             #
    # ------------------------------------------------------------------ #
    duration_ms = req.end_time - req.start_time
    if (
        duration_ms < settings.MIN_GESTURE_DURATION_MS
        or duration_ms > settings.MAX_GESTURE_DURATION_MS
    ):
        log.info(
            "verify.duration_out_of_range",
            duration_ms=duration_ms,
            challenge_id=req.challenge_id,
        )
        return _build_result(
            passed=False,
            score=0.0,
            risk_level="high",
            token=None,
        )

    # ------------------------------------------------------------------ #
    # 5. Track preprocessing & feature extraction                         #
    # ------------------------------------------------------------------ #
    processed = track_utils.preprocess(req.track)
    features = feature_extractor.extract(processed, duration_ms)

    # ------------------------------------------------------------------ #
    # 6. Scoring & risk determination                                      #
    # ------------------------------------------------------------------ #
    score = scorer.compute_score(features)
    passed, risk_level = scorer.determine_risk(
        score,
        pass_threshold=settings.SCORE_PASS_THRESHOLD,
        reject_threshold=settings.SCORE_REJECT_THRESHOLD,
    )

    log.info(
        "verify.result",
        challenge_id=req.challenge_id,
        score=score,
        passed=passed,
        risk_level=risk_level,
        duration_ms=duration_ms,
        ip=client_ip,
    )

    # ------------------------------------------------------------------ #
    # 7. Issue token on pass                                               #
    # ------------------------------------------------------------------ #
    token: str | None = None
    if passed:
        token = await challenge_service.store_token(
            redis,
            challenge_id=req.challenge_id,
            scene=challenge.get("scene", ""),
            ip=client_ip,
            score=score,
        )

    return _build_result(
        passed=passed,
        score=score,
        risk_level=risk_level,
        token=token,
    )


def _build_result(
    *,
    passed: bool,
    score: float,
    risk_level: str,
    token: str | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "pass": passed,
        "score": score,
        "risk_level": risk_level,
    }
    if token is not None:
        result["token"] = token
    return result
