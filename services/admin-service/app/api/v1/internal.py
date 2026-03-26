from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ADMIN_NOT_FOUND, err, ok
from app.schemas.audit_log import AuditLogCreate, AuditLogResponse
from app.services import admin_service, audit_service

router = APIRouter()


@router.get("/admins/{admin_id}")
async def get_admin_permissions(
    admin_id: int, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Return admin permissions for token enrichment by auth-service."""
    admin = await admin_service.get_admin(db, admin_id)
    if admin is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=err(ADMIN_NOT_FOUND, "Admin not found"),
        )
    permissions = await admin_service.get_admin_permissions(db, admin_id)
    return JSONResponse(
        content=ok(
            {
                "id": admin.id,
                "username": admin.username,
                "permissions": permissions,
            }
        )
    )


@router.post("/audit-logs", status_code=status.HTTP_201_CREATED)
async def create_audit_log(
    body: AuditLogCreate, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Create an audit log entry. Called by other services."""
    log = await audit_service.create_audit_log(db, body)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=ok(AuditLogResponse.model_validate(log).model_dump(mode="json")),
    )
