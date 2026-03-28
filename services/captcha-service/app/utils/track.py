"""Track data preprocessing helpers."""
from __future__ import annotations

from typing import List

from app.models.schema import TrackPoint


def deduplicate(track: List[TrackPoint]) -> List[TrackPoint]:
    """Remove consecutive duplicate points (same x, y, t)."""
    if not track:
        return track
    deduped = [track[0]]
    for pt in track[1:]:
        prev = deduped[-1]
        if pt.t != prev.t or pt.x != prev.x or pt.y != prev.y:
            deduped.append(pt)
    return deduped


def normalise_timestamps(track: List[TrackPoint]) -> List[TrackPoint]:
    """Shift timestamps so the first point starts at t=0."""
    if not track:
        return track
    t0 = track[0].t
    return [TrackPoint(t=p.t - t0, x=p.x, y=p.y) for p in track]


def preprocess(track: List[TrackPoint]) -> List[TrackPoint]:
    """Full preprocessing pipeline: deduplicate then normalise."""
    return normalise_timestamps(deduplicate(track))
