from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.response import INVALID_CREDENTIALS, PERMISSION_DENIED, USER_DISABLED, err, ok
from app.models.user import AdminUserStatus
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import authenticate_user, create_token_for_user

router = APIRouter()


@router.post("/admin/login")
async def admin_login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    user = await authenticate_user(db, body.username, body.password)
    if user is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=err(INVALID_CREDENTIALS, "Invalid username or password"),
        )
    if user.status != AdminUserStatus.active:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=err(USER_DISABLED, "Account is disabled"),
        )
    token = await create_token_for_user(db, redis, user)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ok(TokenResponse(access_token=token).model_dump()),
    )


@router.post("/logout")
async def logout() -> JSONResponse:
    return JSONResponse(content=ok({"message": "logged out"}))
