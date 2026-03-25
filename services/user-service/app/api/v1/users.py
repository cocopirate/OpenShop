from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.response import USER_NOT_FOUND, err, ok
from app.schemas.user import AdminUserCreate, AdminUserResponse, AdminUserStatusUpdate, AdminUserUpdate
from app.services import user_service

router = APIRouter()


class AssignRolesRequest(BaseModel):
    role_ids: list[int]


@router.get("")
async def list_users(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    users = await user_service.get_users(db)
    return JSONResponse(content=ok([AdminUserResponse.model_validate(u).model_dump(mode="json") for u in users]))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: AdminUserCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    user = await user_service.create_user(db, body)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(AdminUserResponse.model_validate(user).model_dump(mode="json")),
    )


@router.get("/{user_id}")
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    user = await user_service.get_user_by_public_id(db, user_id)
    if user is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(USER_NOT_FOUND, "User not found"),
        )
    return JSONResponse(content=ok(AdminUserResponse.model_validate(user).model_dump(mode="json")))


@router.put("/{user_id}")
async def update_user(user_id: UUID, body: AdminUserUpdate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    user = await user_service.update_user(db, user_id, body)
    if user is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(USER_NOT_FOUND, "User not found"),
        )
    return JSONResponse(content=ok(AdminUserResponse.model_validate(user).model_dump(mode="json")))


@router.delete("/{user_id}")
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    deleted = await user_service.delete_user(db, user_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(USER_NOT_FOUND, "User not found"),
        )
    return JSONResponse(content=ok({"message": "deleted"}))


@router.post("/{user_id}/status")
async def update_status(user_id: UUID, body: AdminUserStatusUpdate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    redis = get_redis()
    user = await user_service.update_user_status(db, redis, user_id, body.status)
    if user is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(USER_NOT_FOUND, "User not found"),
        )
    return JSONResponse(content=ok(AdminUserResponse.model_validate(user).model_dump(mode="json")))


@router.post("/{user_id}/roles")
async def assign_roles(user_id: UUID, body: AssignRolesRequest, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    redis = get_redis()
    user = await user_service.assign_roles_to_user(db, redis, user_id, body.role_ids)
    if user is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(USER_NOT_FOUND, "User not found"),
        )
    return JSONResponse(content=ok(AdminUserResponse.model_validate(user).model_dump(mode="json")))
