from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.response import ADMIN_ALREADY_EXISTS, ADMIN_NOT_FOUND, err, ok
from app.schemas.admin import (
    AdminAccountCreate,
    AdminAccountResponse,
    AdminAccountStatusUpdate,
    AdminAccountUpdate,
)
from app.services import admin_service

router = APIRouter()


class AssignRolesRequest(BaseModel):
    role_ids: list[int]


@router.get("")
async def list_admins(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    admins, total = await admin_service.get_admins(db, page=page, page_size=page_size)
    return JSONResponse(
        content=ok(
            {
                "items": [AdminAccountResponse.model_validate(a).model_dump(mode="json") for a in admins],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_admin(
    body: AdminAccountCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    existing = await admin_service.get_admin_by_username(db, body.username)
    if existing is not None:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=err(ADMIN_ALREADY_EXISTS, "Username already exists"),
        )
    admin = await admin_service.create_admin(db, body)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(AdminAccountResponse.model_validate(admin).model_dump(mode="json")),
    )


@router.get("/{admin_id}")
async def get_admin(admin_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    admin = await admin_service.get_admin(db, admin_id)
    if admin is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ADMIN_NOT_FOUND, "Admin not found"),
        )
    return JSONResponse(
        content=ok(AdminAccountResponse.model_validate(admin).model_dump(mode="json"))
    )


@router.put("/{admin_id}")
async def update_admin(
    admin_id: int, body: AdminAccountUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    admin = await admin_service.update_admin(db, admin_id, body)
    if admin is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ADMIN_NOT_FOUND, "Admin not found"),
        )
    return JSONResponse(
        content=ok(AdminAccountResponse.model_validate(admin).model_dump(mode="json"))
    )


@router.delete("/{admin_id}")
async def delete_admin(admin_id: int, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    deleted = await admin_service.delete_admin(db, admin_id)
    if not deleted:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ADMIN_NOT_FOUND, "Admin not found"),
        )
    return JSONResponse(content=ok({"message": "deleted"}))


@router.post("/{admin_id}/roles")
async def assign_roles(
    admin_id: int, body: AssignRolesRequest, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    redis = get_redis()
    admin = await admin_service.assign_roles_to_admin(db, redis, admin_id, body.role_ids)
    if admin is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ADMIN_NOT_FOUND, "Admin not found"),
        )
    return JSONResponse(
        content=ok(AdminAccountResponse.model_validate(admin).model_dump(mode="json"))
    )


@router.post("/{admin_id}/status")
async def update_status(
    admin_id: int, body: AdminAccountStatusUpdate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    redis = get_redis()
    admin = await admin_service.update_admin_status(db, redis, admin_id, body.status)
    if admin is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ADMIN_NOT_FOUND, "Admin not found"),
        )
    return JSONResponse(
        content=ok(AdminAccountResponse.model_validate(admin).model_dump(mode="json"))
    )
