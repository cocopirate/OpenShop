from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.response import (
    CREDENTIAL_ALREADY_EXISTS,
    INVALID_CREDENTIALS,
    MISSING_TOKEN,
    REFRESH_TOKEN_INVALID,
    TOKEN_INVALID,
    err,
    ok,
)
from app.core.security import decode_access_token
from app.schemas.auth import (
    AdminLoginRequest,
    AdminTokenResponse,
    ConsumerLoginRequest,
    ConsumerRegisterRequest,
    ConsumerSmsLoginRequest,
    ConsumerTokenResponse,
    LogoutRequest,
    MerchantLoginRequest,
    MerchantSubLoginRequest,
    MerchantSubTokenResponse,
    MerchantTokenResponse,
    RefreshTokenRequest,
    StaffLoginRequest,
    StaffTokenResponse,
)
from app.services.auth_service import (
    exchange_refresh_token,
    login_admin,
    login_consumer,
    login_merchant,
    login_merchant_sub,
    login_or_register_consumer_by_sms,
    login_staff,
    logout_token,
    register_consumer,
)

router = APIRouter()


@router.post("/consumer/login", summary="Consumer login (phone + password)", tags=["public"])
async def consumer_login(
    body: ConsumerLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    access_token, refresh_token = await login_consumer(db, redis, request, body.phone, body.password)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(ConsumerTokenResponse(access_token=access_token, refresh_token=refresh_token).model_dump()),
    )


@router.post("/consumer/sms-login", summary="Consumer login or register via SMS OTP", tags=["public"])
async def consumer_sms_login(
    body: ConsumerSmsLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    access_token, refresh_token = await login_or_register_consumer_by_sms(db, redis, request, body.phone, body.code)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(ConsumerTokenResponse(access_token=access_token, refresh_token=refresh_token).model_dump()),
    )


@router.post("/merchant/login", summary="Merchant login (phone + password)", tags=["public"])
async def merchant_login(
    body: MerchantLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    access_token, refresh_token, merchant_id = await login_merchant(db, redis, request, body.phone, body.password)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(MerchantTokenResponse(access_token=access_token, refresh_token=refresh_token, merchant_id=merchant_id).model_dump()),
    )


@router.post("/merchant-sub/login", summary="Merchant sub-account login (username + password)", tags=["public"])
async def merchant_sub_login(
    body: MerchantSubLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    access_token, refresh_token, merchant_id, permissions = await login_merchant_sub(
        db, redis, request, body.username, body.password
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(
            MerchantSubTokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                merchant_id=merchant_id,
                permissions=permissions,
            ).model_dump()
        ),
    )


@router.post("/staff/login", summary="Staff login (phone + password)", tags=["public"])
async def staff_login(
    body: StaffLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    access_token, refresh_token = await login_staff(db, redis, request, body.phone, body.password)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(StaffTokenResponse(access_token=access_token, refresh_token=refresh_token).model_dump()),
    )


@router.post("/admin/login", summary="Admin login (username + password)", tags=["public"])
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    access_token, refresh_token = await login_admin(db, redis, request, body.username, body.password)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(AdminTokenResponse(access_token=access_token, refresh_token=refresh_token).model_dump()),
    )


@router.post("/refresh", summary="Exchange refresh token for new access + refresh tokens", tags=["public"])
async def refresh_token_endpoint(body: RefreshTokenRequest) -> JSONResponse:
    redis = get_redis()
    try:
        new_access_token, new_refresh_token, payload = await exchange_refresh_token(redis, body.refresh_token)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=err(REFRESH_TOKEN_INVALID, exc.detail),
            )
        raise

    account_type = payload.get("account_type", "")

    if account_type == "admin":
        data = AdminTokenResponse(access_token=new_access_token, refresh_token=new_refresh_token).model_dump()
    elif account_type == "merchant":
        data = MerchantTokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            merchant_id=str(payload.get("merchant_id", "")),
        ).model_dump()
    elif account_type == "merchant_sub":
        data = MerchantSubTokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            merchant_id=str(payload.get("merchant_id", "")),
            permissions=payload.get("permissions", []),
        ).model_dump()
    elif account_type == "merchant_staff":
        data = StaffTokenResponse(access_token=new_access_token, refresh_token=new_refresh_token).model_dump()
    else:
        # consumer (default)
        data = ConsumerTokenResponse(access_token=new_access_token, refresh_token=new_refresh_token).model_dump()

    return JSONResponse(status_code=status.HTTP_200_OK, content=ok(data))


@router.post("/logout", summary="Logout – invalidate access token and revoke refresh token")
async def logout(request: Request, body: LogoutRequest | None = None) -> JSONResponse:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=err(MISSING_TOKEN, "Missing bearer token"),
        )
    token = auth_header[7:]
    try:
        payload = decode_access_token(token)
    except HTTPException:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=err(TOKEN_INVALID, "Invalid or expired token"),
        )

    redis = get_redis()
    rt = body.refresh_token if body else None
    await logout_token(redis, payload, refresh_token=rt)
    return JSONResponse(content=ok({"message": "logged out"}))


@router.post("/register/consumer", summary="Register new consumer credential", status_code=201, tags=["public"])
async def consumer_register(
    body: ConsumerRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        await register_consumer(db, body.phone, body.password, body.biz_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_409_CONFLICT:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=err(CREDENTIAL_ALREADY_EXISTS, exc.detail),
            )
        raise
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok({"message": "consumer registered"}),
    )
