"""Weighted behavioural scoring model.

Score = Σ (normalised_feature_score × weight)

Weights per PRD section 5.3:
    speed_std    0.20
    y_std        0.15
    path_ratio   0.15
    backward     0.15
    pause        0.10
    duration     0.20
    acc_std      0.05
"""
from __future__ import annotations

import math
from typing import Literal

from app.models.schema import TrackFeatures

# --------------------------------------------------------------------------- #
# Weights                                                                       #
# --------------------------------------------------------------------------- #

_WEIGHTS: dict[str, float] = {
    "speed_std": 0.20,
    "y_std": 0.15,
    "path_ratio": 0.15,
    "backward": 0.15,
    "pause": 0.10,
    "duration": 0.20,
    "acc_std": 0.05,
}

# Risk thresholds (default; overridden at call-site from config)
_DEFAULT_PASS_THRESHOLD = 0.7
_DEFAULT_REJECT_THRESHOLD = 0.4


# --------------------------------------------------------------------------- #
# Individual feature scorers (0 → bot-like, 1 → human-like)                   #
# --------------------------------------------------------------------------- #


def _bell(value: float, mu: float, sigma: float) -> float:
    """Gaussian bell-curve peaked at *mu*."""
    if sigma <= 0:
        return 0.0
    return math.exp(-0.5 * ((value - mu) / sigma) ** 2)


def _ramp(value: float, lo: float, hi: float) -> float:
    """Linear ramp clipped to [0, 1]."""
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _score_speed_std(speed_std: float) -> float:
    # Bots: near-zero std; humans: moderate variation 0.05–0.5 px/ms
    return _ramp(speed_std, 0.0, 0.3)


def _score_y_std(y_std: float) -> float:
    # Bots: y_std ≈ 0; humans: slight vertical jitter 1–20 px
    return _bell(y_std, 6.0, 10.0)


def _score_path_ratio(path_ratio: float) -> float:
    # Bots: exactly 1.0 (straight line); humans: 1.05–1.4
    if path_ratio >= 100:
        return 0.0
    return _bell(path_ratio, 1.15, 0.3)


def _score_backward(backward_count: int) -> float:
    # At least some minor correction is human; but heavy backtracking is also
    # suspicious (capped at 3 for full score)
    return min(1.0, backward_count / 3.0)


def _score_pause(pause_count: int) -> float:
    # Short pauses (micro-hesitations) are human; capped at 3
    return min(1.0, pause_count / 3.0)


def _score_duration(duration_ms: int) -> float:
    # Bots: <200 ms or >15 000 ms; humans: peak around 1 200 ms
    return _bell(duration_ms, 1200.0, 1500.0)


def _score_acc_std(acc_std: float) -> float:
    # Bots: constant velocity (acc_std ≈ 0); humans: variable
    return _ramp(acc_std, 0.0, 0.3)


# --------------------------------------------------------------------------- #
# Public API                                                                    #
# --------------------------------------------------------------------------- #


def compute_score(features: TrackFeatures) -> float:
    """Return a human-likeness score in [0, 1] (higher = more human)."""
    component_scores = {
        "speed_std": _score_speed_std(features.speed_std),
        "y_std": _score_y_std(features.y_std),
        "path_ratio": _score_path_ratio(features.path_ratio),
        "backward": _score_backward(features.backward_count),
        "pause": _score_pause(features.pause_count),
        "duration": _score_duration(features.duration_ms),
        "acc_std": _score_acc_std(features.acc_std),
    }
    total = sum(
        component_scores[k] * _WEIGHTS[k] for k in _WEIGHTS
    )
    return round(min(1.0, max(0.0, total)), 4)


RiskLevel = Literal["low", "medium", "high"]


def determine_risk(
    score: float,
    pass_threshold: float = _DEFAULT_PASS_THRESHOLD,
    reject_threshold: float = _DEFAULT_REJECT_THRESHOLD,
) -> tuple[bool, RiskLevel]:
    """Return *(passed, risk_level)* based on the numeric *score*.

    score > pass_threshold          → pass,  low risk
    reject_threshold ≤ score ≤ pass → fail,  medium risk (secondary needed)
    score < reject_threshold        → fail,  high risk (rejected)
    """
    if score >= pass_threshold:
        return True, "low"
    if score >= reject_threshold:
        return False, "medium"
    return False, "high"
