from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import PERMISSION_NOT_FOUND, err, ok
from app.schemas.permission import AdminPermissionCreate, AdminPermissionResponse, AdminPermissionUpdate
from app.services import permission_service

router = APIRouter()


@router.get("")
async def list_permissions(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    perms = await permission_service.get_permissions(db)
    tree = permission_service.build_permission_tree(perms)
    return JSONResponse(
        content=ok([node.model_dump(mode="json") for node in tree])
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_permission(
    body: AdminPermissionCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    perm = await permission_service.create_permission(db, body)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(AdminPermissionResponse.model_validate(perm).model_dump(mode="json")),
    )


@router.put("/{perm_id}")
async def update_permission(
    perm_id: int, body: AdminPermissionUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    perm = await permission_service.update_permission(db, perm_id, body)
    if perm is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(PERMISSION_NOT_FOUND, "Permission not found"),
        )
    return JSONResponse(
        content=ok(AdminPermissionResponse.model_validate(perm).model_dump(mode="json"))
    )


@router.delete("/{perm_id}")
async def delete_permission(
    perm_id: int, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    deleted = await permission_service.delete_permission(db, perm_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(PERMISSION_NOT_FOUND, "Permission not found"),
        )
    return JSONResponse(content=ok({"message": "deleted"}))
