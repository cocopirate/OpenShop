"""Challenge lifecycle management backed by Redis.

Redis key schema
----------------
captcha:challenge:{challenge_id}   – JSON blob, TTL = CHALLENGE_TTL seconds
captcha:token:{token}              – JSON blob, TTL = TOKEN_TTL seconds

Fallback policy (Redis unavailable)
------------------------------------
If Redis is unreachable the service degrades gracefully:
  * init:   returns a synthetic challenge (no storage – cannot verify later)
  * verify: marks the result as ``redis_fallback=True`` and passes through
"""
from __future__ import annotations

import json
import random
import secrets
import time
from typing import Any

import structlog

from app.core.config import settings
from app.core.security import generate_sign_key, generate_token

log = structlog.get_logger(__name__)

_CHALLENGE_KEY_PREFIX = "captcha:challenge:"
_TOKEN_KEY_PREFIX = "captcha:token:"

# Slider distance range (px)
_SLIDER_DISTANCE_MIN = 150
_SLIDER_DISTANCE_MAX = 250


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #


def _challenge_key(challenge_id: str) -> str:
    return f"{_CHALLENGE_KEY_PREFIX}{challenge_id}"


def _token_key(token: str) -> str:
    return f"{_TOKEN_KEY_PREFIX}{token}"


# --------------------------------------------------------------------------- #
# Challenge CRUD                                                                #
# --------------------------------------------------------------------------- #


async def create_challenge(
    redis,
    scene: str,
    client_type: str,
    ip: str,
    ua: str,
) -> dict[str, Any]:
    """Persist a new challenge in Redis and return the init response payload."""
    challenge_id = secrets.token_hex(16)
    sign_key = generate_sign_key()
    distance = random.randint(_SLIDER_DISTANCE_MIN, _SLIDER_DISTANCE_MAX)
    track_seed = secrets.token_hex(8)
    expire_at = int(time.time()) + settings.CHALLENGE_TTL

    data: dict[str, Any] = {
        "ip": ip,
        "ua": ua,
        "scene": scene,
        "client_type": client_type,
        "sign_key": sign_key,
        "expire": expire_at,
        "used": False,
    }

    try:
        await redis.set(
            _challenge_key(challenge_id),
            json.dumps(data),
            ex=settings.CHALLENGE_TTL,
        )
    except Exception as exc:
        log.warning("challenge_service.redis_unavailable", error=str(exc))
        # Return anyway – mark as fallback so verify knows Redis was down
        data["redis_fallback"] = True

    return {
        "challenge_id": challenge_id,
        "expire_in": settings.CHALLENGE_TTL,
        "captcha": {
            "type": "slider",
            "distance": distance,
            "track_seed": track_seed,
        },
        "sign_key": sign_key,
    }


async def fetch_challenge(redis, challenge_id: str) -> dict[str, Any] | None:
    """Load a challenge from Redis.  Returns *None* if not found / expired."""
    try:
        raw = await redis.get(_challenge_key(challenge_id))
    except Exception as exc:
        log.warning("challenge_service.redis_get_failed", error=str(exc))
        return None
    if raw is None:
        return None
    return json.loads(raw)


async def consume_challenge(redis, challenge_id: str) -> bool:
    """Mark a challenge as used (one-time) and return True on success."""
    key = _challenge_key(challenge_id)
    try:
        raw = await redis.get(key)
        if raw is None:
            return False
        data = json.loads(raw)
        if data.get("used"):
            return False
        data["used"] = True
        # Persist updated state; keep a short residual TTL to prevent re-use
        # during any race window.
        await redis.set(key, json.dumps(data), ex=30)
        return True
    except Exception as exc:
        log.warning("challenge_service.redis_consume_failed", error=str(exc))
        return False


# --------------------------------------------------------------------------- #
# Token storage                                                                 #
# --------------------------------------------------------------------------- #


async def store_token(
    redis,
    challenge_id: str,
    scene: str,
    ip: str,
    score: float,
) -> str:
    """Generate a verification token, store it in Redis, and return it."""
    token = generate_token()
    payload = {
        "challenge_id": challenge_id,
        "scene": scene,
        "ip": ip,
        "score": round(score, 4),
        "issued_at": int(time.time()),
    }
    try:
        await redis.set(
            _token_key(token),
            json.dumps(payload),
            ex=settings.TOKEN_TTL,
        )
    except Exception as exc:
        log.warning("challenge_service.token_store_failed", error=str(exc))
    return token


async def verify_token(redis, token: str) -> dict[str, Any] | None:
    """Look up a previously issued verification token.  Returns *None* if
    not found or expired."""
    try:
        raw = await redis.get(_token_key(token))
    except Exception as exc:
        log.warning("challenge_service.token_lookup_failed", error=str(exc))
        return None
    if raw is None:
        return None
    return json.loads(raw)
