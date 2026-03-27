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
    ConsumerTokenResponse,
    MerchantLoginRequest,
    MerchantSubLoginRequest,
    MerchantSubTokenResponse,
    MerchantTokenResponse,
    StaffLoginRequest,
    StaffTokenResponse,
)
from app.services.auth_service import (
    login_admin,
    login_consumer,
    login_merchant,
    login_merchant_sub,
    login_staff,
    logout_token,
    register_consumer,
)

router = APIRouter()


@router.post("/consumer/login", summary="Consumer login (phone + password)")
async def consumer_login(
    body: ConsumerLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    token = await login_consumer(db, redis, request, body.phone, body.password)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(ConsumerTokenResponse(access_token=token).model_dump()),
    )


@router.post("/merchant/login", summary="Merchant login (phone + password)")
async def merchant_login(
    body: MerchantLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    token, merchant_id = await login_merchant(db, redis, request, body.phone, body.password)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(MerchantTokenResponse(access_token=token, merchant_id=merchant_id).model_dump()),
    )


@router.post("/merchant-sub/login", summary="Merchant sub-account login (username + password)")
async def merchant_sub_login(
    body: MerchantSubLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    token, merchant_id, permissions = await login_merchant_sub(
        db, redis, request, body.username, body.password
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(
            MerchantSubTokenResponse(
                access_token=token,
                merchant_id=merchant_id,
                permissions=permissions,
            ).model_dump()
        ),
    )


@router.post("/staff/login", summary="Staff login (phone + password)")
async def staff_login(
    body: StaffLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    token = await login_staff(db, redis, request, body.phone, body.password)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(StaffTokenResponse(access_token=token).model_dump()),
    )


@router.post("/admin/login", summary="Admin login (username + password)")
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    token = await login_admin(db, redis, request, body.username, body.password)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(AdminTokenResponse(access_token=token).model_dump()),
    )


@router.post("/logout", summary="Logout – invalidate token via Redis version bump")
async def logout(request: Request) -> JSONResponse:
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
    await logout_token(redis, payload)
    return JSONResponse(content=ok({"message": "logged out"}))


@router.post("/register/consumer", summary="Register new consumer credential", status_code=201)
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
