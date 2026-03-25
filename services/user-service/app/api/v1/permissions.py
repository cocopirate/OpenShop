from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import PERMISSION_NOT_FOUND, err, ok
from app.schemas.permission import PermissionCreate, PermissionResponse, PermissionUpdate
from app.services import permission_service

router = APIRouter()


@router.get("")
async def list_permissions(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    perms = await permission_service.get_permissions(db)
    return JSONResponse(content=ok([PermissionResponse.model_validate(p).model_dump(mode="json") for p in perms]))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_permission(body: PermissionCreate, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    perm = await permission_service.create_permission(db, body)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(PermissionResponse.model_validate(perm).model_dump(mode="json")),
    )


@router.get("/{perm_id}")
async def get_permission(perm_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    perm = await permission_service.get_permission(db, perm_id)
    if perm is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(PERMISSION_NOT_FOUND, "Permission not found"),
        )
    return JSONResponse(content=ok(PermissionResponse.model_validate(perm).model_dump(mode="json")))


@router.put("/{perm_id}")
async def update_permission(
    perm_id: int, body: PermissionUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    perm = await permission_service.update_permission(db, perm_id, body)
    if perm is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(PERMISSION_NOT_FOUND, "Permission not found"),
        )
    return JSONResponse(content=ok(PermissionResponse.model_validate(perm).model_dump(mode="json")))


@router.delete("/{perm_id}")
async def delete_permission(perm_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    deleted = await permission_service.delete_permission(db, perm_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(PERMISSION_NOT_FOUND, "Permission not found"),
        )
    return JSONResponse(content=ok({"message": "deleted"}))
