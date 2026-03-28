"""Tests for captcha-service core logic and API endpoints."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Provide required env vars before importing app modules.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CAPTCHA_SECRET_KEY", "test-secret-key")
os.environ.setdefault(
    "CAPTCHA_AES_KEY", "a" * 64
)

# ---------------------------------------------------------------------------
# Feature extractor tests
# ---------------------------------------------------------------------------

from app.models.schema import TrackPoint
from app.service import feature_extractor, scorer
from app.utils import track as track_utils


def _make_human_track():
    """Simulate a realistic human slider gesture (180 px in ~1.2 s)."""
    import math

    points = []
    for i in range(60):
        t = i * 20  # 20 ms intervals
        # Non-linear progress with slight y jitter
        progress = (1 - math.cos(math.pi * i / 60)) / 2
        x = round(progress * 180 + (0.5 - (i % 3) * 0.3), 2)
        y = round(2 * math.sin(i * 0.4), 2)
        points.append(TrackPoint(t=t, x=x, y=y))
    return points


def _make_bot_track():
    """Simulate a bot: perfectly linear, constant speed, zero y movement."""
    return [
        TrackPoint(t=i * 10, x=float(i * 3), y=0.0)
        for i in range(60)
    ]


class TestTrackUtils:
    def test_deduplicate_removes_consecutive_duplicates(self):
        pts = [
            TrackPoint(t=0, x=0, y=0),
            TrackPoint(t=0, x=0, y=0),
            TrackPoint(t=10, x=5, y=1),
        ]
        result = track_utils.deduplicate(pts)
        assert len(result) == 2

    def test_normalise_starts_at_zero(self):
        pts = [
            TrackPoint(t=1000, x=0, y=0),
            TrackPoint(t=1020, x=5, y=1),
        ]
        result = track_utils.normalise_timestamps(pts)
        assert result[0].t == 0
        assert result[1].t == 20

    def test_preprocess_pipeline(self):
        pts = [
            TrackPoint(t=500, x=0, y=0),
            TrackPoint(t=500, x=0, y=0),  # duplicate
            TrackPoint(t=520, x=5, y=1),
        ]
        result = track_utils.preprocess(pts)
        assert result[0].t == 0
        assert len(result) == 2


class TestFeatureExtractor:
    def test_human_track_extracts_nonzero_features(self):
        track = _make_human_track()
        processed = track_utils.preprocess(track)
        duration_ms = track[-1].t - track[0].t
        features = feature_extractor.extract(processed, duration_ms)

        assert features.track_length == len(processed)
        assert features.avg_speed > 0
        assert features.speed_std >= 0
        assert features.path_ratio > 0
        assert features.y_std > 0

    def test_short_track_returns_defaults(self):
        track = [TrackPoint(t=0, x=0, y=0)]
        features = feature_extractor.extract(track, 100)
        assert features.track_length == 0
        assert features.avg_speed == 0.0

    def test_bot_track_y_std_near_zero(self):
        track = _make_bot_track()
        processed = track_utils.preprocess(track)
        duration_ms = track[-1].t - track[0].t
        features = feature_extractor.extract(processed, duration_ms)
        assert features.y_std == 0.0
        assert features.speed_std < 0.01  # near-constant speed


class TestScorer:
    def test_human_track_passes(self):
        track = _make_human_track()
        processed = track_utils.preprocess(track)
        duration_ms = 1200
        features = feature_extractor.extract(processed, duration_ms)
        score = scorer.compute_score(features)
        passed, risk_level = scorer.determine_risk(score)
        # Human track should score reasonably high
        assert score > 0.0
        assert risk_level in ("low", "medium", "high")

    def test_bot_track_fails(self):
        track = _make_bot_track()
        processed = track_utils.preprocess(track)
        duration_ms = 590  # 59 * 10 ms
        features = feature_extractor.extract(processed, duration_ms)
        score = scorer.compute_score(features)
        passed, risk_level = scorer.determine_risk(score)
        # Bot track should score low
        assert score < 0.6

    def test_score_range(self):
        track = _make_human_track()
        processed = track_utils.preprocess(track)
        features = feature_extractor.extract(processed, 1200)
        score = scorer.compute_score(features)
        assert 0.0 <= score <= 1.0

    def test_determine_risk_pass(self):
        passed, level = scorer.determine_risk(0.8)
        assert passed is True
        assert level == "low"

    def test_determine_risk_medium(self):
        passed, level = scorer.determine_risk(0.55)
        assert passed is False
        assert level == "medium"

    def test_determine_risk_high(self):
        passed, level = scorer.determine_risk(0.2)
        assert passed is False
        assert level == "high"


# ---------------------------------------------------------------------------
# Security / signing tests
# ---------------------------------------------------------------------------

from app.core.security import compute_sign, generate_sign_key, verify_sign


class TestSecurity:
    def test_sign_verify_roundtrip(self):
        key = generate_sign_key()
        sign = compute_sign("cid123", 1000000, 1001200, key)
        assert verify_sign("cid123", 1000000, 1001200, key, sign) is True

    def test_sign_wrong_key_fails(self):
        key = generate_sign_key()
        sign = compute_sign("cid123", 1000000, 1001200, key)
        wrong_key = generate_sign_key()
        assert verify_sign("cid123", 1000000, 1001200, wrong_key, sign) is False

    def test_sign_tampered_challenge_fails(self):
        key = generate_sign_key()
        sign = compute_sign("cid123", 1000000, 1001200, key)
        assert verify_sign("tampered", 1000000, 1001200, key, sign) is False

    def test_sign_key_is_hex_string(self):
        key = generate_sign_key()
        assert len(key) == 64
        int(key, 16)  # should not raise


# ---------------------------------------------------------------------------
# AES crypto tests
# ---------------------------------------------------------------------------

from app.utils.crypto import decrypt_track, encrypt_track


class TestCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        original = '[{"t": 0, "x": 0, "y": 0}, {"t": 16, "x": 5, "y": 1}]'
        ciphertext = encrypt_track(original)
        assert isinstance(ciphertext, bytes)
        assert ciphertext != original.encode()
        recovered = decrypt_track(ciphertext)
        assert recovered == original

    def test_different_encryptions_produce_different_ciphertexts(self):
        msg = "hello world"
        ct1 = encrypt_track(msg)
        ct2 = encrypt_track(msg)
        # AES-GCM uses a random nonce → outputs differ
        assert ct1 != ct2


# ---------------------------------------------------------------------------
# API endpoint tests (using httpx AsyncClient + mocked Redis)
# ---------------------------------------------------------------------------

import json as _json

import pytest
from httpx import ASGITransport, AsyncClient

import app.main as _app_module


def _make_redis_mock():
    redis = AsyncMock()
    _store: dict = {}

    async def _set(key, value, ex=None):
        _store[key] = value

    async def _get(key):
        return _store.get(key)

    async def _ping():
        return True

    redis.set = AsyncMock(side_effect=_set)
    redis.get = AsyncMock(side_effect=_get)
    redis.ping = AsyncMock(side_effect=_ping)
    return redis


@pytest.fixture
def mock_redis():
    return _make_redis_mock()


@pytest.fixture
async def client(mock_redis):
    """Yield a long-lived AsyncClient that reuses the same mocked Redis store."""
    from app.core import redis as redis_module

    with patch.object(redis_module, "_client", mock_redis):
        transport = ASGITransport(app=_app_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


class TestCaptchaInitEndpoint:
    async def test_init_returns_challenge(self, client):
        resp = await client.get("/captcha/init?scene=login&client_type=h5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert "challenge_id" in data
        assert "sign_key" in data
        assert data["expire_in"] == 120
        assert data["captcha"]["type"] == "slider"

    async def test_init_invalid_scene(self, client):
        resp = await client.get("/captcha/init?scene=invalid&client_type=h5")
        assert resp.status_code == 422


class TestCaptchaVerifyEndpoint:
    def _build_body(self, challenge_id: str, sign_key: str) -> dict:
        from app.core.security import compute_sign

        start_time = 1710000000000
        end_time = 1710000001200
        sign = compute_sign(challenge_id, start_time, end_time, sign_key)

        return {
            "challenge_id": challenge_id,
            "track": [
                {"t": 0, "x": 0.0, "y": 0.0},
                {"t": 20, "x": 5.0, "y": 0.5},
                {"t": 40, "x": 12.0, "y": 1.2},
                {"t": 60, "x": 20.0, "y": 0.8},
                {"t": 80, "x": 30.0, "y": 1.5},
                {"t": 100, "x": 45.0, "y": 0.3},
                {"t": 120, "x": 60.0, "y": 1.8},
                {"t": 140, "x": 78.0, "y": 0.6},
                {"t": 160, "x": 95.0, "y": 2.1},
                {"t": 180, "x": 110.0, "y": 1.0},
                {"t": 200, "x": 130.0, "y": 1.3},
                {"t": 220, "x": 150.0, "y": 0.9},
                {"t": 240, "x": 165.0, "y": 1.6},
                {"t": 260, "x": 175.0, "y": 0.4},
                {"t": 280, "x": 180.0, "y": 0.2},
            ],
            "start_time": start_time,
            "end_time": end_time,
            "device": {"type": "h5", "ua": "test-ua", "width": 375, "height": 812},
            "sign": sign,
        }

    async def test_verify_full_flow(self, client):
        # Step 1: init
        init_resp = await client.get("/captcha/init?scene=login&client_type=h5")
        assert init_resp.status_code == 200
        init_data = init_resp.json()["data"]
        challenge_id = init_data["challenge_id"]
        sign_key = init_data["sign_key"]

        # Step 2: verify
        body = self._build_body(challenge_id, sign_key)
        verify_resp = await client.post("/captcha/verify", json=body)
        assert verify_resp.status_code == 200
        result = verify_resp.json()["data"]
        assert "pass" in result
        assert "score" in result
        assert result["risk_level"] in ("low", "medium", "high")

    async def test_verify_invalid_signature(self, client):
        init_resp = await client.get("/captcha/init?scene=login&client_type=h5")
        init_data = init_resp.json()["data"]

        body = self._build_body(init_data["challenge_id"], init_data["sign_key"])
        body["sign"] = "invalidsignature" * 4  # wrong sign

        verify_resp = await client.post("/captcha/verify", json=body)
        assert verify_resp.status_code == 400

    async def test_verify_unknown_challenge(self, client):
        from app.core.security import compute_sign

        start = 1710000000000
        end = 1710000001200
        fake_key = "a" * 64
        sign = compute_sign("nonexistent", start, end, fake_key)

        body = {
            "challenge_id": "nonexistent",
            "track": [{"t": 0, "x": 0, "y": 0}, {"t": 100, "x": 180, "y": 0}],
            "start_time": start,
            "end_time": end,
            "device": {"type": "pc"},
            "sign": sign,
        }
        resp = await client.post("/captcha/verify", json=body)
        assert resp.status_code == 404
