"""Pydantic request / response schemas for the captcha service."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Shared sub-models                                                             #
# --------------------------------------------------------------------------- #


class TrackPoint(BaseModel):
    """A single pointer sample in a slider gesture."""

    t: int = Field(..., description="Elapsed time since gesture start (ms)")
    x: float = Field(..., description="Horizontal position (px)")
    y: float = Field(..., description="Vertical position (px)")


class DeviceInfo(BaseModel):
    type: Literal["h5", "pc", "app", "mini"]
    ua: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class CaptchaConfig(BaseModel):
    type: str = "slider"
    distance: int
    track_seed: str


# --------------------------------------------------------------------------- #
# /captcha/init                                                                 #
# --------------------------------------------------------------------------- #


class CaptchaInitRequest(BaseModel):
    scene: Literal["login", "register", "sms", "order"]
    client_type: Literal["h5", "pc", "app", "mini"]


class CaptchaInitResponse(BaseModel):
    challenge_id: str
    expire_in: int
    captcha: CaptchaConfig
    sign_key: str


# --------------------------------------------------------------------------- #
# /captcha/verify                                                               #
# --------------------------------------------------------------------------- #


class CaptchaVerifyRequest(BaseModel):
    challenge_id: str
    track: List[TrackPoint] = Field(..., min_length=2)
    start_time: int = Field(..., description="Absolute gesture start timestamp (ms epoch)")
    end_time: int = Field(..., description="Absolute gesture end timestamp (ms epoch)")
    device: DeviceInfo
    sign: str


class CaptchaVerifyResponse(BaseModel):
    """The field name ``pass`` is a Python keyword so we use an alias."""

    passed: bool = Field(..., alias="pass")
    score: float
    risk_level: Literal["low", "medium", "high"]
    token: Optional[str] = None

    model_config = {"populate_by_name": True}


# --------------------------------------------------------------------------- #
# Internal / risk feature snapshot                                              #
# --------------------------------------------------------------------------- #


class TrackFeatures(BaseModel):
    duration_ms: int
    avg_speed: float
    speed_std: float
    acc_std: float
    path_ratio: float
    y_std: float
    backward_count: int
    pause_count: int
    track_length: int
