"""Tests for app.core.crypto and CryptoMiddleware."""
from __future__ import annotations

import base64
import hashlib
import hmac as std_hmac
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import serialization, hashes
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Scope
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_rsa_key_pair():
    """Generate a fresh 2048-bit RSA key pair for testing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_key = private_key.public_key()
    return private_key, public_key, private_pem


def _rsa_encrypt_bytes(data: bytes, public_key) -> bytes:
    """Encrypt *data* with RSA-OAEP (SHA-256) using *public_key*."""
    return public_key.encrypt(
        data,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


# ---------------------------------------------------------------------------
# app.core.crypto unit tests
# ---------------------------------------------------------------------------


class TestAesCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        from app.core.crypto import aes_encrypt, aes_decrypt

        plaintext = b'{"key": "value", "number": 42}'
        ciphertext, key, iv = aes_encrypt(plaintext)
        assert len(key) == 32
        assert len(iv) == 16
        assert ciphertext != plaintext

        recovered = aes_decrypt(ciphertext, key, iv)
        assert recovered == plaintext

    def test_encrypt_with_provided_key(self):
        from app.core.crypto import aes_encrypt, aes_decrypt

        key = os.urandom(32)
        plaintext = b"hello world"
        ciphertext, used_key, iv = aes_encrypt(plaintext, key=key)
        assert used_key == key
        assert aes_decrypt(ciphertext, key, iv) == plaintext

    def test_padding_multiple_of_block_size(self):
        from app.core.crypto import aes_encrypt, aes_decrypt

        # 16-byte plaintext – padding adds a full block
        plaintext = b"A" * 16
        ciphertext, key, iv = aes_encrypt(plaintext)
        assert aes_decrypt(ciphertext, key, iv) == plaintext

    def test_empty_plaintext(self):
        from app.core.crypto import aes_encrypt, aes_decrypt

        plaintext = b""
        ciphertext, key, iv = aes_encrypt(plaintext)
        assert aes_decrypt(ciphertext, key, iv) == plaintext


class TestRsaCrypto:
    def test_rsa_decrypt(self):
        from app.core.crypto import rsa_decrypt

        priv, pub, _ = _generate_rsa_key_pair()
        message = b"super secret AES key 123456789012"
        encrypted = _rsa_encrypt_bytes(message, pub)
        assert rsa_decrypt(encrypted, priv) == message

    def test_load_rsa_private_key(self):
        from app.core.crypto import load_rsa_private_key

        _, _, pem = _generate_rsa_key_pair()
        key = load_rsa_private_key(pem)
        assert key is not None


class TestHmacSign:
    def test_compute_and_verify_success(self):
        from app.core.crypto import compute_hmac_sign, verify_hmac_sign

        secret = "test-secret"
        body = b'{"order_id": 123}'
        ts = str(int(time.time()))
        method = "POST"
        path = "/api/v1/orders"

        sig = compute_hmac_sign(body, ts, method, path, secret)
        ok, reason = verify_hmac_sign(body, ts, method, path, sig, secret)
        assert ok, reason

    def test_verify_wrong_secret(self):
        from app.core.crypto import compute_hmac_sign, verify_hmac_sign

        body = b"{}"
        ts = str(int(time.time()))
        sig = compute_hmac_sign(body, ts, "POST", "/test", "secret-a")
        ok, _ = verify_hmac_sign(body, ts, "POST", "/test", sig, "secret-b")
        assert not ok

    def test_verify_expired_timestamp(self):
        from app.core.crypto import verify_hmac_sign, compute_hmac_sign, SIGN_MAX_AGE_SECONDS

        body = b"{}"
        old_ts = str(int(time.time()) - SIGN_MAX_AGE_SECONDS - 60)
        sig = compute_hmac_sign(body, old_ts, "GET", "/path", "secret")
        ok, reason = verify_hmac_sign(body, old_ts, "GET", "/path", sig, "secret")
        assert not ok
        assert "expired" in reason.lower()

    def test_verify_invalid_timestamp(self):
        from app.core.crypto import verify_hmac_sign

        ok, reason = verify_hmac_sign(b"", "not-a-number", "GET", "/", "sig", "secret")
        assert not ok
        assert "timestamp" in reason.lower()


class TestHybridEncryption:
    def test_decrypt_request_body(self):
        from app.core.crypto import decrypt_request_body, aes_encrypt

        priv, pub, _ = _generate_rsa_key_pair()
        plaintext = b'{"amount": 100}'

        # Simulate client-side encryption
        ciphertext, aes_key, iv = aes_encrypt(plaintext)
        enc_key = _rsa_encrypt_bytes(aes_key, pub)
        envelope = json.dumps({
            "encrypted_key": base64.b64encode(enc_key).decode(),
            "iv": base64.b64encode(iv).decode(),
            "data": base64.b64encode(ciphertext).decode(),
        }).encode()

        recovered, session_key = decrypt_request_body(envelope, priv)
        assert recovered == plaintext
        assert session_key == aes_key

    def test_decrypt_missing_field(self):
        from app.core.crypto import decrypt_request_body

        priv, _, _ = _generate_rsa_key_pair()
        envelope = json.dumps({"encrypted_key": "abc", "iv": "def"}).encode()
        with pytest.raises(ValueError, match="Missing field"):
            decrypt_request_body(envelope, priv)

    def test_decrypt_invalid_json(self):
        from app.core.crypto import decrypt_request_body

        priv, _, _ = _generate_rsa_key_pair()
        with pytest.raises(ValueError, match="valid JSON"):
            decrypt_request_body(b"not json", priv)

    def test_encrypt_response_body(self):
        from app.core.crypto import encrypt_response_body, aes_decrypt

        key = os.urandom(32)
        plaintext = b'{"code": 0, "data": {}}'
        envelope_bytes = encrypt_response_body(plaintext, key)
        envelope = json.loads(envelope_bytes)
        iv = base64.b64decode(envelope["iv"])
        ciphertext = base64.b64decode(envelope["data"])
        assert aes_decrypt(ciphertext, key, iv) == plaintext


# ---------------------------------------------------------------------------
# CryptoMiddleware integration tests
# ---------------------------------------------------------------------------


def _make_rsa_encrypted_envelope(plaintext: bytes, public_key) -> tuple[bytes, bytes]:
    """Return ``(envelope_bytes, aes_key)`` simulating a client-encrypted body."""
    from app.core.crypto import aes_encrypt

    ciphertext, aes_key, iv = aes_encrypt(plaintext)
    enc_key = _rsa_encrypt_bytes(aes_key, public_key)
    envelope = json.dumps({
        "encrypted_key": base64.b64encode(enc_key).decode(),
        "iv": base64.b64encode(iv).decode(),
        "data": base64.b64encode(ciphertext).decode(),
    }).encode()
    return envelope, aes_key


def _make_sign_headers(body: bytes, method: str, path: str, secret: str) -> dict:
    from app.core.crypto import compute_hmac_sign

    ts = str(int(time.time()))
    sig = compute_hmac_sign(body, ts, method, path, secret)
    return {"X-Timestamp": ts, "X-Sign": sig}


class TestCryptoMiddleware:
    """Tests that exercise CryptoMiddleware via a minimal FastAPI app."""

    def test_passthrough_non_configured_path(self):
        """Routes without any crypto tags pass through untouched."""
        from fastapi import FastAPI
        from app.middleware.crypto_middleware import CryptoMiddleware

        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        app.add_middleware(CryptoMiddleware)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_sign_missing_headers_returns_400(self):
        from fastapi import FastAPI
        from app.middleware.crypto_middleware import CryptoMiddleware

        app = FastAPI()

        @app.post("/api/v1/orders", tags=["require-sign"])
        async def _handler(request: Request):
            return Response(content=b"{}", media_type="application/json")

        app.add_middleware(CryptoMiddleware)

        with patch("app.middleware.crypto_middleware.settings") as mock_cfg:
            mock_cfg.CRYPTO_HMAC_SECRET = "secret"

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v1/orders", content=b"{}")

        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40012

    def test_sign_valid_headers_passes(self):
        from fastapi import FastAPI
        from app.middleware.crypto_middleware import CryptoMiddleware
        from app.core.crypto import compute_hmac_sign

        app = FastAPI()

        @app.post("/api/v1/orders", tags=["require-sign"])
        async def _handler(request: Request):
            return Response(content=b'{"ok":true}', media_type="application/json")

        app.add_middleware(CryptoMiddleware)
        secret = "test-hmac-secret"
        body = b'{"amount": 10}'
        ts = str(int(time.time()))
        sig = compute_hmac_sign(body, ts, "POST", "/api/v1/orders", secret)

        with patch("app.middleware.crypto_middleware.settings") as mock_cfg:
            mock_cfg.CRYPTO_HMAC_SECRET = secret

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/v1/orders",
                content=body,
                headers={"X-Timestamp": ts, "X-Sign": sig},
            )

        assert resp.status_code == 200

    def test_sign_invalid_signature_returns_400(self):
        from fastapi import FastAPI
        from app.middleware.crypto_middleware import CryptoMiddleware

        app = FastAPI()

        @app.post("/api/v1/orders", tags=["require-sign"])
        async def _handler(request: Request):
            return Response(content=b"{}", media_type="application/json")

        app.add_middleware(CryptoMiddleware)

        with patch("app.middleware.crypto_middleware.settings") as mock_cfg:
            mock_cfg.CRYPTO_HMAC_SECRET = "secret"

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/v1/orders",
                content=b"{}",
                headers={"X-Timestamp": str(int(time.time())), "X-Sign": "badhex"},
            )

        assert resp.status_code == 400
        assert resp.json()["code"] == 40013

    def test_decrypt_request_body_success(self):
        from fastapi import FastAPI
        from app.middleware.crypto_middleware import CryptoMiddleware

        priv, pub, pem = _generate_rsa_key_pair()
        plaintext = b'{"product_id": 7}'
        envelope, aes_key = _make_rsa_encrypted_envelope(plaintext, pub)

        received_body: list[bytes] = []

        app = FastAPI()

        @app.post("/api/v1/orders", tags=["require-encrypt-request"])
        async def _handler(request: Request):
            received_body.append(await request.body())
            return Response(content=b'{"ok":true}', media_type="application/json")

        app.add_middleware(CryptoMiddleware)

        with patch("app.middleware.crypto_middleware.settings") as mock_cfg:
            mock_cfg.CRYPTO_RSA_PRIVATE_KEY = pem
            # Reset the class-level key cache between tests
            CryptoMiddleware._private_key = None
            CryptoMiddleware._private_key_loaded = False

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v1/orders", content=envelope)

        assert resp.status_code == 200
        assert received_body[0] == plaintext

    def test_decrypt_bad_envelope_returns_400(self):
        from fastapi import FastAPI
        from app.middleware.crypto_middleware import CryptoMiddleware

        _, _, pem = _generate_rsa_key_pair()

        app = FastAPI()

        @app.post("/api/v1/orders", tags=["require-encrypt-request"])
        async def _handler(request: Request):
            return Response(content=b"{}", media_type="application/json")

        app.add_middleware(CryptoMiddleware)

        with patch("app.middleware.crypto_middleware.settings") as mock_cfg:
            mock_cfg.CRYPTO_RSA_PRIVATE_KEY = pem
            CryptoMiddleware._private_key = None
            CryptoMiddleware._private_key_loaded = False

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v1/orders", content=b"not-an-envelope")

        assert resp.status_code == 400
        assert resp.json()["code"] == 40014

    def test_no_rsa_key_configured_returns_500(self):
        from fastapi import FastAPI
        from app.middleware.crypto_middleware import CryptoMiddleware

        app = FastAPI()

        @app.post("/api/v1/orders", tags=["require-encrypt-request"])
        async def _handler(request: Request):
            return Response(content=b"{}", media_type="application/json")

        app.add_middleware(CryptoMiddleware)

        with patch("app.middleware.crypto_middleware.settings") as mock_cfg:
            mock_cfg.CRYPTO_RSA_PRIVATE_KEY = ""
            CryptoMiddleware._private_key = None
            CryptoMiddleware._private_key_loaded = False

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v1/orders", content=b"{}")

        assert resp.status_code == 500
        assert resp.json()["code"] == 50004

    def test_response_encryption(self):
        from fastapi import FastAPI
        from app.middleware.crypto_middleware import CryptoMiddleware
        from app.core.crypto import aes_decrypt

        priv, pub, pem = _generate_rsa_key_pair()
        plaintext = b'{"amount": 50}'
        envelope, aes_key = _make_rsa_encrypted_envelope(plaintext, pub)

        app = FastAPI()

        @app.post("/api/v1/orders", tags=["require-encrypt-request", "require-encrypt-response"])
        async def _handler(request: Request):
            return Response(content=b'{"code":0,"data":"ok"}', media_type="application/json")

        app.add_middleware(CryptoMiddleware)

        with patch("app.middleware.crypto_middleware.settings") as mock_cfg:
            mock_cfg.CRYPTO_RSA_PRIVATE_KEY = pem
            CryptoMiddleware._private_key = None
            CryptoMiddleware._private_key_loaded = False

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/api/v1/orders", content=envelope)

        assert resp.status_code == 200
        resp_envelope = resp.json()
        assert "iv" in resp_envelope and "data" in resp_envelope

        # Decrypt the response with the same AES key used for the request
        iv = base64.b64decode(resp_envelope["iv"])
        data = base64.b64decode(resp_envelope["data"])
        decrypted = aes_decrypt(data, aes_key, iv)
        assert json.loads(decrypted)["code"] == 0
