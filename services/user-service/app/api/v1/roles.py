from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from app.services import role_service

router = APIRouter()


class AssignPermissionsRequest(BaseModel):
    permission_ids: list[int]


@router.get("", response_model=list[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db)):
    return await role_service.get_roles(db)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(body: RoleCreate, db: AsyncSession = Depends(get_db)):
    return await role_service.create_role(db, body)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(role_id: int, db: AsyncSession = Depends(get_db)):
    role = await role_service.get_role(db, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(role_id: int, body: RoleUpdate, db: AsyncSession = Depends(get_db)):
    role = await role_service.update_role(db, role_id, body)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.delete("/{role_id}")
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await role_service.delete_role(db, role_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return {"message": "deleted"}


@router.post("/{role_id}/permissions", response_model=RoleResponse)
async def assign_permissions(
    role_id: int, body: AssignPermissionsRequest, db: AsyncSession = Depends(get_db)
):
    redis = get_redis()
    role = await role_service.assign_permissions_to_role(db, redis, role_id, body.permission_ids)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role
