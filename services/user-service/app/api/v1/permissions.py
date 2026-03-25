from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.permission import PermissionCreate, PermissionResponse, PermissionUpdate
from app.services import permission_service

router = APIRouter()


@router.get("", response_model=list[PermissionResponse])
async def list_permissions(db: AsyncSession = Depends(get_db)):
    return await permission_service.get_permissions(db)


@router.post("", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(body: PermissionCreate, db: AsyncSession = Depends(get_db)):
    return await permission_service.create_permission(db, body)


@router.get("/{perm_id}", response_model=PermissionResponse)
async def get_permission(perm_id: int, db: AsyncSession = Depends(get_db)):
    perm = await permission_service.get_permission(db, perm_id)
    if perm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return perm


@router.put("/{perm_id}", response_model=PermissionResponse)
async def update_permission(
    perm_id: int, body: PermissionUpdate, db: AsyncSession = Depends(get_db)
):
    perm = await permission_service.update_permission(db, perm_id, body)
    if perm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return perm


@router.delete("/{perm_id}")
async def delete_permission(perm_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await permission_service.delete_permission(db, perm_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return {"message": "deleted"}
