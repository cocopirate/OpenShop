"""Crypto middleware for the API Gateway.

Provides three independently configurable security features for each route:

1. **Request decryption** – AES-256-CBC body encrypted with a session key
   that is itself RSA-OAEP encrypted with the server's public key.
2. **Signature verification** (``X-Sign`` + ``X-Timestamp`` headers), verified
   over the **plaintext** body (after decryption when applicable).
3. **Response encryption** – AES-256-CBC using the same session key that
   was obtained while decrypting the request.

Execution order per request: decrypt → verify signature → forward → encrypt response.

Which paths use which feature is driven by the three settings lists:
``CRYPTO_SIGN_PATHS``, ``CRYPTO_ENCRYPT_REQUEST_PATHS``, and
``CRYPTO_ENCRYPT_RESPONSE_PATHS`` (see :mod:`app.core.config`).
"""
from __future__ import annotations

import json

import structlog
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.crypto import (
    decrypt_request_body,
    encrypt_response_body,
    load_rsa_private_key,
    verify_hmac_sign,
)
from app.core.response import err

log = structlog.get_logger(__name__)


def _path_matches(path: str, prefixes: list[str]) -> bool:
    """Return True if *path* starts with any of the configured *prefixes*."""
    for prefix in prefixes:
        if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


class CryptoMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that handles request decryption, signature verification
    and response encryption according to the gateway configuration.
    """

    # Cached parsed RSA private key (lazy-loaded once).
    _private_key = None
    _private_key_loaded = False

    def _get_private_key(self):
        if not self._private_key_loaded:
            if settings.CRYPTO_RSA_PRIVATE_KEY:
                try:
                    CryptoMiddleware._private_key = load_rsa_private_key(
                        settings.CRYPTO_RSA_PRIVATE_KEY
                    )
                except Exception as exc:
                    log.error("crypto.rsa_key_load_failed", error=str(exc))
            CryptoMiddleware._private_key_loaded = True
        return self._private_key

    # ------------------------------------------------------------------
    # Middleware dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method

        needs_sign = _path_matches(path, settings.CRYPTO_SIGN_PATHS)
        needs_decrypt = _path_matches(path, settings.CRYPTO_ENCRYPT_REQUEST_PATHS)
        needs_encrypt_resp = _path_matches(path, settings.CRYPTO_ENCRYPT_RESPONSE_PATHS)

        # Nothing to do for this path – fast exit.
        if not (needs_sign or needs_decrypt or needs_encrypt_resp):
            return await call_next(request)

        # Read and cache the body once; downstream can still call request.body().
        body = await request.body()
        session_aes_key: bytes | None = None

        # ------------------------------------------------------------------ #
        # Step 1: Request decryption (AES + RSA hybrid)                        #
        # ------------------------------------------------------------------ #
        if needs_decrypt:
            private_key = self._get_private_key()
            if private_key is None:
                log.error("crypto.rsa_key_not_configured")
                return self._error_response(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    50004,
                    "Server crypto configuration error",
                )

            try:
                body, session_aes_key = decrypt_request_body(body, private_key)
            except Exception as exc:
                log.warning("crypto.decrypt_failed", path=path, error=str(exc))
                return self._error_response(
                    status.HTTP_400_BAD_REQUEST,
                    40014,
                    f"Request decryption failed: {exc}",
                )

            # Starlette's Request.body() caches its result in _body after the
            # first read.  BaseHTTPMiddleware already consumed the raw stream
            # before calling dispatch(), so downstream code always reads from
            # this cache.  Replacing _body with the decrypted plaintext is the
            # correct and idiomatic way to swap the body inside
            # BaseHTTPMiddleware (see Starlette docs / community examples).
            request._body = body  # type: ignore[attr-defined]

        # ------------------------------------------------------------------ #
        # Step 2: Signature verification (over plaintext body)                 #
        # ------------------------------------------------------------------ #
        if needs_sign:
            timestamp = request.headers.get("X-Timestamp", "")
            signature = request.headers.get("X-Sign", "")

            if not timestamp or not signature:
                log.warning("crypto.sign_missing_headers", path=path)
                return self._error_response(
                    status.HTTP_400_BAD_REQUEST,
                    40012,
                    "Missing X-Timestamp or X-Sign header",
                )

            ok, reason = verify_hmac_sign(
                body,
                timestamp,
                method,
                path,
                signature,
                settings.CRYPTO_HMAC_SECRET,
            )
            if not ok:
                log.warning("crypto.sign_invalid", path=path, reason=reason)
                return self._error_response(
                    status.HTTP_400_BAD_REQUEST,
                    40013,
                    f"Signature verification failed: {reason}",
                )

        # ------------------------------------------------------------------ #
        # Step 3: Forward to the actual route handler                          #
        # ------------------------------------------------------------------ #
        response = await call_next(request)

        # ------------------------------------------------------------------ #
        # Step 4: Response encryption                                          #
        # ------------------------------------------------------------------ #
        if needs_encrypt_resp:
            aes_key = session_aes_key
            if aes_key is None:
                # No session key available (path is in encrypt-response list
                # but NOT in encrypt-request list) – skip encryption and warn.
                log.warning(
                    "crypto.resp_encrypt_skipped_no_key",
                    path=path,
                    hint="Add path to CRYPTO_ENCRYPT_REQUEST_PATHS_JSON so a session key is established",
                )
                return response

            resp_body = b""
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                resp_body += chunk if isinstance(chunk, bytes) else chunk.encode()

            try:
                encrypted_body = encrypt_response_body(resp_body, aes_key)
            except Exception as exc:
                log.error("crypto.resp_encrypt_failed", path=path, error=str(exc))
                return self._error_response(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    50004,
                    "Response encryption failed",
                )

            excluded_headers = {"content-length", "transfer-encoding"}
            headers = {
                k: v
                for k, v in response.headers.items()
                if k.lower() not in excluded_headers
            }
            headers["content-type"] = "application/json"
            return Response(
                content=encrypted_body,
                status_code=response.status_code,
                headers=headers,
                media_type="application/json",
            )

        return response

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    @staticmethod
    def _error_response(http_status: int, code: int, message: str) -> Response:
        content = json.dumps(err(code, message))
        return Response(
            content=content,
            status_code=http_status,
            headers={"content-type": "application/json"},
            media_type="application/json",
        )
