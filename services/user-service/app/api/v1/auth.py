from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import AdminUserStatus
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import authenticate_user, create_token_for_user

router = APIRouter()


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    user = await authenticate_user(db, body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if user.status != AdminUserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    token = await create_token_for_user(db, redis, user)
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout():
    return {"message": "logged out"}
