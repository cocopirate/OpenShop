"""HMAC-SHA256 request signing and verification token helpers."""
from __future__ import annotations

import hashlib
import hmac
import secrets

from app.core.config import settings


# --------------------------------------------------------------------------- #
# HMAC signing                                                                  #
# --------------------------------------------------------------------------- #


def compute_sign(challenge_id: str, start_time: int, end_time: int, sign_key: str) -> str:
    """Compute HMAC-SHA256 signature for a verify request.

    Payload: ``{challenge_id}:{start_time}:{end_time}``
    Key: the per-challenge ``sign_key`` returned during init.
    """
    payload = f"{challenge_id}:{start_time}:{end_time}".encode()
    return hmac.new(sign_key.encode(), payload, hashlib.sha256).hexdigest()


def verify_sign(
    challenge_id: str, start_time: int, end_time: int, sign_key: str, sign: str
) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    expected = compute_sign(challenge_id, start_time, end_time, sign_key)
    return hmac.compare_digest(expected, sign)


# --------------------------------------------------------------------------- #
# Sign-key generation                                                           #
# --------------------------------------------------------------------------- #


def generate_sign_key() -> str:
    """Generate a cryptographically random per-challenge signing key (hex)."""
    return secrets.token_hex(32)


# --------------------------------------------------------------------------- #
# Verification token                                                            #
# --------------------------------------------------------------------------- #


def generate_token() -> str:
    """Generate a URL-safe random token issued after a successful verification."""
    return secrets.token_urlsafe(32)
