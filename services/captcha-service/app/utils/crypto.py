"""AES-256-GCM encrypt / decrypt helpers for optional track payload encryption.

The key is a 32-byte value stored as a 64-character hex string in
``settings.CAPTCHA_AES_KEY``.  Callers that do not require transport-layer
encryption can skip this module entirely; it is provided for completeness and
future use.
"""
from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _load_key() -> bytes:
    raw = settings.CAPTCHA_AES_KEY
    if len(raw) != 64:
        raise ValueError(
            "CAPTCHA_AES_KEY must be a 64-character hex string (32 bytes)."
        )
    return bytes.fromhex(raw)


def encrypt_track(plaintext: str) -> bytes:
    """Encrypt *plaintext* with AES-256-GCM.

    Returns ``nonce (12 bytes) + ciphertext+tag`` as a single byte string.
    """
    key = _load_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return nonce + ct


def decrypt_track(data: bytes) -> str:
    """Decrypt bytes previously produced by :func:`encrypt_track`."""
    if len(data) < 28:  # 12-byte nonce + 16-byte tag minimum
        raise ValueError("Ciphertext too short.")
    key = _load_key()
    aesgcm = AESGCM(key)
    nonce, ct = data[:12], data[12:]
    return aesgcm.decrypt(nonce, ct, None).decode()
