"""Numpy-based feature extraction from a slider track.

All *speed* values are in px/ms; *time* values are in ms.
"""
from __future__ import annotations

import math
from typing import List

import numpy as np

from app.models.schema import TrackFeatures, TrackPoint

# Pause threshold: movements slower than this (px/ms) count as a pause.
_PAUSE_THRESHOLD_PX_PER_MS: float = 0.02


def extract(track: List[TrackPoint], duration_ms: int) -> TrackFeatures:
    """Extract behavioural features from a preprocessed track.

    Parameters
    ----------
    track:
        Preprocessed (deduplicated, t=0-based) list of track points.
    duration_ms:
        Absolute gesture duration = end_time - start_time.
    """
    if len(track) < 2:
        return _default_features(duration_ms)

    xs = np.array([p.x for p in track], dtype=float)
    ys = np.array([p.y for p in track], dtype=float)
    ts = np.array([p.t for p in track], dtype=float)

    # Spatial differences between consecutive points
    dx = np.diff(xs)
    dy = np.diff(ys)
    dt = np.diff(ts)
    dt = np.where(dt <= 0, 1.0, dt)  # guard against zero-duration intervals

    segment_dist = np.sqrt(dx**2 + dy**2)
    path_length = float(np.sum(segment_dist))

    # Displacement start → end
    displacement = math.sqrt((xs[-1] - xs[0]) ** 2 + (ys[-1] - ys[0]) ** 2)
    path_ratio = path_length / displacement if displacement > 1e-6 else 999.0

    # Per-segment speed (px/ms)
    speeds = segment_dist / dt
    avg_speed = float(np.mean(speeds))
    speed_std = float(np.std(speeds))

    # Per-segment acceleration (px/ms²)
    if len(speeds) >= 2:
        acc = np.diff(speeds) / dt[:-1]
        acc_std = float(np.std(acc))
    else:
        acc_std = 0.0

    # Y-axis jitter
    y_std = float(np.std(ys))

    # Backward movements (negative x delta)
    backward_count = int(np.sum(dx < 0))

    # Pauses (very slow segments)
    pause_count = int(np.sum(speeds < _PAUSE_THRESHOLD_PX_PER_MS))

    return TrackFeatures(
        duration_ms=duration_ms,
        avg_speed=round(avg_speed, 6),
        speed_std=round(speed_std, 6),
        acc_std=round(acc_std, 6),
        path_ratio=round(path_ratio, 6),
        y_std=round(y_std, 6),
        backward_count=backward_count,
        pause_count=pause_count,
        track_length=len(track),
    )


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #


def _default_features(duration_ms: int) -> TrackFeatures:
    """Return zero-value features used when the track is too short."""
    return TrackFeatures(
        duration_ms=duration_ms,
        avg_speed=0.0,
        speed_std=0.0,
        acc_std=0.0,
        path_ratio=0.0,
        y_std=0.0,
        backward_count=0,
        pause_count=0,
        track_length=0,
    )
