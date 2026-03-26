"""Cryptographic utilities for the API Gateway.

Provides:
- HMAC-SHA256 request signature verification
- RSA-OAEP + AES-256-CBC hybrid decryption of request bodies
- AES-256-CBC encryption of response bodies
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


# ---------------------------------------------------------------------------
# HMAC-SHA256 signature helpers
# ---------------------------------------------------------------------------

SIGN_MAX_AGE_SECONDS = 300  # allow ±5 minutes skew


def compute_hmac_sign(body: bytes, timestamp: str, method: str, path: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature over ``timestamp + method + path + body``.

    The string to sign is: ``{timestamp}\\n{METHOD}\\n{path}\\n{body_hex}``
    Returns the lowercase hex digest.
    """
    string_to_sign = f"{timestamp}\n{method.upper()}\n{path}\n{body.hex()}"
    return hmac.new(
        secret.encode(),
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_hmac_sign(
    body: bytes,
    timestamp: str,
    method: str,
    path: str,
    signature: str,
    secret: str,
) -> tuple[bool, str]:
    """Verify HMAC-SHA256 signature from the ``X-Timestamp`` / ``X-Sign`` headers.

    Returns ``(ok, reason)`` where *reason* is an empty string on success.
    """
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False, "Invalid X-Timestamp"

    now = int(time.time())
    if abs(now - ts) > SIGN_MAX_AGE_SECONDS:
        return False, "Request timestamp expired"

    expected = compute_hmac_sign(body, timestamp, method, path, secret)
    if not hmac.compare_digest(expected, signature.lower()):
        return False, "Signature mismatch"

    return True, ""


# ---------------------------------------------------------------------------
# RSA-OAEP helpers (server private key decryption)
# ---------------------------------------------------------------------------


def load_rsa_private_key(pem: str):
    """Load an RSA private key from a PEM string."""
    return serialization.load_pem_private_key(pem.encode(), password=None)


def rsa_decrypt(encrypted_bytes: bytes, private_key) -> bytes:
    """Decrypt *encrypted_bytes* with RSA-OAEP (SHA-256 hash)."""
    return private_key.decrypt(
        encrypted_bytes,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


# ---------------------------------------------------------------------------
# AES-256-CBC helpers
# ---------------------------------------------------------------------------

AES_KEY_SIZE = 32  # 256 bits
AES_BLOCK_SIZE = 16  # CBC block / IV size


def _pkcs7_pad(data: bytes) -> bytes:
    pad_len = AES_BLOCK_SIZE - (len(data) % AES_BLOCK_SIZE)
    return data + bytes([pad_len] * pad_len)


def _pkcs7_unpad(data: bytes) -> bytes:
    if not data:
        raise ValueError("Empty data after AES decryption")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > AES_BLOCK_SIZE:
        raise ValueError("Invalid PKCS7 padding")
    return data[:-pad_len]


def aes_encrypt(plaintext: bytes, key: bytes | None = None) -> tuple[bytes, bytes, bytes]:
    """Encrypt *plaintext* with AES-256-CBC.

    Returns ``(ciphertext, key, iv)``.  A random key and IV are generated
    when *key* is ``None``.
    """
    if key is None:
        key = os.urandom(AES_KEY_SIZE)
    iv = os.urandom(AES_BLOCK_SIZE)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(_pkcs7_pad(plaintext)) + encryptor.finalize()
    return ciphertext, key, iv


def aes_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt *ciphertext* with AES-256-CBC and return the plaintext bytes."""
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    return _pkcs7_unpad(padded)


# ---------------------------------------------------------------------------
# High-level request / response processing
# ---------------------------------------------------------------------------

_B64 = base64.b64decode
_B64E = base64.b64encode


def decrypt_request_body(envelope_bytes: bytes, private_key) -> tuple[bytes, bytes]:
    """Decrypt a hybrid-encrypted request envelope.

    The envelope is a JSON object with the following fields:

    .. code-block:: json

        {
            "encrypted_key": "<base64 RSA-OAEP encrypted AES-256 key>",
            "iv": "<base64 AES-CBC IV (16 bytes)>",
            "data": "<base64 AES-CBC encrypted original body>"
        }

    Returns ``(plaintext_bytes, aes_key_bytes)`` so the gateway can reuse
    the session key to encrypt the response.
    """
    try:
        envelope = json.loads(envelope_bytes)
    except Exception as exc:
        raise ValueError(f"Encrypted request must be valid JSON: {exc}") from exc

    for field in ("encrypted_key", "iv", "data"):
        if field not in envelope:
            raise ValueError(f"Missing field in encrypted request envelope: '{field}'")

    try:
        enc_aes_key = _B64(envelope["encrypted_key"])
        iv = _B64(envelope["iv"])
        ciphertext = _B64(envelope["data"])
    except Exception as exc:
        raise ValueError(f"Base64 decode error in encrypted envelope: {exc}") from exc

    aes_key = rsa_decrypt(enc_aes_key, private_key)
    plaintext = aes_decrypt(ciphertext, aes_key, iv)
    return plaintext, aes_key


def encrypt_response_body(response_bytes: bytes, aes_key: bytes) -> bytes:
    """Encrypt *response_bytes* with AES-256-CBC using *aes_key*.

    Returns a JSON envelope:

    .. code-block:: json

        {
            "iv": "<base64>",
            "data": "<base64>"
        }
    """
    ciphertext, _, iv = aes_encrypt(response_bytes, key=aes_key)
    envelope = {
        "iv": _B64E(iv).decode(),
        "data": _B64E(ciphertext).decode(),
    }
    return json.dumps(envelope).encode()
