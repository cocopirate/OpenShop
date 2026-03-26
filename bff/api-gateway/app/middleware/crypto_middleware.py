"""Crypto middleware for the API Gateway.

Provides three independently configurable security features for each route:

1. **Request decryption** – AES-256-CBC body encrypted with a session key
   that is itself RSA-OAEP encrypted with the server's public key.
2. **Signature verification** (``X-Sign`` + ``X-Timestamp`` headers), verified
   over the **plaintext** body (after decryption when applicable).
3. **Response encryption** – AES-256-CBC using the same session key that
   was obtained while decrypting the request.

Execution order per request: decrypt → verify signature → forward → encrypt response.

Which routes use which feature is driven by route tags:

- ``require-sign``             – enable HMAC-SHA256 signature verification.
- ``require-encrypt-request``  – enable AES+RSA hybrid request decryption.
- ``require-encrypt-response`` – enable AES response encryption (requires
  ``require-encrypt-request`` on the same route so the session key is available).

Example::

    @router.post("/api/v1/orders", tags=["require-sign", "require-encrypt-request",
                                         "require-encrypt-response"])
    async def create_order(request: Request):
        ...
"""
from __future__ import annotations

import json

import structlog
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.routing import Match

from app.core.config import settings
from app.core.crypto import (
    decrypt_request_body,
    encrypt_response_body,
    load_rsa_private_key,
    verify_hmac_sign,
)
from app.core.response import err

log = structlog.get_logger(__name__)

# Route tag constants.
TAG_REQUIRE_SIGN = "require-sign"
TAG_REQUIRE_ENCRYPT_REQUEST = "require-encrypt-request"
TAG_REQUIRE_ENCRYPT_RESPONSE = "require-encrypt-response"


def _get_route_tags(request: Request) -> frozenset[str]:
    """Return the tags of the route that best matches the current request.

    Iterates the application route list in definition order (matching FastAPI's
    own dispatch order) and returns the tags of the first fully-matching route.
    Returns an empty frozenset when no route matches.
    """
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            tags = getattr(route, "tags", None) or []
            return frozenset(tags)
    return frozenset()


class CryptoMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that handles request decryption, signature verification
    and response encryption according to the route tags.
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

        tags = _get_route_tags(request)
        needs_sign = TAG_REQUIRE_SIGN in tags
        needs_decrypt = TAG_REQUIRE_ENCRYPT_REQUEST in tags
        needs_encrypt_resp = TAG_REQUIRE_ENCRYPT_RESPONSE in tags

        # Nothing to do for this route – fast exit.
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
                    hint="Add 'require-encrypt-request' tag to the route so a session key is established",
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
