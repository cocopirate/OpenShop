from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.response import ROLE_CANNOT_DELETE_SYSTEM, ROLE_NOT_FOUND, err, ok
from app.schemas.role import AdminRoleCreate, AdminRoleResponse, AdminRoleUpdate
from app.services import role_service

router = APIRouter()


class AssignPermissionsRequest(BaseModel):
    permission_ids: list[int]


@router.get("")
async def list_roles(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    roles = await role_service.get_roles(db)
    return JSONResponse(
        content=ok([AdminRoleResponse.model_validate(r).model_dump(mode="json") for r in roles])
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_role(
    body: AdminRoleCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    role = await role_service.create_role(db, body)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(AdminRoleResponse.model_validate(role).model_dump(mode="json")),
    )


@router.put("/{role_id}")
async def update_role(
    role_id: int, body: AdminRoleUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    role = await role_service.update_role(db, role_id, body)
    if role is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ROLE_NOT_FOUND, "Role not found"),
        )
    return JSONResponse(
        content=ok(AdminRoleResponse.model_validate(role).model_dump(mode="json"))
    )


@router.delete("/{role_id}")
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    success, reason = await role_service.delete_role(db, role_id)
    if not success:
        if reason == "not_found":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=err(ROLE_NOT_FOUND, "Role not found"),
            )
        # system_role
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=err(ROLE_CANNOT_DELETE_SYSTEM, "System roles cannot be deleted"),
        )
    return JSONResponse(content=ok({"message": "deleted"}))


@router.post("/{role_id}/permissions")
async def assign_permissions(
    role_id: int,
    body: AssignPermissionsRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redis = get_redis()
    role = await role_service.assign_permissions_to_role(db, redis, role_id, body.permission_ids)
    if role is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ROLE_NOT_FOUND, "Role not found"),
        )
    return JSONResponse(
        content=ok(AdminRoleResponse.model_validate(role).model_dump(mode="json"))
    )
