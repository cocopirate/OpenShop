from __future__ import annotations

from pydantic import BaseModel


# --------------------------------------------------------------------------- #
# Login requests                                                                #
# --------------------------------------------------------------------------- #


class ConsumerLoginRequest(BaseModel):
    phone: str
    password: str


class MerchantLoginRequest(BaseModel):
    phone: str
    password: str


class MerchantSubLoginRequest(BaseModel):
    username: str
    password: str


class StaffLoginRequest(BaseModel):
    phone: str
    password: str


class AdminLoginRequest(BaseModel):
    username: str
    password: str


# --------------------------------------------------------------------------- #
# Register request                                                              #
# --------------------------------------------------------------------------- #


class ConsumerRegisterRequest(BaseModel):
    phone: str
    password: str
    biz_id: int


# --------------------------------------------------------------------------- #
# Token responses                                                               #
# --------------------------------------------------------------------------- #


class ConsumerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MerchantTokenResponse(BaseModel):
    access_token: str
    merchant_id: str


class MerchantSubTokenResponse(BaseModel):
    access_token: str
    merchant_id: str
    permissions: list[str]


class StaffTokenResponse(BaseModel):
    access_token: str


class AdminTokenResponse(BaseModel):
    access_token: str
    permissions: list[str]


# --------------------------------------------------------------------------- #
# Token payload (internal)                                                      #
# --------------------------------------------------------------------------- #


class TokenPayload(BaseModel):
    sub: str
    account_type: str
    ver: int
    exp: int | None = None
    # optional fields depending on account_type
    merchant_id: str | None = None
    store_id: str | None = None
    job_type: str | None = None
    permissions: list[str] | None = None
